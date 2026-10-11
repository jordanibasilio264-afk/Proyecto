"""Ubicación: apps/Notificaciones/models.py"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.usuarios.base import ModeloBase


class Notificacion(ModeloBase):
    class Tipo(models.TextChoices):
        RECORDATORIO_CITA = "RECORDATORIO_CITA", "Recordatorio de cita"
        CITA_CONFIRMADA = "CITA_CONFIRMADA", "Cita confirmada"
        CITA_CANCELADA = "CITA_CANCELADA", "Cita cancelada"
        CITA_REPROGRAMADA = "CITA_REPROGRAMADA", "Cita reprogramada"
        SEGUIMIENTO = "SEGUIMIENTO", "Seguimiento de paciente"
        ALERTA_MEDICA = "ALERTA_MEDICA", "Alerta médica"
        GENERAL = "GENERAL", "General"

    class Canal(models.TextChoices):
        SISTEMA = "SISTEMA", "Dentro del sistema"
        EMAIL = "EMAIL", "Correo electrónico"
        SMS = "SMS", "SMS"
        WHATSAPP = "WHATSAPP", "WhatsApp"

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente de envío"
        ENVIADA = "ENVIADA", "Enviada"
        FALLIDA = "FALLIDA", "Fallida"

    # Destinatario: un usuario del sistema y/o un paciente (que puede no tener cuenta)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True,
        related_name="notificaciones",
    )
    paciente = models.ForeignKey(
        "usuarios.Paciente", on_delete=models.CASCADE, null=True, blank=True,
        related_name="notificaciones",
    )
    cita = models.ForeignKey(
        "Citas.Cita", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="notificaciones",
    )
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.GENERAL)
    canal = models.CharField(max_length=10, choices=Canal.choices, default=Canal.SISTEMA)
    titulo = models.CharField(max_length=150)
    mensaje = models.TextField()
    estado = models.CharField(
        max_length=10, choices=Estado.choices, default=Estado.PENDIENTE, db_index=True
    )
    programada_para = models.DateTimeField(default=timezone.now, db_index=True)
    enviada_en = models.DateTimeField(null=True, blank=True)
    error = models.CharField(max_length=255, blank=True)
    leida = models.BooleanField(default=False)
    leida_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-programada_para"]
        indexes = [models.Index(fields=["usuario", "leida"])]
        verbose_name = "notificación"
        verbose_name_plural = "notificaciones"

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.titulo}"

    def clean(self):
        if not self.usuario_id and not self.paciente_id:
            raise ValidationError("Indica un usuario o un paciente como destinatario.")

    def marcar_leida(self):
        self.leida = True
        self.leida_en = timezone.now()
        self.save(update_fields=["leida", "leida_en", "actualizado_en"])

    def marcar_enviada(self):
        self.estado = self.Estado.ENVIADA
        self.enviada_en = timezone.now()
        self.save(update_fields=["estado", "enviada_en", "actualizado_en"])