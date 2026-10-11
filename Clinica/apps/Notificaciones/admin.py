"""Ubicación: apps/Notificaciones/admin.py"""
from django.contrib import admin

from .models import Notificacion


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ("titulo", "tipo", "canal", "destinatario", "estado", "programada_para", "leida")
    list_filter = ("tipo", "canal", "estado", "leida")
    search_fields = (
        "titulo", "mensaje", "usuario__email",
        "paciente__nombres", "paciente__apellidos",
    )
    date_hierarchy = "programada_para"
    autocomplete_fields = ("usuario", "paciente", "cita")
    readonly_fields = ("enviada_en", "leida_en", "creado_en", "actualizado_en")
    list_select_related = ("usuario", "paciente")
    actions = ["marcar_leidas", "reintentar_envio"]

    @admin.display(description="Destinatario")
    def destinatario(self, obj):
        return obj.paciente or obj.usuario

    @admin.action(description="Marcar como leídas")
    def marcar_leidas(self, request, queryset):
        for n in queryset.filter(leida=False):
            n.marcar_leida()

    @admin.action(description="Reintentar envío (volver a pendiente)")
    def reintentar_envio(self, request, queryset):
        n = queryset.filter(estado=Notificacion.Estado.FALLIDA).update(
            estado=Notificacion.Estado.PENDIENTE, error=""
        )
        self.message_user(request, f"{n} notificación(es) en cola de nuevo.")