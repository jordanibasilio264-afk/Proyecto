"""Ubicación: apps/Documentos/models.py"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone

from apps.usuarios.base import ModeloBase

MAX_MB = 10


def ruta_documento(instancia, nombre_archivo):
    return f"documentos/paciente_{instancia.paciente_id}/{timezone.now():%Y/%m}/{nombre_archivo}"


def validar_tamano(archivo):
    if archivo.size > MAX_MB * 1024 * 1024:
        raise ValidationError(f"El archivo no puede superar {MAX_MB} MB.")


class Documento(ModeloBase):
    class Tipo(models.TextChoices):
        LABORATORIO = "LABORATORIO", "Resultado de laboratorio"
        IMAGEN = "IMAGEN", "Imagen / estudio"
        RECETA = "RECETA", "Receta médica"
        INFORME = "INFORME", "Informe médico"
        CONSENTIMIENTO = "CONSENTIMIENTO", "Consentimiento"
        IDENTIFICACION = "IDENTIFICACION", "Identificación / seguro"
        OTRO = "OTRO", "Otro"

    paciente = models.ForeignKey(
        "usuarios.Paciente", on_delete=models.PROTECT, related_name="documentos"
    )
    consulta = models.ForeignKey(
        "Expedientes.Consulta", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="documentos",
    )
    titulo = models.CharField(max_length=150)
    tipo = models.CharField(max_length=15, choices=Tipo.choices, default=Tipo.OTRO)
    archivo = models.FileField(
        upload_to=ruta_documento,
        validators=[
            FileExtensionValidator(["pdf", "jpg", "jpeg", "png", "doc", "docx"]),
            validar_tamano,
        ],
    )
    descripcion = models.CharField(max_length=255, blank=True)
    tamano_bytes = models.PositiveIntegerField(default=0, editable=False)
    subido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="documentos_subidos",
    )
    activo = models.BooleanField(default=True)  # "eliminar" = desactivar

    class Meta:
        ordering = ["-creado_en"]
        verbose_name = "documento médico"
        verbose_name_plural = "documentos médicos"

    def __str__(self):
        if self.creado_en:
            return f"{self.titulo} ({timezone.localtime(self.creado_en):%d/%m/%Y}) - {self.paciente}"
        return f"{self.titulo} - {self.paciente}"

    def save(self, *args, **kwargs):
        if self.archivo:
            self.tamano_bytes = self.archivo.size
        super().save(*args, **kwargs)