from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.usuarios.models import Paciente
from .models import Expediente


class ExpedienteForm(forms.ModelForm):
    # ---- Campos que viven en Paciente (al nivel de la clase) ----
    sexo = forms.ChoiceField(
        choices=[("", "---"), *Paciente.Sexo.choices], required=False)
    tipo_sangre = forms.ChoiceField(
        label="Tipo de sangre",
        choices=[("", "---"), *Paciente.TipoSangre.choices], required=False)
    fecha_nacimiento = forms.DateField(
        label="Fecha de nacimiento", required=False,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    cedula = forms.CharField(max_length=20, required=False, label="Cédula")
    telefono = forms.CharField(max_length=20, required=False, label="Teléfono")
    direccion = forms.CharField(max_length=255, required=False, label="Dirección")
    contacto_emergencia_nombre = forms.CharField(
        max_length=120, required=False, label="Nombre del contacto de emergencia")
    contacto_emergencia_telefono = forms.CharField(
        max_length=20, required=False, label="Teléfono del contacto de emergencia")

    CAMPOS_PACIENTE = [
        "sexo", "tipo_sangre", "fecha_nacimiento", "cedula", "telefono",
        "direccion", "contacto_emergencia_nombre", "contacto_emergencia_telefono",
    ]

    class Meta:
        model = Expediente
        fields = [
            "fecha_apertura", "alergias", "antecedentes_personales",
            "antecedentes_familiares", "cirugias_previas",
            "observaciones_generales", "tratamientos",
        ]
        widgets = {
            "fecha_apertura": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "alergias": forms.Textarea(attrs={"rows": 2}),
            "antecedentes_personales": forms.Textarea(attrs={"rows": 3}),
            "antecedentes_familiares": forms.Textarea(attrs={"rows": 2}),
            "cirugias_previas": forms.Textarea(attrs={"rows": 2}),
            "observaciones_generales": forms.Textarea(attrs={"rows": 3}),
            "tratamientos": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        pac = self.instance.paciente
        for campo in self.CAMPOS_PACIENTE:
            self.fields[campo].initial = getattr(pac, campo)

        # Estilos de tu CSS
        for f in self.fields.values():
            css = {"Textarea": "form-textarea", "Select": "form-select"}.get(
                f.widget.__class__.__name__, "form-input")
            f.widget.attrs["class"] = css

    def clean_fecha_nacimiento(self):
        fecha = self.cleaned_data.get("fecha_nacimiento")
        if fecha and fecha > timezone.localdate():
            raise ValidationError("La fecha de nacimiento no puede ser futura.")
        return fecha

    def clean_cedula(self):
        cedula = (self.cleaned_data.get("cedula") or "").strip() or None
        if cedula and Paciente.objects.filter(cedula=cedula).exclude(
                pk=self.instance.paciente_id).exists():
            raise ValidationError("Ya existe otro paciente con esa cédula.")
        return cedula

    @transaction.atomic
    def save(self, commit=True):
        exp = super().save(commit=commit)
        pac = exp.paciente
        pac.sexo = self.cleaned_data["sexo"]
        pac.tipo_sangre = self.cleaned_data["tipo_sangre"]
        pac.fecha_nacimiento = self.cleaned_data["fecha_nacimiento"]
        pac.cedula = self.cleaned_data["cedula"]            # None si está vacía
        pac.telefono = self.cleaned_data["telefono"]
        pac.direccion = self.cleaned_data["direccion"]
        pac.contacto_emergencia_nombre = self.cleaned_data["contacto_emergencia_nombre"]
        pac.contacto_emergencia_telefono = self.cleaned_data["contacto_emergencia_telefono"]
        pac.save()
        return exp