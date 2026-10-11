"""Ubicación: apps/Reportes/admin.py"""
from django.contrib import admin

from .models import ReporteGenerado


@admin.register(ReporteGenerado)
class ReporteGeneradoAdmin(admin.ModelAdmin):
    list_display = ("tipo", "formato", "generado_por", "creado_en")
    list_filter = ("tipo", "formato", "creado_en")
    search_fields = ("generado_por__email",)
    date_hierarchy = "creado_en"
    list_select_related = ("generado_por",)

    # Los genera el sistema; aquí solo se consultan y se pueden limpiar.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False