"""Ubicación: apps/usuarios/base.py  (clases base compartidas)"""
from django.core.exceptions import PermissionDenied
from django.db import models


class ModeloBase(models.Model):
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SinEliminarQuerySet(models.QuerySet):
    def delete(self):
        raise PermissionDenied("Estos registros no pueden eliminarse permanentemente.")


class NoEliminable(ModeloBase):
    """Regla de negocio: expedientes, consultas, recetas y pagos nunca se
    borran. Para 'quitarlos' se usa un campo de estado (activo/anulado)."""

    objects = SinEliminarQuerySet.as_manager()

    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        raise PermissionDenied("Este registro no puede eliminarse permanentemente.")