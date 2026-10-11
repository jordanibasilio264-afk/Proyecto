"""Ubicación: apps/Expedientes/admin.py"""
from django.contrib import admin

from apps.usuarios.admin_mixins import SinEliminarAdmin

from .models import Consulta, Expediente


class ConsultaInline(admin.TabularInline):
    """Historial de consultas dentro del expediente (solo lectura)."""

    model = Consulta
    extra = 0
    can_delete = False
    show_change_link = True
    fields = ("fecha", "medico", "motivo_consulta", "diagnostico")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Expediente)
class ExpedienteAdmin(SinEliminarAdmin, admin.ModelAdmin):
    list_display = ("numero", "paciente", "fecha_apertura", "activo")
    list_filter = ("activo", "fecha_apertura")
    search_fields = ("numero", "paciente__nombres", "paciente__apellidos", "paciente__cedula")
    autocomplete_fields = ("paciente",)
    readonly_fields = ("numero", "creado_en", "actualizado_en")
    list_select_related = ("paciente",)
    inlines = [ConsultaInline]


@admin.register(Consulta)
class ConsultaAdmin(SinEliminarAdmin, admin.ModelAdmin):
    list_display = ("fecha", "expediente", "medico", "motivo_consulta", "requiere_seguimiento")
    list_filter = ("medico", "requiere_seguimiento", "fecha")
    search_fields = (
        "expediente__numero", "expediente__paciente__nombres",
        "expediente__paciente__apellidos", "diagnostico", "codigo_cie10", "motivo_consulta",
    )
    date_hierarchy = "fecha"
    autocomplete_fields = ("expediente", "medico", "cita")
    readonly_fields = ("imc", "creado_en", "actualizado_en")
    list_select_related = ("expediente__paciente", "medico__usuario")
    fieldsets = (
        ("Consulta", {"fields": ("expediente", "cita", "medico", "fecha", "motivo_consulta", "enfermedad_actual")}),
        ("Signos vitales", {"fields": (
            ("presion_sistolica", "presion_diastolica"),
            ("frecuencia_cardiaca", "frecuencia_respiratoria"),
            ("temperatura", "saturacion_oxigeno"),
            ("peso_kg", "talla_cm", "imc"),
        )}),
        ("Diagnóstico y tratamiento", {"fields": (
            "diagnostico", "codigo_cie10", "tratamiento", "observaciones")}),
        ("Seguimiento", {"fields": ("requiere_seguimiento", "fecha_seguimiento")}),
        ("Registro", {"fields": ("creado_en", "actualizado_en")}),
    )

    @admin.display(description="IMC")
    def imc(self, obj):
        return obj.imc if obj and obj.pk else "-"