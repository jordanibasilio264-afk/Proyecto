"""Ubicación: apps/Medicamentos/admin.py"""
from django.contrib import admin

from apps.usuarios.admin_mixins import SinEliminarAdmin

from .models import DetalleReceta, Medicamento, Receta


@admin.register(Medicamento)
class MedicamentoAdmin(admin.ModelAdmin):
    list_display = ("nombre_comercial", "nombre_generico", "concentracion", "forma", "laboratorio", "activo")
    list_filter = ("forma", "activo")
    search_fields = ("nombre_comercial", "nombre_generico", "laboratorio")


class DetalleRecetaInline(admin.TabularInline):
    model = DetalleReceta
    extra = 1
    autocomplete_fields = ("medicamento",)
    fields = ("medicamento", "dosis", "frecuencia", "duracion_dias", "via_administracion", "cantidad", "instrucciones")


@admin.register(Receta)
class RecetaAdmin(SinEliminarAdmin, admin.ModelAdmin):
    list_display = ("numero", "paciente", "medico", "fecha", "vigente_hasta")
    list_filter = ("fecha",)
    search_fields = (
        "numero", "consulta__expediente__paciente__nombres",
        "consulta__expediente__paciente__apellidos",
    )
    date_hierarchy = "fecha"
    autocomplete_fields = ("consulta",)
    readonly_fields = ("numero", "creado_en", "actualizado_en")
    list_select_related = ("consulta__expediente__paciente", "consulta__medico__usuario")
    inlines = [DetalleRecetaInline]