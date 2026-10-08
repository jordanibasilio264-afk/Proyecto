from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuarios

@admin.register(Usuarios)
class UsuarioAdmin(UserAdmin):
    list_display = ("email", "username", "rol", "is_staff", "is_active")
    list_editable = ("rol",)
    list_filter = ("rol", "is_staff", "is_active")

    fieldsets = UserAdmin.fieldsets + (("Rol del usuario", {"fields": ("rol",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Rol del usuario", {"fields": ("rol",)}),
    )