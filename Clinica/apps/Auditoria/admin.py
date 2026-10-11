"""Ubicación: apps/Auditoria/admin.py  (todo de solo lectura)"""
from django.contrib import admin

from apps.usuarios.admin_mixins import SoloLecturaAdmin

from .models import RegistroAcceso, RegistroAuditoria


@admin.register(RegistroAuditoria)
class RegistroAuditoriaAdmin(SoloLecturaAdmin, admin.ModelAdmin):
    list_display = ("fecha", "usuario", "accion", "modelo", "objeto_id", "descripcion", "ip")
    list_filter = ("accion", "modelo", "fecha")
    search_fields = ("usuario__email", "modelo", "objeto_id", "descripcion", "ip")
    date_hierarchy = "fecha"
    list_select_related = ("usuario",)


@admin.register(RegistroAcceso)
class RegistroAccesoAdmin(SoloLecturaAdmin, admin.ModelAdmin):
    list_display = ("fecha", "evento", "usuario", "email_intentado", "ip")
    list_filter = ("evento", "fecha")
    search_fields = ("email_intentado", "usuario__email", "ip")
    date_hierarchy = "fecha"
    list_select_related = ("usuario",)