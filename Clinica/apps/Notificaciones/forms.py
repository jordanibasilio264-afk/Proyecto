"""Ubicación: apps/Notificaciones/forms.py"""
from django import forms

from apps.usuarios.forms_base import EstiloFormMixin, FiltroFechasForm, buscar_texto

from .models import Notificacion


class NotificacionForm(EstiloFormMixin, forms.ModelForm):
    class Meta:
        model = Notificacion
        fields = ["usuario", "paciente", "cita", "tipo", "canal", "titulo",
                  "mensaje", "programada_para"]
        widgets = {"mensaje": forms.Textarea(attrs={"rows": 4})}
        labels = {"programada_para": "Enviar el"}

    def clean(self):
        datos = super().clean()
        canal, usuario, paciente = datos.get("canal"), datos.get("usuario"), datos.get("paciente")
        if canal == Notificacion.Canal.EMAIL:
            if not ((usuario and usuario.email) or (paciente and paciente.email)):
                self.add_error("canal", "El destinatario no tiene correo electrónico registrado.")
        elif canal in (Notificacion.Canal.SMS, Notificacion.Canal.WHATSAPP):
            if not ((usuario and usuario.telefono) or (paciente and paciente.telefono)):
                self.add_error("canal", "El destinatario no tiene teléfono registrado.")
        return datos


class FiltroNotificacionForm(FiltroFechasForm):
    q = forms.CharField(label="Buscar", required=False, widget=forms.TextInput(
        attrs={"placeholder": "Título, mensaje o destinatario"}))
    tipo = forms.ChoiceField(required=False, choices=[("", "Todos los tipos"), *Notificacion.Tipo.choices])
    estado = forms.ChoiceField(required=False, choices=[("", "Todos los estados"), *Notificacion.Estado.choices])
    field_order = ["q", "tipo", "estado", "desde", "hasta"]

    def filtrar(self, qs):
        datos = self.cleaned_data
        qs = buscar_texto(qs, datos.get("q"), [
            "titulo", "mensaje", "usuario__email", "paciente__nombres", "paciente__apellidos"])
        if datos.get("tipo"):
            qs = qs.filter(tipo=datos["tipo"])
        if datos.get("estado"):
            qs = qs.filter(estado=datos["estado"])
        return self.filtrar_fechas(qs, "programada_para")