from django.urls import path
from . import views

urlpatterns = [
    path("", views.reportes, name="reportes"),
    path("exportar/<str:tipo>/<str:formato>/", views.generar, name="reportes_generar"),
]