"""Ubicación: apps/Documentos/admin.py"""
from django.contrib import admin

from apps.usuarios.admin_mixins import SinEliminarAdmin

from .models import Documento


@admin.register(Documento)
class DocumentoAdmin(SinEliminarAdmin, admin.ModelAdmin):
    list_display = ("titulo", "paciente", "tipo", "tamano", "subido_por", "activo", "creado_en")
    list_filter = ("tipo", "activo", "creado_en")
    search_fields = ("titulo", "paciente__nombres", "paciente__apellidos", "descripcion")
    autocomplete_fields = ("paciente", "consulta")
    readonly_fields = ("tamano_bytes", "subido_por", "creado_en", "actualizado_en")
    list_select_related = ("paciente", "subido_por")
    actions = ["desactivar", "activar"]

    @admin.display(description="Tamaño")
    def tamano(self, obj):
        return f"{obj.tamano_bytes / 1024 / 1024:.2f} MB"

    def save_model(self, request, obj, form, change):
        if not change:
            obj.subido_por = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description="Desactivar (eliminar) documentos seleccionados")
    def desactivar(self, request, queryset):
        n = queryset.update(activo=False)
        self.message_user(request, f"{n} documento(s) desactivado(s).")

    @admin.action(description="Reactivar documentos seleccionados")
    def activar(self, request, queryset):
        n = queryset.update(activo=True)
        self.message_user(request, f"{n} documento(s) reactivado(s).")