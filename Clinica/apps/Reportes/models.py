"""Ubicación: apps/Reportes/models.py
Historial de reportes generados (los datos del reporte se consultan en vivo)."""
from django.conf import settings
from django.db import models

from apps.usuarios.base import ModeloBase


class ReporteGenerado(ModeloBase):
    class Tipo(models.TextChoices):
        PACIENTES = "PACIENTES", "Pacientes"
        CITAS = "CITAS", "Citas"
        CONSULTAS = "CONSULTAS", "Consultas"
        PAGOS = "PAGOS", "Pagos"
        DIAGNOSTICOS = "DIAGNOSTICOS", "Diagnósticos"
        MEDICOS = "MEDICOS", "Médicos"

    class Formato(models.TextChoices):
        PDF = "PDF", "PDF"
        EXCEL = "EXCEL", "Excel"

    tipo = models.CharField(max_length=15, choices=Tipo.choices, db_index=True)
    formato = models.CharField(max_length=5, choices=Formato.choices)
    parametros = models.JSONField(default=dict, blank=True)  # filtros usados
    generado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reportes_generados",
    )
    archivo = models.FileField(upload_to="reportes/%Y/%m/", blank=True)

    class Meta:
        ordering = ["-creado_en"]
        verbose_name = "reporte generado"
        verbose_name_plural = "reportes generados"

    def __str__(self):
        return f"Reporte {self.get_tipo_display()} ({self.formato}) - {self.creado_en:%d/%m/%Y}"