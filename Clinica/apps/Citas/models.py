"""Ubicación: apps/Citas/models.py"""
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.usuarios.base import ModeloBase


class CitaQuerySet(models.QuerySet):
    def activas(self):
        return self.filter(estado__in=Cita.ESTADOS_ACTIVOS)

    def pendientes(self):
        """RF-20: citas por atender (programadas o confirmadas, a futuro)."""
        return self.filter(
            estado__in=["PROGRAMADA", "CONFIRMADA"], inicio__gte=timezone.now()
        )

    def proximas(self, horas=24):
        """RF-07/RF-15: citas que ocurren en las próximas N horas."""
        return self.pendientes().filter(
            inicio__lte=timezone.now() + timedelta(hours=horas)
        )

    def del_dia(self, fecha):
        return self.filter(inicio__date=fecha)


class Cita(ModeloBase):
    class Estado(models.TextChoices):
        PROGRAMADA = "PROGRAMADA", "Programada"
        CONFIRMADA = "CONFIRMADA", "Confirmada"
        ATENDIDA = "ATENDIDA", "Atendida"
        CANCELADA = "CANCELADA", "Cancelada"
        NO_ASISTIO = "NO_ASISTIO", "No asistió"
        REPROGRAMADA = "REPROGRAMADA", "Reprogramada"

    # Estados que ocupan agenda (bloquean el horario).
    ESTADOS_ACTIVOS = ("PROGRAMADA", "CONFIRMADA", "ATENDIDA")

    paciente = models.ForeignKey(
        "usuarios.Paciente", on_delete=models.PROTECT, related_name="citas"
    )
    medico = models.ForeignKey(
        "usuarios.Medico", on_delete=models.PROTECT, related_name="citas"
    )
    inicio = models.DateTimeField(db_index=True)
    duracion_minutos = models.PositiveSmallIntegerField(default=30)
    fin = models.DateTimeField(editable=False, blank=True)  # se calcula solo
    motivo = models.CharField(max_length=255)
    estado = models.CharField(
        max_length=15, choices=Estado.choices, default=Estado.PROGRAMADA, db_index=True
    )
    notas = models.TextField(blank=True)
    motivo_cancelacion = models.CharField(max_length=255, blank=True)
    reprogramada_desde = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reprogramaciones",
    )
    creada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="citas_creadas",
    )

    objects = CitaQuerySet.as_manager()

    class Meta:
        ordering = ["inicio"]
        indexes = [
            models.Index(fields=["medico", "inicio"]),
            models.Index(fields=["paciente", "inicio"]),
        ]
        verbose_name = "cita"
        verbose_name_plural = "citas"

    def __str__(self):
        return f"{self.paciente} con {self.medico} - {self.inicio:%d/%m/%Y %H:%M}"

    def _calcular_fin(self):
        if self.inicio and self.duracion_minutos:
            self.fin = self.inicio + timedelta(minutes=self.duracion_minutos)

    # --- Reglas de negocio --------------------------------------------
    def clean(self):
        self._calcular_fin()

        # Una cita cancelada no puede pasar a atendida.
        if self.pk:
            anterior = (
                Cita.objects.filter(pk=self.pk).values_list("estado", flat=True).first()
            )
            if anterior == self.Estado.CANCELADA and self.estado == self.Estado.ATENDIDA:
                raise ValidationError(
                    {"estado": "Una cita cancelada no puede marcarse como atendida."}
                )

        # Sin choques de horario (médico y paciente).
        if (
            self.estado in self.ESTADOS_ACTIVOS
            and self.inicio and self.fin
            and self.medico_id and self.paciente_id
        ):
            solapadas = Cita.objects.filter(
                estado__in=self.ESTADOS_ACTIVOS,
                inicio__lt=self.fin,
                fin__gt=self.inicio,
            ).exclude(pk=self.pk)
            errores = {}
            if solapadas.filter(medico_id=self.medico_id).exists():
                errores["medico"] = "El médico ya tiene una cita en ese horario."
            if solapadas.filter(paciente_id=self.paciente_id).exists():
                errores["paciente"] = "El paciente ya tiene una cita en ese horario."
            if errores:
                raise ValidationError(errores)

    def save(self, *args, **kwargs):
        self._calcular_fin()
        self.full_clean()  # garantiza las reglas aunque no pase por un formulario
        super().save(*args, **kwargs)

    # --- Acciones -----------------------------------------------------
    def confirmar(self):
        self.estado = self.Estado.CONFIRMADA
        self.save()

    def cancelar(self, motivo=""):
        if self.estado == self.Estado.ATENDIDA:
            raise ValidationError("Una cita atendida no puede cancelarse.")
        self.estado = self.Estado.CANCELADA
        self.motivo_cancelacion = motivo
        self.save()

    def marcar_atendida(self):
        self.estado = self.Estado.ATENDIDA
        self.save()