from crum import get_current_user
from django.contrib.auth.models import AnonymousUser
from django.db import models
from django.db.backends.signals import connection_created
from django.db.models.signals import post_delete, pre_save, pre_delete, post_save
from django.dispatch import receiver

from dashboard.models import (
    ProductToPUC,
    ProductToTag,
    PUCToTag,
    RawChem,
    ExtractedComposition,
    ExtractedListPresence,
    ExtractedFunctionalUse,
    DataDocument,
    DocumentTypeGroupTypeCompatibilty,
    Product,
    ProductDocument,
    CommonInfo,
)


# When dissociating a product from a PUC, delete it's (PUC-dependent) tags
@receiver(pre_delete, sender=ProductToPUC)
def delete_product_puc_tags(sender, **kwargs):
    instance = kwargs["instance"]
    ProductToTag.objects.filter(content_object=instance.product).delete()


# When dissociating a product from a PUC, update the uberpuc for that product ID
@receiver(post_delete, sender=ProductToPUC)
def update_uber_puc_on_delete(sender, **kwargs):
    instance = kwargs["instance"]
    instance.update_uber_puc()


@receiver(post_save, sender=ProductToPUC)
def update_uber_puc_on_save(sender, **kwargs):
    instance = kwargs["instance"]
    instance.update_uber_puc()


# When dissociating a puc from a tag, also disocciate any puc-related products from that tag
@receiver(post_delete, sender=PUCToTag)
def delete_related_product_tags(sender, **kwargs):
    instance = kwargs["instance"]
    products = instance.content_object.products.all()
    products_to_tags = ProductToTag.objects.filter(tag=instance.tag).filter(
        content_object__in=products
    )
    products_to_tags.delete()


@receiver(pre_save, sender=RawChem)
@receiver(pre_save, sender=ExtractedComposition)
@receiver(pre_save, sender=ExtractedListPresence)
@receiver(pre_save, sender=ExtractedFunctionalUse)
def uncurate(sender, **kwargs):
    instance = kwargs.get("instance")
    watched_keys = {"raw_cas", "raw_chem_name"}
    if not instance._state.adding and not instance.tracker.changed().keys().isdisjoint(
        watched_keys
    ):
        instance.dsstox = None
        instance.rid = ""


@receiver(post_delete, sender=DocumentTypeGroupTypeCompatibilty)
def rm_invalid_doctypes(sender, **kwargs):
    """When a DocumentTypeGroupTypeCompatibilty is dropped, the newly invalid DocumentType
    fields of affected DataDocuments need to be made unidentified.
    """
    compat_obj = kwargs["instance"]
    doc_type = compat_obj.document_type
    group_type = compat_obj.group_type
    (
        DataDocument.objects.filter(
            document_type=doc_type, data_group__group_type=group_type
        ).update(document_type=doc_type._meta.model.objects.get(code="UN"))
    )


@receiver(models.signals.post_delete, sender=ProductDocument)
def auto_delete_orphaned_products_on_delete(sender, instance, **kwargs):
    """
    Checks for orphaned products on ProductDocument delete.
    Because products can be associated with multiple data documents,
    this check needs to make sure there are no other ProductDocument
    relationships before deleting the Product
    """
    pid = instance.product_id
    if ProductDocument.objects.filter(product_id=pid).count() == 0:
        try:
            instance.product.delete()
        except Product.DoesNotExist:
            pass
        else:
            pass


@receiver(connection_created)
def new_connection(sender, connection, **kwargs):
    user = get_current_user()
    # set current user for the session
    if user:
        connection.cursor().execute("SET @current_user = %s", [user.id])


@receiver(pre_save)
def populate_user_fields(sender, instance=None, **kwargs):
    user = get_current_user()
    if not isinstance(user, AnonymousUser) and issubclass(sender, CommonInfo):
        if not instance.pk:
            instance.created_by = user
        instance.updated_by = user
