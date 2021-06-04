from collections import namedtuple
from django.db import models
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .common_info import CommonInfo
from .PUC import PUC
from .product import Product
from .extracted_list_presence import ExtractedListPresence
from .data_document import DataDocument
from .group_type import GroupType
from ..utils import SimpleTree


def validate_prefix(value):
    if value[:6] != "DTXSID":
        raise ValidationError(
            _('%(value)s does not begin with "DTXSID"'), params={"value": value}
        )


def validate_blank_char(value):
    if " " in value:
        raise ValidationError(
            _("%(value)s cannot have a blank character"), params={"value": value}
        )


class DSSToxLookup(CommonInfo):
    """
    The DSSToxLookup table stores the canonical names for
    chemical compounds. When a raw chemical name and CAS combination
    is "curated," the curator links the raw chemical's RID to an SID
    in the DSSToxLookup table. 
    """

    sid = models.CharField(
        "DTXSID",
        max_length=50,
        null=False,
        blank=False,
        unique=True,
        validators=[validate_prefix, validate_blank_char],
    )
    true_cas = models.CharField("True CAS", max_length=50, blank=True)
    true_chemname = models.CharField("True chemical name", max_length=500, blank=True)

    class JSONAPIMeta:
        resource_name = "chemical"

    def __str__(self):
        return self.true_chemname

    def get_absolute_url(self):
        return reverse("chemical", kwargs={"sid": self.sid})

    def get_puc_count(self):
        return PUC.objects.filter(
            productuberpuc__product__in=Product.objects.filter(
                productdocument__document__extractedtext__rawchem__dsstox=self
            )
        ).count()

    def get_puc_count_by_kind(self, kind):
        return (
            PUC.objects.filter(kind=kind)
            .filter(
                productuberpuc__product__in=Product.objects.filter(
                    productdocument__document__extractedtext__rawchem__dsstox=self
                )
            )
            .count()
        )

    def get_cumulative_puc_count(self, kind=None):
        """
        Gets the count of all PUCs associated with
        the DTXSID or associated with
        one of its child or grandchild PUCs. 
        For performance reasons, only used for testing.
        """
        pucs = PUC.objects.filter(
            productuberpuc__product__in=Product.objects.filter(
                productdocument__document__extractedtext__rawchem__dsstox=self
            )
        )
        if kind:
            pucs = pucs.filter(kind=kind)
        cpucs = PUC.objects.filter(
            # grandparents of PUCs with products
            models.Q(gen_cat__in=pucs.values_list("gen_cat"), prod_fam="")
            # parents of PUCs with products
            | models.Q(
                gen_cat__in=pucs.values_list("gen_cat"),
                prod_fam__in=pucs.values_list("prod_fam"),
                prod_fam__isnull=False,
                prod_type="",
            )
            # the original PUCs with products
            | models.Q(id__in=pucs.values_list("id"))
        )

        return cpucs.count()

    def get_cumulative_puc_products_tree(self, kind=None, data_format=None):
        from dashboard.models import ProductsPerPuc

        if kind is not None:
            product_count_query = f"""
                select ptp.puc_id, COUNT(ptp.product_id) AS product_count 
                from dashboard_producttopuc ptp 
                join dashboard_productdocument doc on ptp.product_id = doc.product_id 
                join dashboard_rawchem chem on doc.document_id = chem.extracted_text_id 
                join dashboard_puc puc on ptp.puc_id = puc.id
                join dashboard_puckind pk on pk.id = puc.kind_id
                where ptp.is_uber_puc = true and chem.dsstox_id = {self.id} and pk.code = '{kind}'
                group by ptp.puc_id 
            """
        else:
            product_count_query = f"""
                select ptp.puc_id, COUNT(ptp.product_id) AS product_count
                from dashboard_producttopuc ptp
                join dashboard_productdocument doc on ptp.product_id = doc.product_id
                join dashboard_rawchem chem on doc.document_id = chem.extracted_text_id
                where ptp.is_uber_puc = true and chem.dsstox_id = {self.id}
                group by ptp.puc_id
            """

        raw_query = f"""
        SELECT cumulative_union.*, puc.id, puc.gen_cat, puc.prod_fam, puc.prod_type,
            COALESCE(pcq.product_count,0) as product_count
        FROM (
            -- gen cat
            SELECT gencat_id.puc_id, gencat_id.kind_id, 1 as puc_level,
                    sum(pcq.product_count) as cumulative_product_count
            FROM dashboard_puc puc
            JOIN ({product_count_query}) pcq ON pcq.puc_id = puc.id
            JOIN (
                select kind_id, gen_cat, id as puc_id 
                from dashboard_puc where prod_fam = '' and prod_type = '' 
            ) gencat_id ON gencat_id.gen_cat = puc.gen_cat AND gencat_id.kind_id = puc.kind_id
            GROUP BY gencat_id.kind_id, gencat_id.gen_cat, gencat_id.puc_id
        UNION
            -- prod fam
            SELECT prodfam_id.puc_id, prodfam_id.kind_id, 2 as puc_level,
                   sum(pcq.product_count) as cumulative_product_count
            FROM dashboard_puc puc
            JOIN ( {product_count_query} ) pcq ON pcq.puc_id = puc.id
            JOIN (
                select kind_id, gen_cat, prod_fam, id as puc_id 
                from dashboard_puc where prod_fam <> '' and prod_type = '' 
            ) prodfam_id ON prodfam_id.gen_cat = puc.gen_cat 
                        AND prodfam_id.kind_id = puc.kind_id 
                        AND prodfam_id.prod_fam = puc.prod_fam
            WHERE puc.prod_fam <> ''
            GROUP BY  prodfam_id.puc_id, prodfam_id.kind_id, prodfam_id.gen_cat, prodfam_id.prod_fam
        UNION
            -- prod_type
            SELECT puc_id, kind_id, 3 as puc_level, pcq.product_count as cumulative_product_count
            FROM dashboard_puc puc
            JOIN ({product_count_query}) pcq  ON pcq.puc_id = puc.id
            WHERE puc.prod_type <> ''
        ) cumulative_union
        LEFT JOIN ({product_count_query}) pcq ON pcq.puc_id = cumulative_union.puc_id
        JOIN dashboard_puc puc ON puc.id = cumulative_union.puc_id
        ORDER BY puc.gen_cat, puc.prod_fam, puc.prod_type
        """

        raw_qs = ProductsPerPuc.objects.raw(raw_query)
        tree = SimpleTree()
        for p in raw_qs:
            names = tuple(n for n in (p.gen_cat, p.prod_fam, p.prod_type) if n)
            # turn data into dictionary
            if data_format == "dict":
                data = {
                    "puc_id": p.puc_id,
                    "kind_id": p.kind_id,
                    "puc_level": p.puc_level,
                    "gen_cat": p.gen_cat,
                    "prod_fam": p.prod_fam,
                    "prod_type": p.prod_type,
                    "product_count": p.product_count,
                    "cumulative_product_count": int(p.cumulative_product_count),
                }
                tree[names] = data
            else:
                tree[names] = p
        return tree

    def get_unique_datadocument_group_types_for_dropdown(self):
        docs = DataDocument.objects.from_chemical(self)
        gts = set(docs.values_list("data_group__group_type__title", flat=True))
        return GroupType.objects.filter(title__in=gts)

    def get_tag_sets(self):
        qs = ExtractedListPresence.objects.filter(dsstox=self)
        tagsets, presence_ids, doc_ids = [], [], []
        for x in qs:
            if x.tags.exists():
                tagsets.append(tuple(x.tags.all()))
                presence_ids.append(x.pk)
                doc_ids.append(x.extracted_text.data_document_id)
        one = {}
        two = {}
        for i, j in enumerate(tagsets):
            if not two.get(hash(j)):
                two[hash(j)] = []
            one[hash(j)] = presence_ids[i]
            two[hash(j)].append(doc_ids[i])
        counter = set(tagsets)
        KeywordSet = namedtuple("KeywordSet", "keywords count presence_id")
        keysets = []
        for kw_set in counter:
            kw_hash = hash(kw_set)
            if one[kw_hash]:
                keysets.append(
                    KeywordSet(
                        keywords=kw_set,
                        count=len(set(two[kw_hash])),
                        presence_id=one[kw_hash],
                    )
                )
        return keysets

    def get_tags_with_extracted_text(self, doc_id=None, tag_id=None):
        extracted_list_presences = (
            ExtractedListPresence.objects.prefetch_related("tags")
            .select_related("extracted_text")
            .filter(dsstox=self)
        )
        tagsets = {}
        for extracted_list_presence in extracted_list_presences:
            if extracted_list_presence.tags.exists() and (
                (
                    not tag_id
                    or tag_id
                    in extracted_list_presence.tags.values_list("pk", flat=True)
                )
                and (not doc_id or doc_id == extracted_list_presence.extracted_text.pk)
            ):
                tagset_dict = tagsets.get(frozenset(extracted_list_presence.tags.all()))
                if tagset_dict:
                    rid_list = tagset_dict.get(extracted_list_presence.extracted_text)
                    if rid_list:
                        rid_list.append(extracted_list_presence)
                    else:
                        tagset_dict.update(
                            {
                                extracted_list_presence.extracted_text: [
                                    extracted_list_presence
                                ]
                            }
                        )
                else:
                    tagsets.update(
                        {
                            frozenset(extracted_list_presence.tags.all()): {
                                extracted_list_presence.extracted_text: [
                                    extracted_list_presence
                                ]
                            }
                        }
                    )
        # Transform the data to be more manageable.
        tagset_list = []
        for tags, values in tagsets.items():
            tagset_list.append(
                {
                    "tags": tags,
                    "related": [
                        {"extracted_text": key, "extracted_list_presence": value}
                        for key, value in values.items()
                    ],
                }
            )
        return tagset_list

    def get_puc_list(self, kind=None):
        """
        Return a queryset of all the PUCs associated with the DTXSID,
        annotated with their counts. Observes the uberpuc assignments.
        """
        pucs = PUC.objects.filter(
            productuberpuc__product__in=Product.objects.filter(
                productdocument__document__extractedtext__rawchem__dsstox=self
            )
        ).annotate(product_count=models.Count("productuberpuc"))
        if kind:
            pucs = pucs.filter(kind=kind)
        return pucs.values_list(
            "id", "kind_id", "gen_cat", "prod_fam", "prod_type", "product_count"
        )
