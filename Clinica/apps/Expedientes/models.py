"""Ubicación: apps/Expedientes/models.py
Incluye: Expediente (RF-09) y Consulta (RF-08)."""
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.usuarios.base import NoEliminable


class Expediente(NoEliminable):
    """Un expediente por paciente. NUNCA se elimina (regla de negocio)."""

    paciente = models.OneToOneField(
        "usuarios.Paciente", on_delete=models.PROTECT, related_name="expediente"
    )
    numero = models.CharField(max_length=20, unique=True, null=True, blank=True, editable=False)
    fecha_apertura = models.DateField(default=timezone.localdate)
    alergias = models.TextField(blank=True)
    antecedentes_personales = models.TextField(blank=True)
    antecedentes_familiares = models.TextField(blank=True)
    enfermedades_cronicas = models.TextField(blank=True)
    cirugias_previas = models.TextField(blank=True)
    habitos = models.TextField("hábitos", blank=True)
    observaciones_generales = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_apertura"]
        verbose_name = "expediente clínico"
        verbose_name_plural = "expedientes clínicos"

    def __str__(self):
        return f"{self.numero or 'EXP'} - {self.paciente}"

    def save(self, *args, **kwargs):
        nuevo = self._state.adding
        super().save(*args, **kwargs)
        if nuevo and not self.numero:
            self.numero = f"EXP-{self.pk:06d}"
            type(self).objects.filter(pk=self.pk).update(numero=self.numero)


class Consulta(NoEliminable):
    """Consulta médica con signos vitales, diagnóstico y tratamiento."""

    expediente = models.ForeignKey(
        Expediente, on_delete=models.PROTECT, related_name="consultas"
    )
    cita = models.OneToOneField(
        "Citas.Cita", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="consulta",
    )
    medico = models.ForeignKey(
        "usuarios.Medico", on_delete=models.PROTECT, related_name="consultas"
    )
    fecha = models.DateTimeField(default=timezone.now, db_index=True)
    motivo_consulta = models.CharField(max_length=255)
    enfermedad_actual = models.TextField(blank=True)

    # Signos vitales
    presion_sistolica = models.PositiveSmallIntegerField(null=True, blank=True)
    presion_diastolica = models.PositiveSmallIntegerField(null=True, blank=True)
    frecuencia_cardiaca = models.PositiveSmallIntegerField(null=True, blank=True)
    frecuencia_respiratoria = models.PositiveSmallIntegerField(null=True, blank=True)
    temperatura = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    saturacion_oxigeno = models.PositiveSmallIntegerField(null=True, blank=True)
    peso_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    talla_cm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)

    diagnostico = models.TextField(blank=True)
    codigo_cie10 = models.CharField("código CIE-10", max_length=10, blank=True)
    tratamiento = models.TextField(blank=True)
    observaciones = models.TextField(blank=True)

    # Seguimiento (RF-20)
    requiere_seguimiento = models.BooleanField(default=False)
    fecha_seguimiento = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-fecha"]
        indexes = [models.Index(fields=["expediente", "-fecha"])]
        verbose_name = "consulta"
        verbose_name_plural = "consultas"

    def __str__(self):
        return f"Consulta {self.fecha:%d/%m/%Y} - {self.expediente.paciente}"

    @property
    def imc(self):
        if self.peso_kg and self.talla_cm:
            metros = float(self.talla_cm) / 100
            return round(float(self.peso_kg) / (metros ** 2), 1)
        return None

    def clean(self):
        errores = {}
        # Solo los médicos registran diagnósticos.
        if self.medico_id and self.medico.usuario.rol != "MEDICO":
            errores["medico"] = "Solo un usuario con rol Médico puede registrar consultas."
        if self.cita_id:
            if self.cita.estado == "CANCELADA":
                errores["cita"] = "No se puede registrar una consulta de una cita cancelada."
            elif self.expediente_id and self.cita.paciente_id != self.expediente.paciente_id:
                errores["cita"] = "La cita pertenece a otro paciente."
        if self.requiere_seguimiento and not self.fecha_seguimiento:
            errores["fecha_seguimiento"] = "Indica la fecha de seguimiento."
        if errores:
            raise ValidationError(errores)