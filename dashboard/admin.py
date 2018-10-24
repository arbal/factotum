from django.contrib import admin
from dashboard.models import *
from django import forms
from taggit_labels.widgets import LabelWidget
from dashboard.signals import *

class PUCAdminForm(forms.ModelForm):
    class Meta:
        model = PUC
        fields = ['gen_cat', 'prod_fam', 'prod_type', 'description','tags']
        widgets = {
            'tags': LabelWidget(model=PUCTag),
        }

class PUCAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'tag_list')
    form = PUCAdminForm
    def get_changeform_initial_data(self, request):
        get_data = super(PUCAdmin, self).get_changeform_initial_data(request)
        get_data['last_edited_by'] = request.user.pk
        return get_data
    def get_queryset(self, request):
        return super(PUCAdmin, self).get_queryset(request).prefetch_related('tags')
    def tag_list(self, obj):
        return u", ".join(o.name for o in obj.tags.all())


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
admin.site.register(PUCTag) #,ProductTagAdmin
admin.site.register(Taxonomy)
admin.site.register(TaxonomySource)
admin.site.register(TaxonomyToPUC)
