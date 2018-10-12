from dal import autocomplete
from django import forms
from dashboard.models import *

class ProductForm(forms.ModelForm):
    required_css_class = 'required' # adds to label tag
    class Meta:
        model = Product
        fields = ['title', 'manufacturer', 'brand_name', 'upc', 'size', 'color']

class BasePUCForm(forms.ModelForm):
    puc = forms.ModelChoiceField(
        queryset=PUC.objects.all(),
        label='Category',
        widget=autocomplete.ModelSelect2(
            url='puc-autocomplete',
            attrs={'data-minimum-input-length': 3,  })
    )

class ProductPUCForm(BasePUCForm):
    class Meta:
        model = ProductToPUC
        fields = ['puc']

class HabitsPUCForm(BasePUCForm):
    class Meta:
        model = ExtractedHabitsAndPracticesToPUC
        fields = ['puc']

class ExtractedTextForm(forms.ModelForm):
    class Meta:
        model = ExtractedText
        fields = ['doc_date', 'data_document', 'extraction_script']
        widgets = {
            'data_document': forms.HiddenInput(),
            'extraction_script': forms.HiddenInput(),
        }

HnPFormSet = forms.inlineformset_factory(parent_model=ExtractedText,
                                    model=ExtractedHabitsAndPractices,
                                    fields=['product_surveyed',
                                            'mass',
                                            'mass_unit',
                                            'frequency',
                                            'frequency_unit',
                                            'duration',
                                            'duration_unit',
                                            'prevalence',
                                            'notes'],
                                            extra=1)

ChemicalFormSet = forms.inlineformset_factory(parent_model=ExtractedText,
                                    model=ExtractedChemical,
                                    fields=['extracted_text',
                                            'raw_cas',
                                            'raw_chem_name',
                                            'raw_min_comp',
                                            'raw_central_comp',
                                            'raw_max_comp',
                                            'unit_type',
                                            'report_funcuse',
                                            'weight_fraction_type',
                                            'ingredient_rank',
                                            ],
                                    extra=0)

