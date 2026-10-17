"""Ubicación: apps/Documentos/urls.py
En el urls.py del proyecto: path("documentos/", include("apps.Documentos.urls"))"""
from django.urls import path

from . import views

urlpatterns = [
    path("", views.documentos_page, name="documentos"),
    path("api/pacientes/<int:paciente_id>/consultas/", views.consultas_api, name="api_consultas"),
    path("api/pacientes/<int:paciente_id>/documentos/", views.documentos_api, name="api_documentos"),
    path("api/documentos/<int:pk>/desactivar/", views.documento_desactivar, name="api_doc_desactivar"),
    path("archivo/<int:pk>/", views.documento_descargar, name="documento_descargar"),
]