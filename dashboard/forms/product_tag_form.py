from django.forms import ModelForm
from taggit.forms import TagField

from dashboard.models import PUCToTag, Product
from dashboard.widgets import FilteredLabelWidget


class ProductTagForm(ModelForm):
    tags = TagField(required=False, widget=FilteredLabelWidget(model=PUCToTag))

    class Meta:
        model = Product
        fields = ["tags"]

    def __init__(self, *args, **kwargs):
        super(ProductTagForm, self).__init__(*args, **kwargs)
        self.fields["tags"].widget.form_instance = self
