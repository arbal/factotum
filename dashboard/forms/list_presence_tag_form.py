from dashboard.models import ExtractedListPresence, ExtractedListPresenceTag
from dal import autocomplete


class ExtractedListPresenceTagForm(autocomplete.FutureModelForm):
    class Meta:
        model = ExtractedListPresence
        fields = ["tags"]

        widgets = {
            "tags": autocomplete.TaggitSelect2("list_presence_tags_autocomplete")
        }

    def __init__(self, *args, **kwargs):
        super(ExtractedListPresenceTagForm, self).__init__(*args, **kwargs)
        self.fields["tags"].widget.attrs.update(
            {"class": "mr-2 ml-2", "style": "width:60%", "data-minimum-input-length": 3}
        )
        self.fields["tags"].label = "List Presence Keywords"
        self.fields["tags"].help_text = ""

    def clean(self):
        valid_tag_list = ExtractedListPresenceTag.objects.all().values_list(
            "name", flat=True
        )
        self.invalid_tags = []
        for tag in self.cleaned_data["tags"]:
            if tag in valid_tag_list:
                pass
            else:
                self.invalid_tags.append(tag)
                self.cleaned_data["tags"].remove(tag)
                self.add_error("tags", "%s is not a valid keyword" % tag)
