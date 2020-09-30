from django.apps import apps
from django.db import models
from itertools import chain
from django.db.models import (
    Count,
    F,
    Q,
    Subquery,
    OuterRef,
    IntegerField,
    Case,
    When,
    Value,
    Window,
)

from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from taggit.managers import TaggableManager
from taggit.models import TaggedItemBase, TagBase

from dashboard.models import ProductDocument, DataDocument
from dashboard.utils import GroupConcat, SimpleTree
from .common_info import CommonInfo
from .raw_chem import RawChem


class PUCQuerySet(models.QuerySet):
    def dtxsid_filter(self, sid):
        """ Returns a QuerySet of PUCs with a product containing a chemical.

        Arguments:
            ``sid``
                a DTXSID sid string
        """
        return self.filter(
            products__datadocument__extractedtext__rawchem__dsstox__sid=sid
        )

    def with_num_products(self):
        """ Returns a QuerySet of PUCs with each PUC's product count
        and each prod_fam (parent) and gen_cat (grandparent) record's 
        cumulative product count

        The product count for the PUC is annotated as 'num_products'
        The cumulative product count for all PUCs sharing the gen_cat
        or prod_fam string is rolled up into cumulative_products.

        This manager can be applied subsequent to .dtxsid_filter(), as used
        on the chemical detail page
        """

        # Counting the products per puc.gen_cat and puc.prod_fam is a Window
        # query, but window functions were not added to MySQL until version 8.
        # Factotum currently uses version 5.

        # pucs = apps.get_model(
        #     app_label="dashboard", model_name="ProductToPUC"
        # ).objects.annotate(
        #     cumulative_gc=Window(
        #         expression=Count("product", distinct=True),
        #         partition_by=[F("puc__kind"), F("puc__gen_cat")],
        #         output_field=IntegerField()
        #     ),
        #     cumulative_pf=Window(
        #         expression=Count("product", distinct=True),
        #         partition_by=[F("puc__kind"), F("puc__gen_cat"), F("puc__prod_fam")],
        #         output_field=IntegerField()
        #     )
        # )

        # The PUC queryset may have already been filtered, so the counts
        # need to be performed on a set of ProductToPUC records that reflects
        # only what overlaps with `self`
        pucs = self

        product_pucs = apps.get_model(
            app_label="dashboard", model_name="ProductToPUC"
        ).objects.filter(puc__in=pucs)

        # Perform a separate query for each level of the hierarchy

        # The parent and grandparent queries have to start from scratch because they need
        # to include any PUCs with no products but whose children have products
        gen_cats = (
            PUC.objects.filter(Q(prod_type__exact="") & Q(prod_fam__exact=""))
            .filter(gen_cat__in=product_pucs.values("puc__gen_cat"))
            .filter(kind__in=pucs.values("kind"))
        )

        # get a simple aggregation of distinct puc_id per grandparent field
        products_per_gen_cat = product_pucs.values(
            "puc__kind", "puc__gen_cat"
        ).annotate(cumulative_products=Count("product", distinct=True))

        # turn that aggregation into a subquery, joining with the parent field as an OuterRef
        gen_cat_sub = products_per_gen_cat.filter(
            puc__kind=OuterRef("kind"), puc__gen_cat=OuterRef("gen_cat")
        ).values("cumulative_products")

        gen_cats = gen_cats.annotate(
            num_products=Count("products", distinct=True)
        ).annotate(
            cumulative_products=Subquery(gen_cat_sub, output_field=IntegerField())
        )

        # print("gen_cats")
        # print("--------")
        # for puc in gen_cats:
        #     print(
        #         f"{puc.id} :: {puc} :: {puc.cumulative_products} :: {puc.num_products}"
        #     )

        # Repeat the query at the parent (prod_fam) level
        prod_fams = (
            PUC.objects.filter(Q(prod_type__exact="") & ~Q(prod_fam__exact=""))
            .filter(prod_fam__in=product_pucs.values("puc__prod_fam"))
            .filter(kind__in=pucs.values("kind"))
        )

        # annotate the prod_fam records with their cumulative product counts
        products_per_prod_fam = (
            product_pucs.exclude(puc__prod_fam="")
            .values("puc__kind", "puc__prod_fam")
            .annotate(cumulative_products=Count("product", distinct=True))
        )

        # turn that aggregation into a subquery, joining with the parent field
        # as an OuterRef
        prod_fam_sub = products_per_prod_fam.filter(
            puc__kind=OuterRef("kind"), puc__prod_fam=OuterRef("prod_fam")
        ).values("cumulative_products")

        prod_fams = (
            prod_fams.annotate(num_products=Count("products", distinct=True))
            .annotate(
                cumulative_products=Subquery(prod_fam_sub, output_field=IntegerField())
            )
        )

        # print("prod_fams")
        # print("----")
        # for puc in prod_fams:
        #     print(
        #         f"{puc.id} :: {puc} :: {puc.cumulative_products} :: {puc.num_products}"
        #     )
        # annotate the child-only PUC queryset with the per-PUC product counts
        pucs = (
            pucs.filter(~Q(prod_type__exact=""))
            .annotate(num_products=Count("products", distinct=True))
            .filter(num_products__gt=0)
            .annotate(cumulative_products=Count("products", distinct=True))
        )

        # print("pucs")
        # print("----")
        # for puc in pucs:
        #     print(
        #         f"{puc.id} :: {puc} :: {puc.cumulative_products} :: {puc.num_products}"
        #     )

        # print("-----------------")
        # print("  gen_cats.union(prod_fams, pucs) ")
        # for puc in gen_cats.union(prod_fams, pucs):
        #     print(
        #         f"{puc.id} :: {puc} :: {puc.cumulative_products} :: {puc.num_products}"
        #     )

        # return parents.union(pucs)
        return gen_cats.union(prod_fams, pucs)

    def with_allowed_attributes(self):
        """ Returns a QuerySet of PUCs with an allowed tags string.

        The allowed tags string is annotated as 'allowed_attributes'
        """
        return self.annotate(
            allowed_attributes=GroupConcat("tags__name", separator="; ", distinct=True)
        )

    def with_assumed_attributes(self):
        """ Returns a QuerySet of PUCs with an assumed tags string.

        The assumed tags string is annotated as 'assumed_attributes'
        """
        return self.annotate(
            assumed_attributes=GroupConcat(
                "tags__name",
                separator="; ",
                distinct=True,
                filter=Q(puctotag__assumed=True),
            )
        )

    def astree(self, include=None):
        """ Returns a SimpleTree representation of a PUC queryset.
        """
        tree = SimpleTree()
        for puc in self:
            if isinstance(puc, dict):
                names = tuple(
                    n for n in (puc["gen_cat"], puc["prod_fam"], puc["prod_type"]) if n
                )
            elif isinstance(puc, self.model):
                names = tuple(
                    n for n in (puc.gen_cat, puc.prod_fam, puc.prod_type) if n
                )
            tree[names] = puc
        return tree


