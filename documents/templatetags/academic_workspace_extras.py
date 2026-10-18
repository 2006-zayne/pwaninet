"""
Template helpers for the VASTO Student Dashboard workspace.
Exposes the per-unit tint palette from documents.academic.workspace to
templates so units and timetable blocks colour-code consistently.
"""
from django import template

from ..academic.workspace import unit_tint

register = template.Library()


@register.filter
def unit_tint_var(unit_code, which="ubg"):
    """`{{ unit.code|unit_tint_var:'uac' }}` → CSS value for the given tint var."""
    mapping = unit_tint(unit_code)
    return mapping.get(which, mapping["ubg"])
