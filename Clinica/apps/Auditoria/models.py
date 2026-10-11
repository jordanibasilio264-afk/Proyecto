"""Ubicación: apps/Auditoria/models.py
Registros de solo lectura: se crean, nunca se editan ni se borran."""
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import models


class SoloAnadirQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise PermissionDenied("Los registros de auditoría no se pueden modificar.")

    def delete(self):
        raise PermissionDenied("Los registros de auditoría no se pueden eliminar.")


class RegistroInmutable(models.Model):
    objects = SoloAnadirQuerySet.as_manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise PermissionDenied("Los registros de auditoría no se pueden modificar.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionDenied("Los registros de auditoría no se pueden eliminar.")


class RegistroAuditoria(RegistroInmutable):
    """Historial de cambios importantes (RF-19)."""

    class Accion(models.TextChoices):
        CREAR = "CREAR", "Crear"
        EDITAR = "EDITAR", "Editar"
        ELIMINAR = "ELIMINAR", "Eliminar / desactivar"
        CONSULTAR = "CONSULTAR", "Consultar"
        DESCARGAR = "DESCARGAR", "Descargar"
        CONFIRMAR = "CONFIRMAR", "Confirmar"
        CANCELAR = "CANCELAR", "Cancelar"
        OTRO = "OTRO", "Otro"

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="acciones_auditadas",
    )
    accion = models.CharField(max_length=10, choices=Accion.choices, db_index=True)
    modelo = models.CharField(max_length=100, db_index=True)   # ej. "Citas.Cita"
    objeto_id = models.CharField(max_length=50, blank=True)
    descripcion = models.CharField(max_length=255, blank=True)
    datos_anteriores = models.JSONField(null=True, blank=True)
    datos_nuevos = models.JSONField(null=True, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-fecha"]
        indexes = [models.Index(fields=["modelo", "objeto_id"])]
        verbose_name = "registro de auditoría"
        verbose_name_plural = "registros de auditoría"

    def __str__(self):
        return f"{self.fecha:%d/%m/%Y %H:%M} - {self.usuario} - {self.accion} {self.modelo}"


class RegistroAcceso(RegistroInmutable):
    """Inicios y cierres de sesión, y intentos fallidos."""

    class Evento(models.TextChoices):
        LOGIN = "LOGIN", "Inicio de sesión"
        LOGOUT = "LOGOUT", "Cierre de sesión"
        LOGIN_FALLIDO = "LOGIN_FALLIDO", "Intento fallido"

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="accesos",
    )
    email_intentado = models.CharField(max_length=254, blank=True)
    evento = models.CharField(max_length=15, choices=Evento.choices, db_index=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    fecha = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "registro de acceso"
        verbose_name_plural = "registros de acceso"

    def __str__(self):
        return f"{self.fecha:%d/%m/%Y %H:%M} - {self.get_evento_display()} - {self.email_intentado or self.usuario}"