class PUC(CommonInfo):
    kind = models.ForeignKey(
        "dashboard.PUCKind", on_delete=models.CASCADE, default=1, help_text="kind"
    )
    gen_cat = models.CharField(max_length=50, blank=False, help_text="general category")
    prod_fam = models.CharField(
        max_length=50, blank=True, default="", help_text="product family"
    )
    prod_type = models.CharField(
        max_length=100, blank=True, default="", help_text="product type"
    )
    description = models.TextField(null=False, blank=False, help_text="PUC description")
    last_edited_by = models.ForeignKey(
        "auth.User", on_delete=models.CASCADE, default=1, help_text="last edited by"
    )
    products = models.ManyToManyField(
        "Product", through="ProductToPUC", help_text="products assigned to this PUC"
    )
    extracted_habits_and_practices = models.ManyToManyField(
        "dashboard.ExtractedHabitsAndPractices",
        through="dashboard.ExtractedHabitsAndPracticesToPUC",
        help_text=("extracted Habits and Practices " "records assigned to this PUC"),
    )
    tags = TaggableManager(
        through="dashboard.PUCToTag",
        to="dashboard.PUCTag",
        blank=True,
        help_text="A set of PUC Attributes applicable to this PUC",
    )
    objects = PUCQuerySet.as_manager()

    class JSONAPIMeta:
        resource_name = "puc"

    class Meta:
        ordering = ["gen_cat", "prod_fam", "prod_type"]
        verbose_name_plural = "PUCs"

    def __str__(self):
        cats = [self.gen_cat, self.prod_fam, self.prod_type]
        return " - ".join(cat for cat in cats if cat)

    def natural_key(self):
        return self.gen_cat

    def tag_list(self, obj):
        return ", ".join(o.name for o in obj.tags.all())

    def get_level(self):
        if self.is_level_one:
            return 1
        if self.is_level_two:
            return 2
        else:
            return 3

    @property
    def is_level_one(self):  # gen_cat only
        return self.prod_fam == "" and self.prod_type == ""

    @property
    def is_level_two(self):  # no prod_type
        return not self.prod_fam == "" and self.prod_type == ""

    @property
    def is_level_three(self):  # most granular PUC
        return not self.prod_fam == "" and not self.prod_type == ""

    def get_children(self):
        if self.is_level_one:
            return PUC.objects.filter(gen_cat=self.gen_cat)
        if self.is_level_two:
            return PUC.objects.filter(gen_cat=self.gen_cat, prod_fam=self.prod_fam)
        if self.is_level_three:
            return PUC.objects.filter(pk=self.pk)

    def get_parent_ids(self):
        if self.is_level_one:
            return [self.pk, 0, 0]
        if self.is_level_two:
            gen_cat_puc = PUC.objects.filter(
                gen_cat=self.gen_cat, prod_fam="", prod_type=""
            ).first()
            return [gen_cat_puc.pk, self.pk, 0]
        if self.is_level_three:
            gen_cat_puc = PUC.objects.filter(
                gen_cat=self.gen_cat, prod_fam="", prod_type=""
            ).first()
            prod_fam_puc = PUC.objects.filter(
                gen_cat=self.gen_cat, prod_fam=self.prod_fam, prod_type=""
            ).first()
            return [gen_cat_puc.pk, prod_fam_puc.pk, self.pk]

    @property
    def product_count(self):
        """Don't use this in large querysets. It uses a SQL query for each 
        PUC record. """
        return self.products.count()

    @property
    def cumulative_product_count(self):
        ProductToPUC = apps.get_model("dashboard", "ProductToPUC")
        if self.is_level_one:
            return ProductToPUC.objects.filter(puc__gen_cat=self.gen_cat).count()
        if self.is_level_two:
            return ProductToPUC.objects.filter(puc__prod_fam=self.prod_fam).count()
        if self.is_level_three:
            return ProductToPUC.objects.filter(puc=self).count()

    @property
    def curated_chemical_count(self):
        docs = ProductDocument.objects.filter(product__in=self.products.all())
        return (
            RawChem.objects.filter(
                extracted_text__data_document__in=docs.values_list(
                    "document", flat=True
                ),
                dsstox__isnull=False,
            )
            .values("dsstox")
            .distinct()
            .count()
        )

    @property
    def document_count(self):
        return DataDocument.objects.filter(Q(products__puc=self)).distinct().count()

    @property
    def admin_url(self):
        return reverse("admin:dashboard_puc_change", args=(self.pk,))

    def get_absolute_url(self):
        return reverse("puc_detail", args=(self.pk,))

    def get_assumed_tags(self):
        """Queryset of PUC tags a Product is assumed to have """
        qs = PUCToTag.objects.filter(content_object=self, assumed=True)
        return PUCTag.objects.filter(dashboard_puctotag_items__in=qs)

    def get_allowed_tags(self):
        """Queryset of PUC tags a Product is allowed to have """
        qs = PUCToTag.objects.filter(content_object=self, assumed=False)
        return PUCTag.objects.filter(dashboard_puctotag_items__in=qs)

    def get_linked_taxonomies(self):
        from dashboard.models import Taxonomy

        return (
            Taxonomy.objects.filter(product_category=self)
            .annotate(source_title=F("source__title"))
            .annotate(source_description=F("source__description"))
        )


class PUCToTag(TaggedItemBase, CommonInfo):
    content_object = models.ForeignKey(PUC, on_delete=models.CASCADE)
    tag = models.ForeignKey(
        "PUCTag", on_delete=models.CASCADE, related_name="%(app_label)s_%(class)s_items"
    )
    assumed = models.BooleanField(default=False)

    def __str__(self):
        return str(self.tag)

    class Meta:
        unique_together = ["content_object", "tag"]
        verbose_name = _("PUC Tag")
        verbose_name_plural = _("PUC Tags")


class PUCTag(TagBase, CommonInfo):
    definition = models.TextField(blank=True, max_length=255)

    class Meta:
        verbose_name = _("PUC Attribute")
        verbose_name_plural = _("PUC Attributes")
        ordering = ("name",)

    def __str__(self):
        return self.name


class PUCKind(CommonInfo):
    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=2, unique=True, null=True, blank=True)

    class Meta:
        verbose_name = _("PUC kind")
        verbose_name_plural = _("PUC kinds")

    def __str__(self):
        return str(self.code)
