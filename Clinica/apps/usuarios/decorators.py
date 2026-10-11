"""Ubicación: apps/usuarios/decorators.py"""
from functools import wraps

from django.contrib.auth.mixins import AccessMixin
from django.contrib.auth.views import redirect_to_login
from django.http import Http404


def _sin_acceso(request):
    """Sin sesión -> al login. Con sesión pero sin permiso -> 404,
    para no revelar que la página existe."""
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path())
    raise Http404


def requiere_permiso(*codigos):
    """Vistas de función. Exige TODOS los permisos indicados.
    Ej: @requiere_permiso("citas.crear")
    """
    def decorador(vista):
        @wraps(vista)
        def envoltura(request, *args, **kwargs):
            u = request.user
            if not u.is_authenticated or not all(u.tiene_permiso(c) for c in codigos):
                return _sin_acceso(request)
            return vista(request, *args, **kwargs)
        return envoltura
    return decorador


def requiere_rol(*roles):
    """Vistas de función. Ej: @requiere_rol("ADMIN", "MEDICO")"""
    def decorador(vista):
        @wraps(vista)
        def envoltura(request, *args, **kwargs):
            u = request.user
            if not u.is_authenticated or not (u.is_superuser or u.rol in roles):
                return _sin_acceso(request)
            return vista(request, *args, **kwargs)
        return envoltura
    return decorador


class _AccesoOculto(AccessMixin):
    """Misma regla que _sin_acceso, para vistas de clase."""

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect_to_login(self.request.get_full_path())
        raise Http404


class PermisoRequeridoMixin(_AccesoOculto):
    """Vistas de clase. Ej:
        class CitaLista(PermisoRequeridoMixin, ListView):
            permisos_requeridos = ("citas.ver",)
    """
    permisos_requeridos = ()

    def dispatch(self, request, *args, **kwargs):
        u = request.user
        if not u.is_authenticated or not all(
            u.tiene_permiso(c) for c in self.permisos_requeridos
        ):
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class RolRequeridoMixin(_AccesoOculto):
    """Ej: roles_requeridos = ("ADMIN",)"""
    roles_requeridos = ()

    def dispatch(self, request, *args, **kwargs):
        u = request.user
        if not u.is_authenticated or not (
            u.is_superuser or u.rol in self.roles_requeridos
        ):
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)