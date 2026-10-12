"""Ubicación: apps/Medicamentos/forms.py"""
from datetime import date

from django import forms
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.forms import inlineformset_factory

from apps.Expedientes.models import Consulta
from apps.usuarios.forms_base import EstiloFormMixin, FiltroFechasForm, buscar_texto, limpiar_nombre
from apps.usuarios.models import Medico

from .models import DetalleReceta, Medicamento, Receta


class MedicamentoForm(EstiloFormMixin, forms.ModelForm):
    class Meta:
        model = Medicamento
        fields = ["nombre_comercial", "nombre_generico", "concentracion", "forma",
                  "laboratorio", "indicaciones", "contraindicaciones", "activo"]
        widgets = {"indicaciones": forms.Textarea(attrs={"rows": 3}),
                   "contraindicaciones": forms.Textarea(attrs={"rows": 3})}

    def clean_nombre_comercial(self):
        return limpiar_nombre(self.cleaned_data["nombre_comercial"])

    def clean_nombre_generico(self):
        return limpiar_nombre(self.cleaned_data["nombre_generico"])


class RecetaForm(EstiloFormMixin, forms.ModelForm):
    """Solo médicos, y solo sobre consultas propias.
    Uso: RecetaForm(request.POST or None, instance=receta, usuario=request.user, consulta=consulta)"""

    class Meta:
        model = Receta
        fields = ["consulta", "indicaciones_generales", "vigente_hasta"]
        widgets = {"indicaciones_generales": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, usuario, consulta=None, **kwargs):
        super().__init__(*args, **kwargs)
        medico = Medico.objects.filter(usuario=usuario, activo=True).first()
        if not usuario.es_medico or medico is None:
            raise PermissionDenied("Solo un médico activo puede generar recetas.")
        if self.instance.pk:
            consulta = self.instance.consulta
        if consulta is not None:
            if consulta.medico_id != medico.pk:
                raise PermissionDenied("Solo el médico de la consulta puede recetar.")
            del self.fields["consulta"]
            self.instance.consulta = consulta
        else:
            self.fields["consulta"].queryset = Consulta.objects.filter(
                medico=medico).select_related("expediente__paciente")

    def clean_vigente_hasta(self):
        fecha = self.cleaned_data.get("vigente_hasta")
        if fecha and "vigente_hasta" in self.changed_data and fecha < date.today():
            raise ValidationError("La vigencia no puede estar en el pasado.")
        return fecha


class DetalleRecetaForm(EstiloFormMixin, forms.ModelForm):
    class Meta:
        model = DetalleReceta
        fields = ["medicamento", "dosis", "frecuencia", "duracion_dias",
                  "via_administracion", "cantidad", "instrucciones"]
        labels = {"duracion_dias": "Duración (días)", "via_administracion": "Vía"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        condicion = Q(activo=True)
        if self.instance.medicamento_id:
            condicion |= Q(pk=self.instance.medicamento_id)
        self.fields["medicamento"].queryset = Medicamento.objects.filter(condicion)
        self.fields["cantidad"].widget.attrs["min"] = 1


# Receta + sus medicamentos en una sola pantalla (mínimo uno).
DetalleRecetaFormSet = inlineformset_factory(
    Receta, DetalleReceta, form=DetalleRecetaForm,
    extra=1, can_delete=True, min_num=1, validate_min=True,
)


class FiltroMedicamentoForm(EstiloFormMixin, forms.Form):
    q = forms.CharField(label="Buscar", required=False, widget=forms.TextInput(
        attrs={"placeholder": "Nombre comercial, genérico o laboratorio"}))
    forma = forms.ChoiceField(required=False, choices=[("", "Todas las formas"), *Medicamento.Forma.choices])
    activo = forms.ChoiceField(label="Estado", required=False,
                               choices=[("", "Todos"), ("1", "Activos"), ("0", "Inactivos")])

    def filtrar(self, qs):
        datos = self.cleaned_data
        qs = buscar_texto(qs, datos.get("q"), ["nombre_comercial", "nombre_generico", "laboratorio"])
        if datos.get("forma"):
            qs = qs.filter(forma=datos["forma"])
        if datos.get("activo") in ("0", "1"):
            qs = qs.filter(activo=datos["activo"] == "1")
        return qs


class FiltroRecetaForm(FiltroFechasForm):
    q = forms.CharField(label="Buscar", required=False, widget=forms.TextInput(
        attrs={"placeholder": "No. de receta, paciente o medicamento"}))
    field_order = ["q", "desde", "hasta"]

    def filtrar(self, qs):
        qs = buscar_texto(qs, self.cleaned_data.get("q"), [
            "numero", "consulta__expediente__paciente__nombres",
            "consulta__expediente__paciente__apellidos",
            "detalles__medicamento__nombre_comercial",
            "detalles__medicamento__nombre_generico"]).distinct()
        return self.filtrar_fechas(qs, "fecha")