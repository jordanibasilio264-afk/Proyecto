from django.urls import path
from . import views

urlpatterns = [
    path("", views.lista_expedientes, name="expedientes"),
    path("crear/", views.crear_expediente, name="crear_expediente"),
    path("<int:pk>/", views.detalle_expediente, name="detalle_expediente"),
    path("<int:pk>/editar/", views.editar_expediente, name="editar_expediente"),
    path("<int:pk>/documentos/", views.adjuntar_documento, name="adjuntar_documento"),
    path("<int:pk>/pdf/", views.descargar_expediente_pdf, name="descargar_expediente_pdf"),
]