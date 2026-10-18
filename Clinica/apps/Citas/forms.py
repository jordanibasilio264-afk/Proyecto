"""Ubicación: apps/Citas/forms.py"""
from datetime import timedelta

from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.usuarios.forms_base import EstiloFormMixin, FiltroFechasForm, buscar_texto
from apps.usuarios.models import Medico, Paciente

from .models import Cita


def validar_horario_medico(medico, inicio, duracion):
    """Si el médico tiene horario configurado, la cita debe caer dentro de él."""
    horarios = medico.horarios.filter(activo=True)
    if not horarios.exists():
        return  # sin horario configurado no se bloquea
    local_ini = timezone.localtime(inicio) if timezone.is_aware(inicio) else inicio
    local_fin = local_ini + timedelta(minutes=duracion)
    if local_fin.date() == local_ini.date():
        for h in horarios.filter(dia_semana=local_ini.weekday()):
            if h.hora_inicio <= local_ini.time() and local_fin.time() <= h.hora_fin:
                return
    raise ValidationError("El médico no atiende en ese horario. Revisa su agenda.")


class CitaForm(EstiloFormMixin, forms.ModelForm):
    """Registrar / editar cita.
    Uso: CitaForm(request.POST or None, instance=cita, usuario=request.user)
    - Si el usuario es Paciente, la cita se asigna a él automáticamente.
    - Si es Médico, la cita se asigna a su propia agenda."""

    class Meta:
        model = Cita
        fields = ["paciente", "medico", "inicio", "duracion_minutos", "motivo", "notas"]
        widgets = {"notas": forms.Textarea(attrs={"rows": 3})}
        labels = {"inicio": "Fecha y hora", "duracion_minutos": "Duración (min)"}

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        self._error_perfil = None
        self.fields["paciente"].queryset = Paciente.objects.filter(activo=True)
        self.fields["medico"].queryset = (
            Medico.objects.filter(activo=True)
            .select_related("usuario").prefetch_related("especialidades")
        )
        self.fields["medico"].label_from_instance = self._etiqueta_medico
        self.fields["duracion_minutos"].widget.attrs.update({"min": 5, "max": 240, "step": 5})

        if usuario is not None and usuario.es_paciente:
            perfil = getattr(usuario, "perfil_paciente", None)
            del self.fields["paciente"]
            if perfil is None:
                self._error_perfil = "Tu cuenta no tiene un perfil de paciente asociado."
            else:
                self.instance.paciente = perfil
        elif usuario is not None and usuario.es_medico:
            perfil = getattr(usuario, "perfil_medico", None)
            del self.fields["medico"]
            if perfil is None:
                self._error_perfil = "Tu cuenta no tiene un perfil de médico asociado."
            else:
                self.instance.medico = perfil

    @staticmethod
    def _etiqueta_medico(medico):
        """'Dr(a). Ana Pérez - Cardiología, Medicina interna'"""
        especialidades = ", ".join(e.nombre for e in medico.especialidades.all())
        return f"{medico} - {especialidades}" if especialidades else str(medico)

    def clean_duracion_minutos(self):
        minutos = self.cleaned_data["duracion_minutos"]
        if not 5 <= minutos <= 240:
            raise ValidationError("La duración debe estar entre 5 y 240 minutos.")
        return minutos

    def clean(self):
        datos = super().clean()
        if self._error_perfil:
            raise ValidationError(self._error_perfil)
        inicio, duracion = datos.get("inicio"), datos.get("duracion_minutos")
        medico = datos.get("medico") or getattr(self.instance, "medico", None)
        if inicio and duracion and medico:
            if (not self.instance.pk or "inicio" in self.changed_data) and inicio < timezone.now():
                self.add_error("inicio", "No se pueden agendar citas en el pasado.")
            else:
                try:
                    validar_horario_medico(medico, inicio, duracion)
                except ValidationError as e:
                    self.add_error("inicio", e)
        return datos

    def save(self, commit=True):
        cita = super().save(commit=False)
        if cita._state.adding and self.usuario is not None:
            cita.creada_por = self.usuario
        if commit:
            cita.save()
        return cita


