from dal import autocomplete
from django import forms

from dashboard.models import (
    ExtractedListPresence,
    ExtractedListPresenceTag,
    ExtractedHabitsAndPractices,
    ExtractedHabitsAndPracticesTag,
    ExtractedHabitsAndPracticesToTag,
    ExtractedListPresenceToTag,
)


class TagFormSaveMixin:
    through_model = None

    def save(self):
        tags = self.cleaned_data.get("tags")
        chems = self.cleaned_data.get("chems")

        build_list = []
        for chem in chems:
            for tag in tags:
                if tag not in chem.tags.all():
                    build_list.append(self.through_model(tag=tag, content_object=chem))
        self.through_model.objects.bulk_create(build_list)


class ExtractedListPresenceTagForm(TagFormSaveMixin, forms.Form):
    tags = forms.ModelMultipleChoiceField(
        queryset=ExtractedListPresenceTag.objects.all(),
        label="",
        widget=autocomplete.ModelSelect2Multiple(
            url="list_presence_tags_autocomplete",
            attrs={"data-minimum-input-length": 3, "style": "width: 100%"},
        ),
    )

    chems = forms.ModelMultipleChoiceField(
        queryset=ExtractedListPresence.objects.prefetch_related("tags").all(),
        label="",
        widget=forms.MultipleHiddenInput(),
    )

    through_model = ExtractedListPresenceToTag


class ExtractedHabitsAndPracticesTagForm(TagFormSaveMixin, forms.Form):
    tags = forms.ModelMultipleChoiceField(
        queryset=ExtractedHabitsAndPracticesTag.objects.all(),
        label="",
        widget=autocomplete.ModelSelect2Multiple(
            url="habits_and_practices_tags_autocomplete",
            attrs={"data-minimum-input-length": 3, "style": "width: 100%"},
        ),
    )

    chems = forms.ModelMultipleChoiceField(
        queryset=ExtractedHabitsAndPractices.objects.prefetch_related("tags").all(),
        label="",
        widget=forms.MultipleHiddenInput(),
    )

    through_model = ExtractedHabitsAndPracticesToTag
