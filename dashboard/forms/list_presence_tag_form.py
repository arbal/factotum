from django import forms
from dashboard.models import ExtractedListPresence
from taggit.forms import TagWidget, TagField

class ExtractedListPresenceTagForm(forms.ModelForm):
    tags = TagField(label="List Presence Keywords", required=False)

    class Meta:
        model = ExtractedListPresence
        fields = ['tags']
        widgets = {
            'tags': TagWidget()
        }

    def __init__(self, *args, **kwargs):
        super(ExtractedListPresenceTagForm, self).__init__(*args, **kwargs)
        self.fields['tags'].widget.attrs.update({'class':'mr-2 ml-2','size':'60'})
