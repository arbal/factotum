from django.contrib import admin
from dashboard.models import *
from django.db.models import Count

from django import forms
from taggit_labels.widgets import LabelWidget
from dashboard.signals import *

class PUCAdminForm(forms.ModelForm):
    class Meta:
        model = PUC
        fields = ['gen_cat', 'prod_fam', 'prod_type', 'description','tags',]
        readonly_fields = ('num_products',)
        widgets = {
            'tags': LabelWidget(model=PUCTag),
        }

class PUCAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'tag_list','num_products')
    form = PUCAdminForm
    def get_changeform_initial_data(self, request):
        get_data = super(PUCAdmin, self).get_changeform_initial_data(request)
        get_data['last_edited_by'] = request.user.pk
        return get_data
    def get_queryset(self, request):
        return super(PUCAdmin, self).get_queryset(request).prefetch_related('tags').annotate(num_products=Count('products'))
    def num_products(self, obj):
        return obj.num_products
    num_products.short_description = 'Product Count'
    num_products.admin_order_field = 'num_products'
    def tag_list(self, obj):
        return u", ".join(o.name for o in obj.tags.all())

class HHDocAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'hhe_report_number')

class PUCToTagAdmin(admin.ModelAdmin):
    list_display = ('content_object', 'tag', 'assumed')
    list_filter = ('tag',)
    def tag(self, obj):
        return obj.tag    
    def assumed(self, obj):
        return obj.assumed 

# Register your models here.
admin.site.register(DataSource)
admin.site.register(GroupType)
admin.site.register(DataGroup)
admin.site.register(DocumentType)
admin.site.register(DataDocument)
admin.site.register(Script)
admin.site.register(Product)
admin.site.register(ProductToPUC)
admin.site.register(ProductDocument)
admin.site.register(SourceCategory)
admin.site.register(PUC, PUCAdmin)
admin.site.register(ExtractedText)
admin.site.register(ExtractedChemical)
admin.site.register(ExtractedFunctionalUse)
admin.site.register(ExtractedHabitsAndPractices)
admin.site.register(DSSToxLookup)
admin.site.register(QAGroup)
admin.site.register(UnitType)
admin.site.register(WeightFractionType)
admin.site.register(PUCTag) #,ProductTagAdmin
admin.site.register(Taxonomy)
admin.site.register(TaxonomySource)
admin.site.register(TaxonomyToPUC)
admin.site.register(ExtractedHHDoc, HHDocAdmin)
admin.site.register(ExtractedHHRec)
admin.site.register(PUCToTag, PUCToTagAdmin)
