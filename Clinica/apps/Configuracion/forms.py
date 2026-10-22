"""Ubicación: apps/Configuracion/forms.py"""
from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.usuarios.forms_base import EstiloFormMixin, limpiar_telefono
from apps.usuarios.models import (Especialidad, Medico,HorarioMedico, Paciente, Usuarios,
                                  cedula_validator, solo_digitos)
from django.db.models import Q

from .models import ConfiguracionConsultorio

DIAS = "LMXJVSD"  # índice = HorarioMedico.dia_semana (0=Lunes ... 6=Domingo)

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


class DatosClinicaForm(ConfiguracionForm):
    class Meta(ConfiguracionForm.Meta):
        fields = ["nombre_consultorio", "telefono", "email", "direccion",
                  "hora_apertura", "hora_cierre", "duracion_cita_defecto"]


class UsuarioAdminForm(forms.ModelForm):
    # Sin validadores del modelo: la cédula se limpia (quita guiones) antes de validar
    cedula = forms.CharField(label="Cédula", required=False, max_length=15)
    password1 = forms.CharField(
        label="Contraseña", required=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    password2 = forms.CharField(
        label="Confirmar contraseña", required=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    especialidad = forms.ModelChoiceField(
        label="Especialidad", required=False, empty_label="— Sin especialidad —",
        queryset=Especialidad.objects.filter(activa=True))
    fecha_nacimiento = forms.DateField(
        label="Fecha de nacimiento", required=False,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    sexo = forms.ChoiceField(
        label="Sexo", required=False,
        choices=[("", "— No indicado —")] + list(Paciente.Sexo.choices))
    
        # --- Médico ---
    exequatur = forms.CharField(label="Exequátur / No. de colegiatura", required=False, max_length=30)
    consultorio = forms.CharField(label="Consultorio / sala", required=False, max_length=50)
    duracion_cita_minutos = forms.IntegerField(
        label="Duración de cita (min)", required=False, min_value=5, max_value=240, initial=30)
    medico_activo = forms.BooleanField(label="Médico activo", required=False, initial=True)
    dias = forms.MultipleChoiceField(
        label="Días de atención", required=False,
        widget=forms.CheckboxSelectMultiple,
        choices=[(d, d) for d in DIAS], initial=list("LMXJV"))
    hora_inicio = forms.TimeField(
        label="Hora de inicio", required=False, initial="08:00",
        widget=forms.TimeInput(attrs={"type": "time"}, format="%H:%M"))
    hora_fin = forms.TimeField(
        label="Hora de fin", required=False, initial="16:00",
        widget=forms.TimeInput(attrs={"type": "time"}, format="%H:%M"))
    
    # --- Paciente ---
    tipo_sangre = forms.ChoiceField(
        label="Tipo de sangre", required=False,
        choices=[("", "— No indicado —")] + list(Paciente.TipoSangre.choices))
    direccion = forms.CharField(label="Dirección", required=False, max_length=255)
    contacto_emergencia_nombre = forms.CharField(
        label="Contacto de emergencia (nombre)", required=False, max_length=120)
    contacto_emergencia_telefono = forms.CharField(
        label="Contacto de emergencia (teléfono)", required=False, max_length=20)
    paciente_activo = forms.BooleanField(label="Paciente activo", required=False, initial=True)

    class Meta:
        model = Usuarios
        fields = ["first_name", "last_name", "email", "telefono",
                  "cedula", "rol", "is_active"]
        labels = {
            "first_name": "Nombres", "last_name": "Apellidos",
            "email": "Correo electrónico", "telefono": "Teléfono", "rol": "Rol",
        }

    def __init__(self, *args,solicitante=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.solicitante = solicitante
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True
        # El admin no puede crear ni asignar el rol Administrador
        self.fields["rol"].choices = [
            (v, l) for v, l in Usuarios.Roles.choices if v != "ADMIN"
        ]
        if self.instance.pk:
            self.fields["password1"].label = "Nueva contraseña (opcional)"
            self.fields["password2"].label = "Confirmar nueva contraseña"
        else:
            self.fields["password1"].required = True
        medico = getattr(self.instance, "perfil_medico", None)
        ficha = getattr(self.instance, "perfil_paciente", None)
        if medico:
            self.initial.update({
                "especialidad": medico.especialidades.first(),
                "exequatur": medico.exequatur,
                "consultorio": medico.consultorio,
                "duracion_cita_minutos": medico.duracion_cita_minutos,
                "medico_activo": medico.activo,
            })
            horarios = list(medico.horarios.filter(activo=True).order_by("dia_semana"))
            if horarios:
                self.initial["dias"] = [DIAS[h.dia_semana] for h in horarios]
                self.initial["hora_inicio"] = horarios[0].hora_inicio
                self.initial["hora_fin"] = horarios[0].hora_fin
            if ficha:
                self.initial.update({
                    "fecha_nacimiento": ficha.fecha_nacimiento,
                    "sexo": ficha.sexo,
                    "tipo_sangre": ficha.tipo_sangre,
                    "direccion": ficha.direccion,
                    "contacto_emergencia_nombre": ficha.contacto_emergencia_nombre,
                    "contacto_emergencia_telefono": ficha.contacto_emergencia_telefono,
                    "paciente_activo": ficha.activo,
            })
        if solicitante and solicitante.rol == Usuarios.Roles.RECEPCIONISTA:
            self.fields["rol"].choices = [(Usuarios.Roles.PACIENTE, Usuarios.Roles.PACIENTE.label)]
            self.initial["rol"] = Usuarios.Roles.PACIENTE
            self.fields["rol"].disabled = True

    def clean_exequatur(self):
        valor = (self.cleaned_data.get("exequatur") or "").strip() or None
        if valor:
            propio = getattr(self.instance, "perfil_medico", None)
            if Medico.objects.filter(exequatur=valor).exclude(pk=getattr(propio, "pk", None)).exists():
                raise ValidationError("Ese exequátur ya pertenece a otro médico.")
        return valor

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        otros = Usuarios.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if otros.exists():
            raise ValidationError("Ese correo ya está en uso.")
        return email

    def clean_cedula(self):
        cedula = solo_digitos(self.cleaned_data.get("cedula"))
        if not cedula:
            return None
        try:
            cedula_validator(cedula)
        except ValidationError as e:
            raise ValidationError(e.messages)
        # Una ficha sin cuenta con esta cédula se vinculará al guardar, no es conflicto
        propia = Paciente.objects.filter(usuario=self.instance).first() if self.instance.pk else None
        choque = (Paciente.objects.filter(cedula=cedula, usuario__isnull=False)
                  .exclude(pk=getattr(propia, "pk", None)))
        if choque.exists():
            raise ValidationError("Esa cédula ya está registrada en otro paciente.")
        return cedula

    def clean(self):
        datos = super().clean()
        p1, p2 = datos.get("password1"), datos.get("password2")
        if p1 or p2:
            if p1 != p2:
                self.add_error("password2", "Las contraseñas no coinciden.")
            else:
                try:
                    validate_password(p1)
                except ValidationError as e:
                    self.add_error("password1", e)

        if datos.get("rol") == Usuarios.Roles.MEDICO and datos.get("dias"):
            ini, fin = datos.get("hora_inicio"), datos.get("hora_fin")
            if not ini or not fin:
                self.add_error("hora_fin", "Indica la hora de inicio y de fin.")
            elif fin <= ini:
                self.add_error("hora_fin", "La hora de fin debe ser posterior a la de inicio.")
        return datos

    def save(self, commit=True):
        with transaction.atomic():
            u = super().save(commit=False)
            if self.cleaned_data.get("password1"):
                u.set_password(self.cleaned_data["password1"])
            u.save()
            self._asegurar_perfil(u)
        return u

    def _asegurar_perfil(self, u):
        cd = self.cleaned_data
        cambio = lambda *campos: any(c in self.changed_data for c in campos)

        if u.rol == Usuarios.Roles.MEDICO:
            medico, _ = Medico.objects.get_or_create(usuario=u)
            if "exequatur" in self.changed_data:
                medico.exequatur = cd.get("exequatur")
            if "consultorio" in self.changed_data:
                medico.consultorio = cd.get("consultorio") or ""
            if "duracion_cita_minutos" in self.changed_data and cd.get("duracion_cita_minutos"):
                medico.duracion_cita_minutos = cd["duracion_cita_minutos"]
            if "medico_activo" in self.changed_data:
                medico.activo = cd.get("medico_activo", True)
            medico.save()
            if cd.get("especialidad") and "especialidad" in self.changed_data:
                medico.especialidades.set([cd["especialidad"]])

            # Horario: se crea la primera vez y después solo si cambió
            if cd.get("dias") and (not medico.horarios.exists()
                                   or cambio("dias", "hora_inicio", "hora_fin")):
                marcados = [DIAS.index(d) for d in cd["dias"]]
                for i in range(7):
                    if i in marcados:
                        HorarioMedico.objects.update_or_create(
                            medico=medico, dia_semana=i,
                            defaults={"hora_inicio": cd["hora_inicio"],
                                      "hora_fin": cd["hora_fin"], "activo": True})
                    else:
                        HorarioMedico.objects.filter(medico=medico, dia_semana=i).update(activo=False)

        elif u.rol == Usuarios.Roles.PACIENTE:
            ficha = Paciente.objects.filter(usuario=u).first()
            if not ficha:
                # Ficha creada antes por recepción (sin cuenta): se vincula, no se duplica
                q = Q(email__iexact=u.email)
                if u.cedula:
                    q |= Q(cedula=u.cedula)
                ficha = Paciente.objects.filter(usuario__isnull=True).filter(q).first() or Paciente()
                ficha.usuario = u
            ficha.nombres, ficha.apellidos = u.first_name, u.last_name
            ficha.email, ficha.telefono, ficha.cedula = u.email, u.telefono, u.cedula

            # Solo se escribe lo que el admin cambió; el resto conserva su valor
            if "fecha_nacimiento" in self.changed_data:
                ficha.fecha_nacimiento = cd.get("fecha_nacimiento") or None
            for campo in ("sexo", "tipo_sangre", "direccion",
                          "contacto_emergencia_nombre", "contacto_emergencia_telefono"):
                if campo in self.changed_data:
                    setattr(ficha, campo, cd.get(campo) or "")
            if "paciente_activo" in self.changed_data:
                ficha.activo = cd.get("paciente_activo", True)
            ficha.save()  # Paciente.save() sincroniza de vuelta al usuario