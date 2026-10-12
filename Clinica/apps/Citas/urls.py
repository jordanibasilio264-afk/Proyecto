"""Ubicación: apps/Citas/urls.py
En el urls.py del proyecto:  path("", include("apps.Citas.urls")),"""
from django.urls import path

from . import views

urlpatterns = [
    path("citas/", views.citas, name="citas"),  # lista + crear (modal)
    path("citas/<int:pk>/editar/", views.editar_cita, name="cita_editar"),
    path("citas/<int:pk>/cancelar/", views.cancelar_cita, name="cita_cancelar"),
    path("citas/<int:pk>/reprogramar/", views.reprogramar_cita, name="cita_reprogramar"),
    path("citas/<int:pk>/confirmar/", views.confirmar_cita, name="cita_confirmar"),
]