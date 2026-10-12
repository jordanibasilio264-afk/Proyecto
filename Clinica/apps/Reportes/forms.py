"""Ubicación: apps/Reportes/forms.py
Uso: form = ReporteForm(request.POST or None, usuario=request.user)
     if form.is_valid(): parametros = form.parametros()  # guardar en ReporteGenerado.parametros"""
from django import forms
from django.core.exceptions import ValidationError

from apps.usuarios.forms_base import EstiloFormMixin
from apps.usuarios.models import Medico, Paciente

from .models import ReporteGenerado


class ReporteForm(EstiloFormMixin, forms.Form):
    tipo = forms.ChoiceField(label="Tipo de reporte", choices=ReporteGenerado.Tipo.choices)
    formato = forms.ChoiceField(choices=ReporteGenerado.Formato.choices, initial="PDF")
    desde = forms.DateField(label="Desde", required=False)
    hasta = forms.DateField(label="Hasta", required=False)
    medico = forms.ModelChoiceField(queryset=Medico.objects.select_related("usuario"),
                                    required=False, empty_label="Todos los médicos")
    paciente = forms.ModelChoiceField(queryset=Paciente.objects.filter(activo=True),
                                      required=False, empty_label="Todos los pacientes")

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        if usuario is not None:
            # El reporte de pagos solo para quien puede ver ingresos.
            if not usuario.tiene_permiso("pagos.ver_ingresos"):
                self.fields["tipo"].choices = [
                    c for c in self.fields["tipo"].choices
                    if c[0] != ReporteGenerado.Tipo.PAGOS]
            # Un médico solo reporta sobre sus propios pacientes y consultas.
            if usuario.es_medico:
                self.fields["medico"].queryset = Medico.objects.filter(usuario=usuario)
                self.fields["medico"].empty_label = None
                self.fields["medico"].required = True

    def clean(self):
        datos = super().clean()
        desde, hasta = datos.get("desde"), datos.get("hasta")
        if desde and hasta and desde > hasta:
            raise ValidationError("La fecha «desde» no puede ser posterior a «hasta».")
        return datos

    def parametros(self):
        """Filtros listos para guardarse como JSON."""
        d = self.cleaned_data
        return {
            "tipo": d["tipo"],
            "desde": d["desde"].isoformat() if d.get("desde") else None,
            "hasta": d["hasta"].isoformat() if d.get("hasta") else None,
            "medico_id": d["medico"].pk if d.get("medico") else None,
            "paciente_id": d["paciente"].pk if d.get("paciente") else None,
        }