"""Ubicación: apps/Expedientes/forms.py"""
from datetime import timedelta
from decimal import Decimal

from django import forms
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models import Q
from django.utils import timezone

from apps.Citas.models import Cita
from apps.usuarios.forms_base import EstiloFormMixin, FiltroFechasForm, buscar_texto
from apps.usuarios.models import Medico, Paciente

from .models import Consulta, Expediente


class ExpedienteForm(EstiloFormMixin, forms.ModelForm):
    class Meta:
        model = Expediente
        fields = ["paciente", "fecha_apertura", "alergias", "antecedentes_personales",
                  "antecedentes_familiares", "enfermedades_cronicas", "cirugias_previas",
                  "habitos", "observaciones_generales", "activo"]
        widgets = {n: forms.Textarea(attrs={"rows": 3}) for n in (
            "alergias", "antecedentes_personales", "antecedentes_familiares",
            "enfermedades_cronicas", "cirugias_previas", "habitos", "observaciones_generales")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["paciente"].disabled = True  # un expediente no cambia de paciente
        else:
            # Solo pacientes que todavía no tienen expediente.
            self.fields["paciente"].queryset = Paciente.objects.filter(
                activo=True, expediente__isnull=True)


class ConsultaForm(EstiloFormMixin, forms.ModelForm):
    """Solo médicos. Uso:
        ConsultaForm(request.POST or None, instance=consulta,
                     usuario=request.user, expediente=expediente)
    El médico se asigna solo; nadie más puede registrar consultas ni diagnósticos."""

    RANGOS = {
        "presion_sistolica": (40, 300), "presion_diastolica": (20, 200),
        "frecuencia_cardiaca": (20, 250), "frecuencia_respiratoria": (5, 80),
        "temperatura": (30, 45), "saturacion_oxigeno": (50, 100),
        "peso_kg": (0.3, 500), "talla_cm": (30, 250),
    }

    class Meta:
        model = Consulta
        fields = [
            "expediente", "cita", "fecha", "motivo_consulta", "enfermedad_actual",
            "presion_sistolica", "presion_diastolica", "frecuencia_cardiaca",
            "frecuencia_respiratoria", "temperatura", "saturacion_oxigeno",
            "peso_kg", "talla_cm", "diagnostico", "codigo_cie10", "tratamiento",
            "observaciones", "requiere_seguimiento", "fecha_seguimiento",
        ]
        widgets = {n: forms.Textarea(attrs={"rows": 3}) for n in (
            "enfermedad_actual", "diagnostico", "tratamiento", "observaciones")}
        labels = {
            "presion_sistolica": "Presión sistólica", "presion_diastolica": "Presión diastólica",
            "frecuencia_cardiaca": "Frec. cardíaca (lpm)", "frecuencia_respiratoria": "Frec. respiratoria (rpm)",
            "temperatura": "Temperatura (°C)", "saturacion_oxigeno": "Saturación O₂ (%)",
            "peso_kg": "Peso (kg)", "talla_cm": "Talla (cm)",
        }

    def __init__(self, *args, usuario, expediente=None, **kwargs):
        super().__init__(*args, **kwargs)
        medico = Medico.objects.filter(usuario=usuario, activo=True).first()
        if not usuario.es_medico or medico is None:
            raise PermissionDenied("Solo un médico activo puede registrar consultas.")
        if self.instance.pk:
            if self.instance.medico_id != medico.pk:
                raise PermissionDenied("Solo el médico que la registró puede editarla.")
            expediente = self.instance.expediente
        else:
            self.instance.medico = medico

        citas = Cita.objects.filter(medico=medico).exclude(estado="CANCELADA")
        citas = citas.filter(Q(consulta__isnull=True) | Q(pk=self.instance.cita_id))
        if expediente is not None:
            del self.fields["expediente"]
            self.instance.expediente = expediente
            citas = citas.filter(paciente=expediente.paciente)
        else:
            self.fields["expediente"].queryset = Expediente.objects.filter(
                activo=True).select_related("paciente")
        self.fields["cita"].queryset = citas.select_related("paciente")

        for nombre, (minimo, maximo) in self.RANGOS.items():
            campo = self.fields[nombre]
            campo.widget.attrs.update({"min": minimo, "max": maximo})
            campo.validators += [MinValueValidator(Decimal(str(minimo))),
                                 MaxValueValidator(Decimal(str(maximo)))]

    def clean_fecha(self):
        fecha = self.cleaned_data["fecha"]
        if fecha > timezone.now() + timedelta(minutes=5):
            raise ValidationError("La fecha de la consulta no puede ser futura.")
        return fecha

    def clean(self):
        datos = super().clean()
        sis, dia = datos.get("presion_sistolica"), datos.get("presion_diastolica")
        if sis and dia and dia >= sis:
            self.add_error("presion_diastolica", "Debe ser menor que la sistólica.")
        return datos


class FiltroConsultaForm(FiltroFechasForm):
    q = forms.CharField(label="Buscar", required=False, widget=forms.TextInput(
        attrs={"placeholder": "Paciente, No. de expediente, diagnóstico o CIE-10"}))
    medico = forms.ModelChoiceField(queryset=Medico.objects.select_related("usuario"),
                                    required=False, empty_label="Todos los médicos")
    seguimiento = forms.BooleanField(label="Solo con seguimiento pendiente", required=False)
    field_order = ["q", "medico", "seguimiento", "desde", "hasta"]

    def filtrar(self, qs):
        datos = self.cleaned_data
        qs = buscar_texto(qs, datos.get("q"), [
            "expediente__paciente__nombres", "expediente__paciente__apellidos",
            "expediente__numero", "diagnostico", "codigo_cie10"])
        if datos.get("medico"):
            qs = qs.filter(medico=datos["medico"])
        if datos.get("seguimiento"):
            qs = qs.filter(requiere_seguimiento=True)
        return self.filtrar_fechas(qs, "fecha")