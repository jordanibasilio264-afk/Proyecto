from django.urls import path
from . import views


urlpatterns = [
    path("", views.gestion, name="seguros"),
    path("guardar/", views.guardar, name="guardar_seguro"),
    path("eliminar/<int:id>/", views.eliminar, name="eliminar_seguro"),
]