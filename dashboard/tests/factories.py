import datetime
import factory
from django.db import IntegrityError
import random
from dashboard import models
from faker.providers import BaseProvider


class ChemicalProvider(BaseProvider):
    def cas_number(self):
        """
        Returns a CAS string
        """
        seg1 = self.generator.random.randrange(10, 9999999)
        seg2 = self.generator.random.randrange(10, 99)
        seg3 = self.generator.random.randrange(0, 9)
        return f"{seg1}-{seg2}-{seg3}"

    def sid(self):
        """
        Returns a DTXSID
        """
        seg1 = "DTXSID"
        seg2 = str(random.randint(0, 9999999)).rjust(7, "0")
        return f"{seg1}{seg2}"


factory.Faker.add_provider(ChemicalProvider)


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

    title = factory.Faker("word")


class UnitTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.UnitType

    title = factory.Faker("word")
    description = factory.Faker("text")


class WeightFractionTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.WeightFractionType

    title = factory.Faker("word")
    description = factory.Faker("text")


class ExtractedTextFactory(FactotumFactoryBase):
    class Meta:
        model = models.ExtractedText

    data_document = factory.SubFactory(DataDocumentFactory)
    extraction_script = factory.SubFactory(ScriptFactory, script_type="EX")


class TrueChemicalFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.DSSToxLookup

    sid = factory.Faker("sid")
    true_cas = factory.Faker("cas_number")
    true_chemname = factory.Faker("word")


class FunctionalUseCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.FunctionalUseCategory

    title = factory.Faker("word")
    description = factory.Faker("text", max_nb_chars=255)


class FunctionalUseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.FunctionalUse

    category = factory.SubFactory(FunctionalUseCategoryFactory)
    report_funcuse = factory.Faker("word")
    clean_funcuse = factory.Faker("word")
    # extraction_script = factory.SubFactory(ScriptFactory)


class RawChemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.RawChem
        abstract = True

    class Params:
        is_curated = False

    raw_cas = factory.Faker("cas_number")
    raw_chem_name = factory.Faker("word")
    if factory.SelfAttribute("is_curated"):
        dsstox = factory.SubFactory(TrueChemicalFactory)

    @factory.post_generation
    def functional_uses(obj, create, extracted, **kwargs):
        """
        generates a functional use record for each RawChem created,
        more if a `functional_uses` argument is provided with a higher number
        """
        if not create:
            # Build, not create related
            return

        if extracted:
            for n in range(extracted):
                FunctionalUseFactory(chem=obj)
        else:
            import random

            number_of_units = random.randint(1, 3)
            for n in range(number_of_units):
                FunctionalUseFactory(chem=obj)


class ExtractedListPresenceFactory(RawChemFactory):
    class Meta:
        model = models.ExtractedListPresence

    extracted_text = factory.SubFactory(
        ExtractedTextFactory, data_document__data_group__group_type__code="CP"
    )

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if extracted:
            # Add the list of tags that were passed in
            for tag in extracted:
                self.tags.add(tag)


class ExtractedListPresenceTagKindFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.ExtractedListPresenceTagKind

    name = factory.Faker("word")


class ExtractedListPresenceTagFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.ExtractedListPresenceTag

    definition = factory.Faker("word")
    name = factory.Faker("word")
    kind = factory.SubFactory(ExtractedListPresenceTagKindFactory)


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


class ExtractedChemicalFactory(RawChemFactory):
    class Meta:
        model = models.ExtractedChemical

    extracted_text = factory.SubFactory(
        ExtractedTextFactory, data_document__data_group__group_type__code="CO"
    )
    raw_min_comp = factory.LazyAttribute(lambda o: random.randint(0, 50))
    raw_max_comp = factory.LazyAttribute(lambda o: random.randint(50, 100))
    unit_type = factory.SubFactory(UnitTypeFactory)
    weight_fraction_type = factory.SubFactory(WeightFractionTypeFactory)
    component = factory.Faker("word")
    ingredient_rank = factory.LazyAttribute(lambda o: random.randint(1, 999))
    lower_wf_analysis = factory.LazyAttribute(lambda o: 0.5 - random.random() / 2)
    upper_wf_analysis = factory.LazyAttribute(lambda o: 0.5 + random.random() / 2)


class ExtractedFunctionalUseFactory(RawChemFactory):
    class Meta:
        model = models.ExtractedFunctionalUse

    extracted_text = factory.SubFactory(
        ExtractedTextFactory, data_document__data_group__group_type__code="FU"
    )


class ExtractedHHDocFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.ExtractedHHDoc

    extracted_text = factory.SubFactory(
        ExtractedTextFactory, data_document__data_group__group_type__code="HH"
    )


class ExtractedHHRecFactory(RawChemFactory):
    class Meta:
        model = models.ExtractedHHRec

    extracted_text = factory.SubFactory(
        ExtractedTextFactory, data_document__data_group__group_type__code="HH"
    )
