"""Ubicación: apps/SegurosMedicos/forms.py"""
from django import forms
from django.core.exceptions import ValidationError

from apps.usuarios.forms_base import EstiloFormMixin, buscar_texto, limpiar_nombre, limpiar_telefono

from .models import SeguroMedico, SeguroPaciente


class SeguroMedicoForm(EstiloFormMixin, forms.ModelForm):
    class Meta:
        model = SeguroMedico
        fields = ["nombre", "rnc", "telefono", "email", "porcentaje_cobertura", "activo"]
        labels = {"telefono": "Teléfono"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["porcentaje_cobertura"].widget.attrs.update({"min": 0, "max": 100})

    def clean_nombre(self):
        nombre = limpiar_nombre(self.cleaned_data["nombre"])
        repetido = SeguroMedico.objects.filter(nombre__iexact=nombre).exclude(pk=self.instance.pk)
        if repetido.exists():
            raise ValidationError("Ya existe un seguro con ese nombre.")
        return nombre

    def clean_telefono(self):
        return limpiar_telefono(self.cleaned_data.get("telefono"))


class SeguroPacienteForm(EstiloFormMixin, forms.ModelForm):
    """Asociar un seguro a un paciente. Uso: SeguroPacienteForm(request.POST or None, paciente=paciente)"""

    class Meta:
        model = SeguroPaciente
        fields = ["paciente", "seguro", "numero_afiliado", "titular_nombre",
                  "vigente_desde", "vigente_hasta", "es_principal", "activo"]
        labels = {"numero_afiliado": "No. de afiliado", "es_principal": "Seguro principal"}

    def __init__(self, *args, paciente=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["seguro"].queryset = SeguroMedico.objects.filter(activo=True)
        if paciente is not None:
            del self.fields["paciente"]
            self.instance.paciente = paciente

    def clean(self):
        datos = super().clean()
        paciente = datos.get("paciente") or getattr(self.instance, "paciente", None)
        if paciente is None:
            return datos
        otros = SeguroPaciente.objects.filter(paciente=paciente).exclude(pk=self.instance.pk)
        if datos.get("es_principal") and otros.filter(es_principal=True).exists():
            self.add_error("es_principal",
                           "Ya hay un seguro principal. Quítale la marca primero.")
        if datos.get("seguro") and datos.get("numero_afiliado") and otros.filter(
                seguro=datos["seguro"], numero_afiliado=datos["numero_afiliado"]).exists():
            self.add_error("numero_afiliado", "Este paciente ya tiene ese seguro registrado.")
        return datos


class FiltroSeguroForm(EstiloFormMixin, forms.Form):
    q = forms.CharField(label="Buscar", required=False, widget=forms.TextInput(
        attrs={"placeholder": "Paciente, seguro o No. de afiliado"}))

    def filtrar(self, qs):
        return buscar_texto(qs, self.cleaned_data.get("q"), [
            "paciente__nombres", "paciente__apellidos", "seguro__nombre", "numero_afiliado"])