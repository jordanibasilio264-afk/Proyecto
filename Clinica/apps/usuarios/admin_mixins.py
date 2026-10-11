"""Ubicación: apps/usuarios/admin_mixins.py"""


class SinEliminarAdmin:
    """Para modelos que nunca se borran (expedientes, consultas, recetas, pagos).
    Al devolver False, Django también oculta la acción 'Eliminar seleccionados'."""

    def has_delete_permission(self, request, obj=None):
        return False


class SoloLecturaAdmin:
    """Para auditoría: solo se consulta."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False