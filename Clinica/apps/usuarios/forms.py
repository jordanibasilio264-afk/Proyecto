"""Ubicación: apps/usuarios/forms.py
Usuarios, contraseñas, especialidades, médicos (con horarios) y pacientes."""
import re
from datetime import date

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    PasswordChangeForm, PasswordResetForm, SetPasswordForm, UserCreationForm,
)
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.forms import BaseInlineFormSet, inlineformset_factory

from .forms_base import EstiloFormMixin, buscar_texto, limpiar_nombre, limpiar_telefono
from .models import Especialidad, HorarioMedico, Medico, Paciente

Usuario = get_user_model()


# ----------------------------------------------------------------- Usuarios (RF-01)
class UsuarioCrearForm(EstiloFormMixin, UserCreationForm):
    """Solo para el Administrador: crea usuarios de cualquier rol."""

    class Meta:
        model = Usuario
        fields = ("first_name", "last_name", "email", "telefono", "rol")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True
        self.fields["first_name"].label = "Nombre"
        self.fields["last_name"].label = "Apellido"
        self.fields["telefono"].label = "Teléfono"
        self.fields["password1"].label = "Contraseña"
        self.fields["password2"].label = "Confirmar contraseña"

    def clean_telefono(self):
        return limpiar_telefono(self.cleaned_data.get("telefono"))


