from collections import namedtuple
from django.db import models
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .common_info import CommonInfo
from .product_document import ProductDocument
from .PUC import PUC
from .extracted_list_presence import ExtractedListPresence
from .data_document import DataDocument
from .group_type import GroupType


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

    @property
    def puc_count(self):
        pdocs = ProductDocument.objects.from_chemical(self)
        return PUC.objects.filter(products__in=pdocs.values("product")).count()

    @property
    def cumulative_puc_count(self):
        pdocs = ProductDocument.objects.from_chemical(self)
        pucs = PUC.objects.filter(products__in=pdocs.values("product"))
        titles = []
        for puc in pucs:
            titles += list(f for f in (puc.gen_cat, puc.prod_fam, puc.prod_type) if f)
        return len(set(titles))

    def puc_count_by_kind(self, kind):
        pdocs = ProductDocument.objects.from_chemical(self)
        pucs = PUC.objects.filter(products__in=pdocs.values("product")).filter(
            kind=kind
        )
        return pucs.count()

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
