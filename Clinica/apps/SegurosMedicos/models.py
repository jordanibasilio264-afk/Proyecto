"""Ubicación: apps/SegurosMedicos/models.py"""
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.db import models
from django.utils import timezone

from apps.usuarios.base import ModeloBase


class SeguroMedico(ModeloBase):
    """Aseguradora / ARS (ej. SENASA, Humano, Universal...)."""

    nombre = models.CharField(max_length=120, unique=True)
    rnc = models.CharField("RNC", max_length=20, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    porcentaje_cobertura = models.PositiveSmallIntegerField(
        "cobertura por defecto (%)", default=0, validators=[MaxValueValidator(100)]
    )
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "seguro médico"
        verbose_name_plural = "seguros médicos"

    def __str__(self):
        return self.nombre


class SeguroPaciente(ModeloBase):
    """Asocia un seguro con un paciente (RF-13)."""

    paciente = models.ForeignKey(
        "usuarios.Paciente", on_delete=models.CASCADE, related_name="seguros"
    )
    seguro = models.ForeignKey(
        SeguroMedico, on_delete=models.PROTECT, related_name="afiliados"
    )
    numero_afiliado = models.CharField(max_length=50)
    titular_nombre = models.CharField(max_length=120, blank=True)
    vigente_desde = models.DateField(default=timezone.localdate)
    vigente_hasta = models.DateField(null=True, blank=True)
    es_principal = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["paciente", "seguro", "numero_afiliado"],
                name="seguro_paciente_unico",
            ),
            # Un solo seguro principal por paciente
            models.UniqueConstraint(
                fields=["paciente"],
                condition=models.Q(es_principal=True),
                name="un_seguro_principal_por_paciente",
            ),
        ]
        verbose_name = "seguro del paciente"
        verbose_name_plural = "seguros de pacientes"

    def __str__(self):
        return f"{self.paciente} - {self.seguro} ({self.numero_afiliado})"

    @property
    def vigente(self):
        hoy = timezone.localdate()
        return self.activo and self.vigente_desde <= hoy and (
            self.vigente_hasta is None or self.vigente_hasta >= hoy
        )

    def clean(self):
        if self.vigente_hasta and self.vigente_hasta < self.vigente_desde:
            raise ValidationError({"vigente_hasta": "No puede ser anterior a la fecha de inicio."})