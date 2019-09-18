import os
from django import template

register = template.Library()

ICON_MAP = {
    ".csv": "-csv",
    ".pdf": "-pdf",
    ".txt": "-alt",
    ".doc": "-word",
    ".docx": "-word",
    ".xls": "-excel",
    ".xlsx": "-excel",
    ".jpg": "-image",
    ".tiff": "-image",
}


@register.filter
def fileicon(value):
    _, ext = os.path.splitext(value)
    return "fa-file" + ICON_MAP.get(ext, "")
