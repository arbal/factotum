from dal_select2.widgets import ModelSelect2
from django import forms
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from taggit_labels.widgets import LabelWidget

from dashboard.models import (
    PUC,
    PUCTag,
    Script,
    DocumentType,
    DataSource,
    GroupType,
    DataGroup,
    DataDocument,
    Product,
    ProductToPUC,
    ProductToPucClassificationMethod,
    ProductDocument,
    SourceCategory,
    PUCKind,
    ExtractedText,
    ExtractedComposition,
    ExtractedFunctionalUse,
    ExtractedHabitsAndPractices,
    ExtractedHabitsAndPracticesDataType,
    ExtractedHabitsAndPracticesTagKind,
    ExtractedHabitsAndPracticesTag,
    DSSToxLookup,
    QAGroup,
    UnitType,
    WeightFractionType,
    Taxonomy,
    TaxonomySource,
    TaxonomyToPUC,
    ExtractedHHDoc,
    ExtractedHHRec,
    PUCToTag,
    ExtractedListPresence,
    ExtractedListPresenceTag,
    ExtractedListPresenceToTag,
    ExtractedListPresenceTagKind,
    FunctionalUse,
    FunctionalUseCategory,
    CurationStep,
    FunctionalUseToRawChem,
    ExtractedLMDoc,
    ExtractedLMRec,
    News,
    StatisticalValue,
)
from dashboard.models.extracted_lmrec import HarmonizedMedium


class PUCAdminForm(forms.ModelForm):
    class Meta:
        model = PUC
        fields = ["gen_cat", "prod_fam", "prod_type", "description", "tags", "kind"]
        readonly_fields = ("product_count", "cumulative_product_count")
        widgets = {"tags": LabelWidget(model=PUCTag)}


class PUCAdmin(admin.ModelAdmin):
    list_display = ("__str__", "tag_list")
    list_filter = ("kind",)
    form = PUCAdminForm

    def get_changeform_initial_data(self, request):
        get_data = super(PUCAdmin, self).get_changeform_initial_data(request)
        get_data["last_edited_by"] = request.user.pk
        return get_data

    def get_queryset(self, request):
        return super(PUCAdmin, self).get_queryset(request).prefetch_related("tags")

    def tag_list(self, obj):
        return u", ".join(o.name for o in obj.tags.all())


class PUCKindAdmin(admin.ModelAdmin):
    list_display = ("__str__", "name")


class ProductToPucClassificationMethodAdmin(admin.ModelAdmin):
    list_display = ("rank", "code", "name")


class HHDocAdmin(admin.ModelAdmin):
    list_display = ("__str__", "hhe_report_number")


class ScriptForm(forms.ModelForm):
    class Meta(object):
        model = Script
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(ScriptForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk and not self.instance.script_type == "EX":
            # Since the pk is set this is not a new instance
            self.fields["confidence"].widget = forms.HiddenInput()


class ScriptAdmin(admin.ModelAdmin):
    list_filter = ("script_type",)
    list_display = ("__str__", "confidence_level")
    form = ScriptForm

    def confidence_level(self, obj):
        if obj.script_type == "EX":
            return obj.confidence
        else:
            return ""


class ExtractedListPresenceToTagAdmin(admin.ModelAdmin):
    list_display = ("content_object", "tag")
    list_filter = ("tag",)

    def tag(self, obj):
        return obj.tag


class ExtractedListPresenceTagAdmin(admin.ModelAdmin):
    list_filter = ("kind",)


class ExtractedHabitsAndPracticesTagAdmin(admin.ModelAdmin):
    list_filter = ("kind",)


class PUCToTagAdmin(admin.ModelAdmin):
    list_display = ("content_object", "tag", "assumed")
    list_filter = ("tag",)

    def tag(self, obj):
        return obj.tag

    def assumed(self, obj):
        return obj.assumed


class DataGroupAdmin(admin.ModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            # All model fields as read_only
            return self.readonly_fields + tuple(["group_type"])
        return self.readonly_fields


class GroupTypeInline(admin.TabularInline):
    model = DocumentType.group_types.through
    extra = 0
    can_delete = True
    verbose_name = _("Compatible Group Type")
    verbose_name_plural = _("Compatible Group Types")


class DocumentTypeAdmin(admin.ModelAdmin):
    inlines = [GroupTypeInline]


class FunctionalUseAdmin(admin.ModelAdmin):
    list_display = ("report_funcuse", "category")
    list_filter = ("category",)


# Simple autocomplete form that will allow this page to load
# with any number of functional uses or chemicals.
class FunctionalUseToRawChemAdminForm(forms.ModelForm):
    class Meta:
        model = FunctionalUseToRawChem
        fields = ("chemical", "functional_use")
        widgets = {
            "chemical": ModelSelect2(url="chemical_autocomplete"),
            "functional_use": ModelSelect2(url="functional_use_autocomplete"),
        }


class FunctionalUseToRawChemAdmin(admin.ModelAdmin):
    list_display = ("chemical", "functional_use")
    form = FunctionalUseToRawChemAdminForm


# Register your models here.
admin.site.register(DataSource)
admin.site.register(GroupType)
admin.site.register(DataGroup, DataGroupAdmin)
admin.site.register(DocumentType, DocumentTypeAdmin)
admin.site.register(DataDocument)
admin.site.register(Script, ScriptAdmin)
admin.site.register(Product)
admin.site.register(ProductToPUC)
admin.site.register(
    ProductToPucClassificationMethod, ProductToPucClassificationMethodAdmin
)
admin.site.register(ProductDocument)
admin.site.register(SourceCategory)
admin.site.register(PUC, PUCAdmin)
admin.site.register(PUCKind, PUCKindAdmin)
admin.site.register(ExtractedText)
admin.site.register(ExtractedComposition)
admin.site.register(ExtractedFunctionalUse)
admin.site.register(ExtractedHabitsAndPractices)
admin.site.register(ExtractedHabitsAndPracticesDataType)
admin.site.register(ExtractedHabitsAndPracticesTagKind)
admin.site.register(ExtractedHabitsAndPracticesTag, ExtractedHabitsAndPracticesTagAdmin)
admin.site.register(DSSToxLookup)
admin.site.register(QAGroup)
admin.site.register(UnitType)
admin.site.register(WeightFractionType)
admin.site.register(PUCTag)
admin.site.register(Taxonomy)
admin.site.register(TaxonomySource)
admin.site.register(TaxonomyToPUC)
admin.site.register(ExtractedHHDoc, HHDocAdmin)
admin.site.register(ExtractedHHRec)
admin.site.register(ExtractedLMDoc)
admin.site.register(ExtractedLMRec)
admin.site.register(StatisticalValue)
admin.site.register(HarmonizedMedium)
admin.site.register(PUCToTag, PUCToTagAdmin)
admin.site.register(ExtractedListPresence)
admin.site.register(ExtractedListPresenceTag, ExtractedListPresenceTagAdmin)
admin.site.register(ExtractedListPresenceToTag, ExtractedListPresenceToTagAdmin)
admin.site.register(ExtractedListPresenceTagKind)
admin.site.register(FunctionalUse, FunctionalUseAdmin)
admin.site.register(FunctionalUseToRawChem, FunctionalUseToRawChemAdmin)
admin.site.register(FunctionalUseCategory)
admin.site.register(CurationStep)
admin.site.register(News)
