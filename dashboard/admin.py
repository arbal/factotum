from dashboard.models import *
from django.contrib import admin


# auto-populate User field w/ current user
class PUCAdmin(admin.ModelAdmin):
    def get_changeform_initial_data(self, request):
        get_data = super(PUCAdmin, self).get_changeform_initial_data(request)
        get_data['last_edited_by'] = request.user.pk
        return get_data


# Register your models here.
admin.site.register(DataSource)
admin.site.register(GroupType)
admin.site.register(DataGroup)
admin.site.register(DocumentType)
admin.site.register(DataDocument)
admin.site.register(Script)
admin.site.register(Product)
admin.site.register(ProductDocument)
admin.site.register(SourceCategory)
admin.site.register(PUC, PUCAdmin)
admin.site.register(ExtractedText)
admin.site.register(ExtractedChemical)
admin.site.register(ExtractedFunctionalUse)
admin.site.register(ExtractedHabitsAndPractices)
admin.site.register(DSSToxSubstance)
admin.site.register(QAGroup)
admin.site.register(UnitType)
admin.site.register(WeightFractionType)
admin.site.register(ProductAttribute)
admin.site.register(PUCAttribute)
admin.site.register(Taxonomy)
admin.site.register(TaxonomySource)
admin.site.register(TaxonomyToPUC)
