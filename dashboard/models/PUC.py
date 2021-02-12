from django.db import models
from django.apps import apps
from django.db.models import F, Q
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
    gen_cat = models.CharField(
        max_length=50, blank=False, help_text="general category", db_index=True
    )
    prod_fam = models.CharField(
        max_length=50, blank=True, default="", help_text="product family", db_index=True
    )
    prod_type = models.CharField(
        max_length=100, blank=True, default="", help_text="product type", db_index=True
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
        return u", ".join(o.name for o in obj.tags.all())

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
        """ 
        """
        return self.products_per_puc.product_count

    @property
    def cumulative_product_count(self):
        # return self.cumulative_products_per_puc.cumulative_product_count
        ProductToPUC = apps.get_model("dashboard", "ProductUberPuc")
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
        return DataDocument.objects.filter(
            Q(products__product_uber_puc__puc=self)
        ).count()

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