class ReprogramarCitaForm(EstiloFormMixin, forms.Form):
    """Mueve una cita: la original queda 'Reprogramada' y se crea una nueva.
    Uso: form = ReprogramarCitaForm(request.POST or None, cita=cita, usuario=request.user)
         if form.is_valid(): nueva = form.guardar()"""

    inicio = forms.DateTimeField(label="Nueva fecha y hora")
    duracion_minutos = forms.IntegerField(label="Duración (min)", min_value=5, max_value=240)
    motivo = forms.CharField(label="Motivo del cambio", max_length=200, required=False)

    def __init__(self, *args, cita, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.cita = cita
        self.usuario = usuario
        self.fields["duracion_minutos"].initial = cita.duracion_minutos

    def clean(self):
        datos = super().clean()
        if self.cita.estado not in ("PROGRAMADA", "CONFIRMADA"):
            raise ValidationError("Solo se pueden reprogramar citas programadas o confirmadas.")
        inicio, duracion = datos.get("inicio"), datos.get("duracion_minutos")
        if inicio and duracion:
            if inicio < timezone.now():
                self.add_error("inicio", "No se pueden agendar citas en el pasado.")
                return datos
            try:
                validar_horario_medico(self.cita.medico, inicio, duracion)
            except ValidationError as e:
                self.add_error("inicio", e)
                return datos
            fin = inicio + timedelta(minutes=duracion)
            otras = Cita.objects.filter(
                estado__in=Cita.ESTADOS_ACTIVOS, inicio__lt=fin, fin__gt=inicio
            ).exclude(pk=self.cita.pk)
            if otras.filter(medico=self.cita.medico).exists():
                self.add_error("inicio", "El médico ya tiene una cita en ese horario.")
            if otras.filter(paciente=self.cita.paciente).exists():
                self.add_error("inicio", "El paciente ya tiene una cita en ese horario.")
        return datos

    @transaction.atomic
    def guardar(self):
        anterior = self.cita
        motivo = self.cleaned_data.get("motivo", "")
        anterior.estado = Cita.Estado.REPROGRAMADA
        anterior.motivo_cancelacion = f"Reprogramada. {motivo}".strip()
        anterior.save()  # primero libera el horario viejo
        nueva = Cita(
            paciente=anterior.paciente, medico=anterior.medico,
            inicio=self.cleaned_data["inicio"],
            duracion_minutos=self.cleaned_data["duracion_minutos"],
            motivo=anterior.motivo, notas=anterior.notas,
            reprogramada_desde=anterior, creada_por=self.usuario,
        )
        nueva.save()
        return nueva


class CancelarCitaForm(EstiloFormMixin, forms.Form):
    """Uso: form = CancelarCitaForm(request.POST or None, cita=cita); form.guardar()"""

    motivo = forms.CharField(label="Motivo de la cancelación", max_length=255,
                             widget=forms.Textarea(attrs={"rows": 2}))

    def __init__(self, *args, cita, **kwargs):
        super().__init__(*args, **kwargs)
        self.cita = cita

    def clean(self):
        datos = super().clean()
        if self.cita.estado == Cita.Estado.ATENDIDA:
            raise ValidationError("Una cita atendida no puede cancelarse.")
        if self.cita.estado == Cita.Estado.CANCELADA:
            raise ValidationError("La cita ya está cancelada.")
        return datos

    def guardar(self):
        self.cita.cancelar(self.cleaned_data["motivo"])
        return self.cita


class FiltroCitaForm(FiltroFechasForm):
    """RF-06 / RF-18: buscar citas por paciente, médico, estado o fecha."""

    q = forms.CharField(label="Buscar", required=False,
                        widget=forms.TextInput(attrs={"placeholder": "Paciente, cédula o motivo"}))
    medico = forms.ModelChoiceField(queryset=Medico.objects.select_related("usuario"),
                                    required=False, empty_label="Todos los médicos", label="Médico")
    estado = forms.ChoiceField(required=False, choices=[("", "Todos los estados"), *Cita.Estado.choices])
    field_order = ["q", "medico", "estado", "desde", "hasta"]

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        if usuario is not None and usuario.es_paciente:
            # El paciente no busca por paciente/cédula ni elige entre todos los médicos.
            self.fields["q"].widget.attrs["placeholder"] = "Motivo de la cita"
            self.fields["medico"].queryset = Medico.objects.filter(
                citas__paciente__usuario=usuario
            ).distinct().select_related("usuario")

    def filtrar(self, qs):
        datos = self.cleaned_data
        qs = buscar_texto(qs, datos.get("q"),
                          ["paciente__nombres", "paciente__apellidos", "paciente__cedula", "motivo"])
        if datos.get("medico"):
            qs = qs.filter(medico=datos["medico"])
        if datos.get("estado"):
            qs = qs.filter(estado=datos["estado"])
        campos = ["motivo"] if getattr(self, "usuario", None) and self.usuario.es_paciente else \
         ["paciente__nombres", "paciente__apellidos", "paciente__cedula", "motivo"]
        qs = buscar_texto(qs, datos.get("q"), campos)
        return self.filtrar_fechas(qs, "inicio")