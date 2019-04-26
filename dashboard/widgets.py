from taggit_labels.widgets import LabelWidget


class FilteredLabelWidget(LabelWidget):
    # overriding django-taggit-label function to display subset of tags
    def tag_list(self, tags):
        # must set form_instance in form __init__()
        puc = self.form_instance.instance.get_uber_puc() or None
        qs = self.model.objects.filter(content_object=puc,assumed=False)
        filtered = [unassumed.tag for unassumed in qs]
        return [(tag.name, 'selected taggit-tag' if tag.name in tags else 'taggit-tag')
                for tag in filtered]
