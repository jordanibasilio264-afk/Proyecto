"""Ubicación: apps/SegurosMedicos/admin.py"""
from django.contrib import admin

from .models import SeguroMedico, SeguroPaciente


@admin.register(SeguroMedico)
class SeguroMedicoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "rnc", "telefono", "porcentaje_cobertura", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre", "rnc")


@admin.register(SeguroPaciente)
class SeguroPacienteAdmin(admin.ModelAdmin):
    list_display = ("paciente", "seguro", "numero_afiliado", "es_principal", "vigente_ahora", "activo")
    list_filter = ("seguro", "es_principal", "activo")
    search_fields = ("paciente__nombres", "paciente__apellidos", "numero_afiliado", "seguro__nombre")
    autocomplete_fields = ("paciente", "seguro")
    list_select_related = ("paciente", "seguro")

    @admin.display(boolean=True, description="Vigente")
    def vigente_ahora(self, obj):
        return obj.vigente