"""Ubicación: apps/Inicio/urls.py
En el urls.py del proyecto:  path("", include("apps.Inicio.urls")),

En settings.py:
    LOGIN_URL = "login"
    LOGIN_REDIRECT_URL = "inicio"    # cámbialo a "dashboard" cuando lo tengas
    LOGOUT_REDIRECT_URL = "inicio"
"""
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("login/", views.IniciarSesion.as_view(), name="login"),
    path("registro/", views.registro, name="registro"),
    path("logout/", LogoutView.as_view(), name="logout"),

    # Recuperar contraseña por correo
    path("password-reset/",
         auth_views.PasswordResetView.as_view(
             template_name="password_reset.html",
             email_template_name="password_reset_email.txt",
             subject_template_name="password_reset_subject.txt",
         ),
         name="password_reset"),
    path("password-reset/enviado/",
         auth_views.PasswordResetDoneView.as_view(
             template_name="password_reset_done.html"),
         name="password_reset_done"),
    path("password-reset/<uidb64>/<token>/",
         auth_views.PasswordResetConfirmView.as_view(
             template_name="password_reset_confirm.html"),
         name="password_reset_confirm"),
    path("password-reset/completado/",
         auth_views.PasswordResetCompleteView.as_view(
             template_name="password_reset_complete.html"),
         name="password_reset_complete"),
]