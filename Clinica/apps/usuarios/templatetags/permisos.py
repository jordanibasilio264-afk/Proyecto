"""
Ubicación: apps/usuarios/templatetags/permisos.py
(crea también un archivo vacío __init__.py en esa carpeta)
"""
from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def tiene_permiso(context, codigo):
    usuario = context["request"].user
    return usuario.is_authenticated and usuario.tiene_permiso(codigo)