"""Ubicación: apps/Citas/admin.py"""
from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from .models import Cita


@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = ("inicio", "paciente", "medico", "estado", "duracion_minutos")
    list_filter = ("estado", "medico", "inicio")
    search_fields = (
        "paciente__nombres", "paciente__apellidos", "paciente__cedula",
        "medico__usuario__first_name", "medico__usuario__last_name", "motivo",
    )
    date_hierarchy = "inicio"
    autocomplete_fields = ("paciente", "medico", "reprogramada_desde")
    readonly_fields = ("fin", "creada_por", "creado_en", "actualizado_en")
    list_select_related = ("paciente", "medico__usuario")
    actions = ["confirmar_citas", "marcar_atendidas", "cancelar_citas"]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.creada_por = request.user
        super().save_model(request, obj, form, change)

    def _aplicar(self, request, queryset, metodo, exito, **kwargs):
        ok = 0
        for cita in queryset:
            try:
                getattr(cita, metodo)(**kwargs)
                ok += 1
            except ValidationError as e:
                self.message_user(request, f"{cita}: {'; '.join(e.messages)}", messages.ERROR)
        if ok:
            self.message_user(request, f"{ok} cita(s) {exito}.", messages.SUCCESS)

    @admin.action(description="Confirmar citas seleccionadas")
    def confirmar_citas(self, request, queryset):
        self._aplicar(request, queryset, "confirmar", "confirmada(s)")

    @admin.action(description="Marcar como atendidas")
    def marcar_atendidas(self, request, queryset):
        self._aplicar(request, queryset, "marcar_atendida", "marcada(s) como atendida(s)")

    @admin.action(description="Cancelar citas seleccionadas")
    def cancelar_citas(self, request, queryset):
        self._aplicar(
            request, queryset, "cancelar", "cancelada(s)",
            motivo="Cancelada desde el administrador",
        )