"""Ubicación: apps/Auditoria/forms.py  (solo filtros: la auditoría no se edita)"""
from django import forms

from apps.usuarios.forms_base import FiltroFechasForm, buscar_texto

from .models import RegistroAcceso, RegistroAuditoria


class FiltroAuditoriaForm(FiltroFechasForm):
    q = forms.CharField(label="Buscar", required=False, widget=forms.TextInput(
        attrs={"placeholder": "Usuario, descripción o ID del objeto"}))
    accion = forms.ChoiceField(required=False, choices=[("", "Todas las acciones"), *RegistroAuditoria.Accion.choices])
    modelo = forms.CharField(label="Módulo", required=False, widget=forms.TextInput(
        attrs={"placeholder": "Ej. Citas.Cita"}))
    field_order = ["q", "accion", "modelo", "desde", "hasta"]

    def filtrar(self, qs):
        datos = self.cleaned_data
        qs = buscar_texto(qs, datos.get("q"), ["usuario__email", "descripcion", "objeto_id"])
        if datos.get("accion"):
            qs = qs.filter(accion=datos["accion"])
        if datos.get("modelo"):
            qs = qs.filter(modelo__icontains=datos["modelo"])
        return self.filtrar_fechas(qs, "fecha")


class FiltroAccesoForm(FiltroFechasForm):
    q = forms.CharField(label="Buscar", required=False, widget=forms.TextInput(
        attrs={"placeholder": "Correo o IP"}))
    evento = forms.ChoiceField(required=False, choices=[("", "Todos los eventos"), *RegistroAcceso.Evento.choices])
    field_order = ["q", "evento", "desde", "hasta"]

    def filtrar(self, qs):
        datos = self.cleaned_data
        qs = buscar_texto(qs, datos.get("q"), ["email_intentado", "usuario__email", "ip"])
        if datos.get("evento"):
            qs = qs.filter(evento=datos["evento"])
        return self.filtrar_fechas(qs, "fecha")