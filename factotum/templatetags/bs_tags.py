from django import template

register = template.Library()


@register.filter("add_class")
def add_class(field, class_name):
    return field.as_widget(
        attrs={"class": " ".join((field.field.widget.attrs["class"], class_name))}
    )
