"""Ubicación: apps/usuarios/context_processors.py

Registrar en settings.py -> TEMPLATES -> OPTIONS -> context_processors:
    "apps.usuarios.context_processors.permisos",

Uso en plantillas:
    {% if "citas.ver" in permisos %} ... {% endif %}
"""
from .models import PERMISOS_POR_ROL


def permisos(request):
    u = request.user
    if not u.is_authenticated or not u.is_active:
        return {"permisos": set()}
    if u.is_superuser:
        return {"permisos": set().union(*PERMISOS_POR_ROL.values())}
    return {"permisos": PERMISOS_POR_ROL.get(u.rol, set())}