from django import template
from dashboard.models import PUC

register = template.Library()


@register.simple_tag
def to_list(*args):
    return args


@register.inclusion_tag("core/components/puc/bubble_puc_legend.html")
def show_bubble_puc_legend(pucs, kind, show_filter=False):
    kind_display = dict(PUC.KIND_CHOICES).get(kind) or ""
    return {
        "pucs": pucs,
        "kind": kind,
        "kind_display": kind_display,
        "show_filter": show_filter,
    }
