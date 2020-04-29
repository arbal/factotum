import datetime
import factory
from django.db import IntegrityError

from dashboard import models


class FactotumFactoryBase(factory.django.DjangoModelFactory):
    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """
        This is an override to handle integrity errors with key "name".
        Name is a unique key and while it's rare that you will end up using the
        same word twice with faker for two different tags if a model fails to
        build it will simply retry.

        TODO: related_factories are double created

        :return: saved model instance
        """
        try:
            obj = super()._create(model_class, *args, **kwargs)
        except IntegrityError:
            obj = cls.simple_generate(create=True)
        return obj


class DataSourceFactory(FactotumFactoryBase):
    class Meta:
        model = models.DataSource


class PUCFactory(FactotumFactoryBase):
    class Meta:
        model = models.PUC

    kind = factory.Iterator(choice[0] for choice in models.PUC.KIND_CHOICES)
    gen_cat = factory.Faker("word")
    prod_fam = factory.Faker("word")
    prod_type = factory.Faker("word")
    description = factory.Faker("text")


class GroupTypeFactory(FactotumFactoryBase):
    class Meta:
        model = models.GroupType
        django_get_or_create = ("code",)

    code = "CO"


class DataGroupFactory(FactotumFactoryBase):
    class Meta:
        model = models.DataGroup

    data_source = factory.SubFactory(DataSourceFactory)
    group_type = factory.SubFactory(GroupTypeFactory)
    downloaded_at = datetime.datetime.utcnow()


class DocumentTypeFactory(FactotumFactoryBase):
    class Meta:
        model = models.DocumentType
        django_get_or_create = ("code",)

    title = factory.Faker("word")
    description = factory.Faker("paragraph")
    # Default type - unknown (compatible with all document types)
    code = "UN"


class DataDocumentFactory(FactotumFactoryBase):
    class Meta:
        model = models.DataDocument

    data_group = factory.SubFactory(DataGroupFactory)
    document_type = factory.SubFactory(DocumentTypeFactory)

    # document_type_compatibility = factory.RelatedFactory()


class ScriptFactory(FactotumFactoryBase):
    class Meta:
        model = models.Script


class ExtractedTextFactory(FactotumFactoryBase):
    class Meta:
        model = models.ExtractedText

    data_document = factory.SubFactory(DataDocumentFactory)
    extraction_script = factory.SubFactory(ScriptFactory)


class ExtractedHabitsAndPracticesDataTypeFactory(FactotumFactoryBase):
    class Meta:
        model = models.ExtractedHabitsAndPracticesDataType

    title = factory.Faker("word")
    description = factory.Faker("text", max_nb_chars=255)


class ExtractedHabitsAndPracticesTagKindFactory(FactotumFactoryBase):
    class Meta:
        model = models.ExtractedHabitsAndPracticesTagKind

    name = factory.Faker("word")

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """
        This is an override to handle integrity errors with key "name".
        Name is a unique key and while it's rare that you will end up using the
        same word twice with faker for two different tags if a model fails to
        build it will simply retry.

        This could probably be built into our base DjangoModelFactory

        :return: saved model instance
        """
        obj = model_class(*args, **kwargs)
        try:
            obj.save()
        except IntegrityError:
            obj = cls()
        return obj


class ExtractedHabitsAndPracticesTagFactory(FactotumFactoryBase):
    class Meta:
        model = models.ExtractedHabitsAndPracticesTag

    definition = factory.Faker("word")
    name = factory.Faker("word")
    kind = factory.SubFactory(ExtractedHabitsAndPracticesTagKindFactory)


class ExtractedHabitsAndPracticesFactory(FactotumFactoryBase):
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


class ExtractedHabitsAndPracticesToTagFactory(FactotumFactoryBase):
    class Meta:
        model = models.ExtractedHabitsAndPracticesToTag

    content_object = factory.SubFactory(ExtractedHabitsAndPracticesFactory)
    tag = factory.SubFactory(ExtractedHabitsAndPracticesTagFactory)
