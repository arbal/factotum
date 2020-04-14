import datetime
import factory

from dashboard import models


class DataSourceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.DataSource


class PUCFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.PUC

    kind = factory.Iterator(choice[0] for choice in models.PUC.KIND_CHOICES)
    gen_cat = factory.Faker("word")
    prod_fam = factory.Faker("word")
    prod_type = factory.Faker("word")
    description = factory.Faker("text")


class GroupTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.GroupType
        django_get_or_create = ("code",)

    code = "CO"


class DataGroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.DataGroup

    data_source = factory.SubFactory(DataSourceFactory)
    group_type = factory.SubFactory(GroupTypeFactory)
    downloaded_at = datetime.datetime.utcnow()


class DocumentTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.DocumentType
        django_get_or_create = ("code",)

    # Default type - unknown (compatible with all document types)
    code = "UN"


class DataDocumentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.DataDocument

    data_group = factory.SubFactory(DataGroupFactory)
    document_type = factory.SubFactory(DocumentTypeFactory)

    # document_type_compatibility = factory.RelatedFactory()


class ScriptFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Script


class ExtractedTextFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.ExtractedText

    data_document = factory.SubFactory(DataDocumentFactory)
    extraction_script = factory.SubFactory(ScriptFactory)


class ExtractedHabitsAndPracticesDataTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.ExtractedHabitsAndPracticesDataType


class ExtractedHabitsAndPracticesTagKindFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.ExtractedHabitsAndPracticesTagKind

    name = factory.Faker("word")


class ExtractedHabitsAndPracticesTagFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.ExtractedHabitsAndPracticesTag

    definition = factory.Faker("word")
    name = factory.Faker("word")
    kind = factory.SubFactory(ExtractedHabitsAndPracticesTagKindFactory)


class ExtractedHabitsAndPracticesFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.ExtractedHabitsAndPractices

    product_surveyed = factory.Faker("word")
    notes = factory.Faker("paragraph")
    extracted_text = factory.SubFactory(
        ExtractedTextFactory, data_document__data_group__group_type__code="HP"
    )
    data_type = factory.SubFactory(ExtractedHabitsAndPracticesDataTypeFactory)

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if extracted:
            # Add the list of tags that were passed in
            for tag in extracted:
                self.tags.add(tag)

    @factory.post_generation
    def PUCs(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if extracted:
            # Add the list of PUCs that were passed in
            for puc in extracted:
                self.PUCs.add(puc)


class ExtractedHabitsAndPracticesToTagFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.ExtractedHabitsAndPracticesToTag

    content_object = factory.SubFactory(ExtractedHabitsAndPracticesFactory)
    tag = factory.SubFactory(ExtractedHabitsAndPracticesTagFactory)
