"""Ubicación: apps/Inicio/urls.py
En el urls.py del proyecto:  path("", include("apps.Inicio.urls")),

En settings.py:
    LOGIN_URL = "login"
    LOGIN_REDIRECT_URL = "inicio"    # cámbialo a "dashboard" cuando lo tengas
    LOGOUT_REDIRECT_URL = "inicio"
"""
from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("login/", views.IniciarSesion.as_view(), name="login"),
    path("registro/", views.registro, name="registro"),
    path("logout/", LogoutView.as_view(), name="logout"),  
]