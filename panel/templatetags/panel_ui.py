from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from panel.icons import ICONS

register = template.Library()


@register.simple_tag
def icon(name, css="h-5 w-5"):
    """{% icon "cube" "h-4 w-4" %} renders an inline Heroicons SVG that inherits the text colour."""
    inner = ICONS.get(name)
    if inner is None:
        return ""
    return format_html(
        '<svg class="{}" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" '
        'stroke="currentColor" aria-hidden="true">{}</svg>', css, mark_safe(inner))
