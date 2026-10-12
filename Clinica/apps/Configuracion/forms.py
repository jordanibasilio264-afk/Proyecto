"""Ubicación: apps/Configuracion/forms.py
Uso: ConfiguracionForm(request.POST or None, request.FILES or None,
                       instance=ConfiguracionConsultorio.obtener())"""
from django import forms
from django.core.exceptions import ValidationError

from apps.usuarios.forms_base import EstiloFormMixin, limpiar_telefono

from .models import ConfiguracionConsultorio


class ConfiguracionForm(EstiloFormMixin, forms.ModelForm):
    class Meta:
        model = ConfiguracionConsultorio
        fields = [
            "nombre_consultorio", "rnc", "telefono", "email", "direccion", "logo", "moneda",
            "hora_apertura", "hora_cierre", "duracion_cita_defecto",
            "recordatorio_horas_antes", "paciente_frecuente_min_citas",
            "dias_alerta_seguimiento", "permitir_registro_publico",
        ]
        labels = {
            "telefono": "Teléfono", "direccion": "Dirección",
            "duracion_cita_defecto": "Duración de cita por defecto (min)",
            "recordatorio_horas_antes": "Enviar recordatorio (horas antes de la cita)",
            "paciente_frecuente_min_citas": "Citas atendidas para considerar paciente frecuente",
            "dias_alerta_seguimiento": "Avisar seguimientos con (días) de anticipación",
            "permitir_registro_publico": "Permitir que los pacientes se registren solos",
        }

    def clean_telefono(self):
        return limpiar_telefono(self.cleaned_data.get("telefono"))

    def clean_moneda(self):
        return self.cleaned_data["moneda"].strip().upper()

    def clean_duracion_cita_defecto(self):
        minutos = self.cleaned_data["duracion_cita_defecto"]
        if not 5 <= minutos <= 240:
            raise ValidationError("Debe estar entre 5 y 240 minutos.")
        return minutos

    def clean(self):
        datos = super().clean()
        apertura, cierre = datos.get("hora_apertura"), datos.get("hora_cierre")
        if apertura and cierre and cierre <= apertura:
            self.add_error("hora_cierre", "La hora de cierre debe ser posterior a la de apertura.")
        return datos