class UsuarioEditarForm(EstiloFormMixin, forms.ModelForm):
    """Editar, asignar rol y activar/desactivar. Sin contraseña."""

    class Meta:
        model = Usuario
        fields = ("first_name", "last_name", "email", "telefono", "rol", "is_active")
        labels = {
            "first_name": "Nombre", "last_name": "Apellido",
            "telefono": "Teléfono", "is_active": "Activo",
        }

    def __init__(self, *args, usuario_actual=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True
        # Evita que un administrador se quite el acceso a sí mismo.
        if usuario_actual is not None and self.instance.pk == usuario_actual.pk:
            for nombre in ("rol", "is_active"):
                self.fields[nombre].disabled = True
                self.fields[nombre].help_text = "No puedes cambiar tu propio rol ni desactivarte."

    def clean_telefono(self):
        return limpiar_telefono(self.cleaned_data.get("telefono"))


class PerfilForm(EstiloFormMixin, forms.ModelForm):
    """Cada usuario edita sus propios datos básicos (no el rol)."""

    class Meta:
        model = Usuario
        fields = ("first_name", "last_name", "telefono")
        labels = {"first_name": "Nombre", "last_name": "Apellido", "telefono": "Teléfono"}

    def clean_telefono(self):
        return limpiar_telefono(self.cleaned_data.get("telefono"))


# ----------------------------------------------------------------- Contraseñas
class CambiarPasswordForm(EstiloFormMixin, PasswordChangeForm):
    """El usuario cambia su contraseña (pide la actual)."""


class NuevaPasswordForm(EstiloFormMixin, SetPasswordForm):
    """El admin asigna una contraseña, o el paso final de 'recuperar contraseña'."""


class RecuperarPasswordForm(EstiloFormMixin, PasswordResetForm):
    """Paso 1 de recuperar contraseña: pide el correo."""


# ----------------------------------------------------------------- Especialidades (RF-05)
class EspecialidadForm(EstiloFormMixin, forms.ModelForm):
    class Meta:
        model = Especialidad
        fields = ("nombre", "descripcion", "activa")

    def clean_nombre(self):
        nombre = limpiar_nombre(self.cleaned_data["nombre"])
        repetida = Especialidad.objects.filter(nombre__iexact=nombre).exclude(pk=self.instance.pk)
        if repetida.exists():
            raise ValidationError("Ya existe una especialidad con ese nombre.")
        return nombre


# ----------------------------------------------------------------- Médicos (RF-04)
class MedicoForm(EstiloFormMixin, forms.ModelForm):
    class Meta:
        model = Medico
        fields = ("usuario", "especialidades", "exequatur", "cedula",
                  "consultorio", "duracion_cita_minutos", "activo")
        widgets = {"especialidades": forms.SelectMultiple(attrs={"size": 6})}
        labels = {"usuario": "Usuario (rol Médico)", "duracion_cita_minutos": "Duración de cita (min)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo usuarios con rol Médico que aún no tengan perfil.
        condicion = Q(rol=Usuario.Roles.MEDICO, perfil_medico__isnull=True)
        especialidades = Q(activa=True)
        if self.instance.pk:
            condicion |= Q(pk=self.instance.usuario_id)
            especialidades |= Q(medicos=self.instance)
            self.fields["usuario"].disabled = True
        self.fields["usuario"].queryset = Usuario.objects.filter(condicion)
        self.fields["especialidades"].queryset = Especialidad.objects.filter(especialidades).distinct()
        self.fields["duracion_cita_minutos"].widget.attrs.update({"min": 5, "max": 240, "step": 5})

    def clean_duracion_cita_minutos(self):
        minutos = self.cleaned_data["duracion_cita_minutos"]
        if not 5 <= minutos <= 240:
            raise ValidationError("La duración debe estar entre 5 y 240 minutos.")
        return minutos


class HorarioMedicoForm(EstiloFormMixin, forms.ModelForm):
    class Meta:
        model = HorarioMedico
        fields = ("dia_semana", "hora_inicio", "hora_fin", "activo")


class BaseHorarioFormSet(BaseInlineFormSet):
    """Detecta horarios que se cruzan dentro del mismo envío."""

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        franjas = []
        for form in self.forms:
            datos = form.cleaned_data
            if not datos or datos.get("DELETE") or not datos.get("activo", True):
                continue
            franjas.append((datos["dia_semana"], datos["hora_inicio"], datos["hora_fin"]))
        franjas.sort()
        for a, b in zip(franjas, franjas[1:]):
            if a[0] == b[0] and b[1] < a[2]:
                raise ValidationError("Hay horarios que se cruzan el mismo día.")


HorarioMedicoFormSet = inlineformset_factory(
    Medico, HorarioMedico, form=HorarioMedicoForm, formset=BaseHorarioFormSet,
    extra=1, can_delete=True,
)


# ----------------------------------------------------------------- Pacientes (RF-03)
class PacienteForm(EstiloFormMixin, forms.ModelForm):
    class Meta:
        model = Paciente
        fields = (
            "nombres", "apellidos", "cedula", "fecha_nacimiento", "sexo", "tipo_sangre",
            "telefono", "email", "direccion",
            "contacto_emergencia_nombre", "contacto_emergencia_telefono", "activo",
        )
        labels = {
            "cedula": "Cédula / documento",
            "telefono": "Teléfono",
            "direccion": "Dirección",
            "contacto_emergencia_nombre": "Contacto de emergencia",
            "contacto_emergencia_telefono": "Teléfono de emergencia",
        }

    def clean_nombres(self):
        return limpiar_nombre(self.cleaned_data["nombres"])

    def clean_apellidos(self):
        return limpiar_nombre(self.cleaned_data["apellidos"])

    def clean_cedula(self):
        valor = re.sub(r"[\s-]", "", self.cleaned_data.get("cedula") or "")
        return valor or None  # vacío = NULL (evita choques con el campo único)

    def clean_fecha_nacimiento(self):
        fecha = self.cleaned_data["fecha_nacimiento"]
        hoy = date.today()
        if fecha > hoy:
            raise ValidationError("La fecha de nacimiento no puede ser futura.")
        if hoy.year - fecha.year > 120:
            raise ValidationError("Revisa la fecha de nacimiento.")
        return fecha

    def clean_telefono(self):
        return limpiar_telefono(self.cleaned_data.get("telefono"))

    def clean_contacto_emergencia_telefono(self):
        return limpiar_telefono(self.cleaned_data.get("contacto_emergencia_telefono"))


class FiltroPacienteForm(EstiloFormMixin, forms.Form):
    q = forms.CharField(
        label="Buscar", required=False,
        widget=forms.TextInput(attrs={"placeholder": "Nombre, cédula, teléfono o correo"}),
    )
    activo = forms.ChoiceField(
        label="Estado", required=False,
        choices=[("", "Todos"), ("1", "Activos"), ("0", "Inactivos")],
    )

    def filtrar(self, qs):
        datos = self.cleaned_data
        qs = buscar_texto(qs, datos.get("q"), ["nombres", "apellidos", "cedula", "telefono", "email"])
        if datos.get("activo") in ("0", "1"):
            qs = qs.filter(activo=datos["activo"] == "1")
        return qs