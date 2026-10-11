"""Ubicación: apps/pagos/admin.py"""
from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from apps.usuarios.admin_mixins import SinEliminarAdmin

from .models import Pago


@admin.register(Pago)
class PagoAdmin(SinEliminarAdmin, admin.ModelAdmin):
    list_display = (
        "numero_recibo", "paciente", "concepto", "monto",
        "monto_cubierto_seguro", "metodo", "estado", "fecha_pago",
    )
    list_filter = ("estado", "metodo", "fecha_pago")
    search_fields = (
        "numero_recibo", "paciente__nombres", "paciente__apellidos",
        "concepto", "referencia",
    )
    date_hierarchy = "fecha_pago"
    autocomplete_fields = ("paciente", "cita", "seguro_paciente")
    readonly_fields = ("numero_recibo", "recibido_por", "creado_en", "actualizado_en")
    list_select_related = ("paciente",)
    actions = ["anular_pagos"]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.recibido_por = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description="Anular pagos seleccionados")
    def anular_pagos(self, request, queryset):
        ok = 0
        for pago in queryset.exclude(estado=Pago.Estado.ANULADO):
            try:
                pago.anular("Anulado desde el administrador")
                ok += 1
            except ValidationError as e:
                self.message_user(request, f"{pago}: {'; '.join(e.messages)}", messages.ERROR)
        if ok:
            self.message_user(request, f"{ok} pago(s) anulado(s).", messages.SUCCESS)