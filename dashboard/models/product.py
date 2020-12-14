from taggit.managers import TaggableManager

from django.apps import apps
from django.db import models
from django.urls import reverse
from django.db.models import Max, Prefetch
from django.core.exceptions import ValidationError

from factotum.environment import env
from .common_info import CommonInfo
from .extracted_text import ExtractedText
from .data_source import DataSource
from .source_category import SourceCategory
from dashboard.utils import uuid_file, get_model_next_pk


def validate_product_image_size(image):
    if image.size > env.PRODUCT_IMAGE_MAX_SIZE:
        raise ValidationError(
            "Max size of file is %s MB" % (env.PRODUCT_IMAGE_MAX_SIZE / 1000000)
        )


class ProductQuerySet(models.QuerySet):
    # This does not work when no product exists
    # def next_upc(self):
    #     return "stub_" + str(Product.objects.all().aggregate(Max("id"))["id__max"] + 1)

    def prefetch_pucs(self):
        """Prefetch PUCs to make Product.uber_puc use less SQL calls"""
        ProductToPUC = apps.get_model("dashboard", "ProductToPUC")
        return self.prefetch_related(
            Prefetch(
                "producttopuc_set", queryset=ProductToPUC.objects.select_related("puc")
            )
        )


class Product(CommonInfo):
    documents = models.ManyToManyField(
        through="dashboard.ProductDocument",
        to="dashboard.DataDocument",
        help_text=("Data Documents related to this Product"),
    )
    tags = TaggableManager(
        through="dashboard.ProductToTag",
        to="dashboard.PUCTag",
        help_text=("A set of PUC Tags applicable " "to this Product"),
    )
    source_category = models.ForeignKey(
        SourceCategory,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text=("The category assigned in " "the product's data source"),
    )
    title = models.CharField(max_length=255)
    manufacturer = models.CharField(
        db_index=True, max_length=250, blank=True, default="", help_text="title"
    )
    upc = models.CharField(
        db_index=True,
        max_length=60,
        null=False,
        blank=False,
        unique=True,
        help_text="UPC",
    )
    url = models.CharField(
        max_length=500, blank=True, verbose_name="Product URL", help_text="Product URL"
    )
    brand_name = models.CharField(
        db_index=True, max_length=200, blank=True, default="", help_text="brand name"
    )
    size = models.CharField(max_length=100, blank=True, help_text="size")
    model_number = models.CharField(
        max_length=200, blank=True, help_text="model number"
    )
    color = models.CharField(max_length=100, blank=True, help_text="color")
    item_id = models.IntegerField(null=True, blank=True, help_text="item ID")
    parent_item_id = models.IntegerField(
        null=True, blank=True, help_text="parent item ID"
    )
    short_description = models.TextField(blank=True, help_text="short description")
    long_description = models.TextField(blank=True, help_text="long description")
    epa_reg_number = models.CharField(
        blank=True,
        max_length=25,
        verbose_name="EPA Reg. No.",
        help_text="the document's EPA registration number",
    )
    thumb_image = models.CharField(
        max_length=500, blank=True, help_text="thumbnail image"
    )
    medium_image = models.CharField(
        max_length=500, blank=True, help_text="medium image"
    )
    large_image = models.CharField(max_length=500, blank=True, help_text="large image")
    image = models.ImageField(
        help_text="The product's image file",
        upload_to=uuid_file,
        validators=[validate_product_image_size],
        blank=True,
        null=True,
    )
    objects = ProductQuerySet.as_manager()

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("product_detail", kwargs={"pk": self.pk})

    def product_to_predicted_puc(self):
        return self.producttopuc_set.filter(classification_method_id="AU").first()

    @property
    def get_producttopuc(self):
        """Returns the "producttopuc" for this product with the
        lowest `classification_method.rank` value. If there are
        multiple product-to-puc assignments with the same low-scoring
        classification method, the `first()` will return an arbitrary
        choice. There is no tiebreaking logic yet.

        To reduce SQL calls, prefetch this result with
            Product.objects.prefetch_pucs()
        """
        return self.producttopuc_set.order_by("classification_method__rank").first()

    @property
    def uber_puc(self):
        producttopuc = self.get_producttopuc
        if producttopuc:
            return producttopuc.puc
        return None

    @property
    def get_classification_method(self):
        producttopuc = self.get_producttopuc
        if producttopuc:
            return producttopuc.classification_method
        return None

    def get_tag_list(self):
        return u", ".join(o.name for o in self.tags.all())

    # returns list of valid puc_tags
    def get_puc_tag_list(self):
        all_uber_tags = self.uber_puc.tags.all()
        return u", ".join(o.name for o in all_uber_tags)

    # returns set of valid puc_tags
    def get_puc_tags(self):
        if self.uber_puc:
            return self.uber_puc.tags.all()
        else:
            return []

    def save(self, *args, **kwargs):
        if not self.upc:
            # mint a new stub_x UPC if there was none provided
            self.upc = "stub_" + str(get_model_next_pk(Product))
        super(Product, self).save(*args, **kwargs)

    @property
    def rawchems(self):
        """A generator of all RawChem objects in this product

        It's recommended to first "prefetch_related" the RawChem objects:
            Product.objects.prefetch_related("datadocument_set__extractedtext__rawchem")
        """
        for doc in self.datadocument_set.all():
            try:
                yield from doc.extractedtext.rawchem.all()
            except ExtractedText.DoesNotExist:
                pass

    class Meta:
        ordering = ["-created_at"]


class DuplicateProduct(Product):
    """
    A model for storing product records whose UPCs already exist in the database
    """

    source_upc = models.CharField(
        db_index=True,
        max_length=60,
        null=False,
        blank=False,
        unique=False,
        help_text="Source UPC",
    )
