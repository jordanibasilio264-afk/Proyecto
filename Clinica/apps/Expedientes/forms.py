from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.usuarios.models import Paciente
from .models import Expediente


class ExpedienteForm(forms.ModelForm):
    # Campos que viven en Paciente
    sexo = forms.ChoiceField(
        choices=[("", "---"), *Paciente.Sexo.choices], required=False)
    tipo_sangre = forms.ChoiceField(
        choices=[("", "---"), *Paciente.TipoSangre.choices], required=False)
    fecha_nacimiento = forms.DateField(
        label="Fecha de nacimiento", required=False,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))

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
        self.fields["sexo"].initial = pac.sexo
        self.fields["tipo_sangre"].initial = pac.tipo_sangre
        self.fields["fecha_nacimiento"].initial = pac.fecha_nacimiento
        # Estilos de tu CSS
        for name, f in self.fields.items():
            css = {"Textarea": "form-textarea", "Select": "form-select"}.get(
                f.widget.__class__.__name__, "form-input")
            f.widget.attrs["class"] = css

    def clean_fecha_nacimiento(self):
        fecha = self.cleaned_data.get("fecha_nacimiento")
        if fecha and fecha > timezone.localdate():
            raise ValidationError("La fecha de nacimiento no puede ser futura.")
        return fecha

    @transaction.atomic
    def save(self, commit=True):
        exp = super().save(commit=commit)
        pac = exp.paciente
        pac.sexo = self.cleaned_data["sexo"]
        pac.tipo_sangre = self.cleaned_data["tipo_sangre"]
        pac.fecha_nacimiento = self.cleaned_data["fecha_nacimiento"]
        pac.save()
        return exp