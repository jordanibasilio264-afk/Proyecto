"""Ubicación: apps/Configuracion/admin.py"""
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse

from .models import ConfiguracionConsultorio


@admin.register(ConfiguracionConsultorio)
class ConfiguracionAdmin(admin.ModelAdmin):
    readonly_fields = ("creado_en", "actualizado_en")
    fieldsets = (
        ("Datos del consultorio", {"fields": (
            "nombre_consultorio", "rnc", "telefono", "email", "direccion", "logo", "moneda")}),
        ("Agenda", {"fields": ("hora_apertura", "hora_cierre", "duracion_cita_defecto")}),
        ("Notificaciones e inteligencia", {"fields": (
            "recordatorio_horas_antes", "paciente_frecuente_min_citas", "dias_alerta_seguimiento")}),
        ("Acceso", {"fields": ("permitir_registro_publico",)}),
        ("Registro", {"fields": ("creado_en", "actualizado_en")}),
    )

    def has_add_permission(self, request):
        return not ConfiguracionConsultorio.objects.exists()  # solo una

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        """Si ya existe, entra directo a editarla."""
        obj = ConfiguracionConsultorio.objects.first()
        if obj:
            opts = self.model._meta
            return redirect(reverse(f"admin:{opts.app_label}_{opts.model_name}_change", args=[obj.pk]))
        return super().changelist_view(request, extra_context)