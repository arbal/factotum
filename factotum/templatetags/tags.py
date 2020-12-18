from django import template
from dashboard.models import PUCKind

register = template.Library()


@register.simple_tag
def to_list(*args):
    return args


@register.inclusion_tag("core/components/puc/bubble_puc_legend.html")
def show_bubble_puc_legend(pucs, kind_code, show_filter=False):
    kind = PUCKind.objects.filter(code=kind_code).first() or ""
    return {"pucs": pucs, "kind": kind, "show_filter": show_filter}


@register.filter
def concat_string(value_1, value_2):
    return str(value_1) + str(value_2)
