"""
Ubicación: apps/usuarios/admin.py
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Especialidad, HorarioMedico, Medico, Paciente, Usuarios


@admin.register(Usuarios)
class UsuariosAdmin(UserAdmin):
    model = Usuarios

    # Todo lo que usaba 'username' se reemplaza por 'email'
    ordering = ("email",)
    list_display = ("email", "first_name", "last_name", "cedula", "rol", "is_active")
    list_filter = ("rol", "is_active", "is_staff")
    search_fields = ("email", "first_name", "last_name","cedula")
    filter_horizontal = ()  # sin widget de grupos/permisos

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Información personal", {"fields": ("first_name", "last_name", "cedula", "telefono")}),
        ("Rol y estado", {"fields": ("rol", "is_active", "is_staff", "is_superuser")}),
        ("Fechas importantes", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "first_name", "last_name", "cedula", "telefono",
                       "rol", "password1", "password2"),
        }),
    )


@admin.register(Especialidad)
class EspecialidadAdmin(admin.ModelAdmin):
    list_display = ("nombre", "descripcion", "activa")
    list_filter = ("activa",)
    search_fields = ("nombre",)


class HorarioMedicoInline(admin.TabularInline):
    model = HorarioMedico
    extra = 1
    fields = ("dia_semana", "hora_inicio", "hora_fin", "activo")


@admin.register(Medico)
class MedicoAdmin(admin.ModelAdmin):
    list_display = ("__str__", "exequatur", "especialidades_lista", "consultorio", "activo")
    list_filter = ("activo", "especialidades")
    search_fields = (
        "usuario__first_name", "usuario__last_name", "usuario__email",
        "exequatur", "cedula",
    )
    autocomplete_fields = ("usuario",)
    filter_horizontal = ("especialidades",)
    list_select_related = ("usuario",)
    inlines = [HorarioMedicoInline]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("especialidades")

    @admin.display(description="Especialidades")
    def especialidades_lista(self, obj):
        return ", ".join(e.nombre for e in obj.especialidades.all()) or "-"


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ("nombre_completo", "cedula", "telefono", "edad_display", "sexo", "activo")
    list_filter = ("activo", "sexo", "tipo_sangre")
    search_fields = ("nombres", "apellidos", "cedula", "telefono", "email")
    autocomplete_fields = ("usuario",)
    fieldsets = (
        ("Datos personales", {"fields": (
            "nombres", "apellidos", "cedula", "fecha_nacimiento", "sexo", "tipo_sangre")}),
        ("Contacto", {"fields": ("telefono", "email", "direccion")}),
        ("Contacto de emergencia", {"fields": (
            "contacto_emergencia_nombre", "contacto_emergencia_telefono")}),
        ("Cuenta y estado", {"fields": ("usuario", "activo")}),
    )

    @admin.display(description="Edad")
    def edad_display(self, obj):
        return obj.edad