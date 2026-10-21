from django.urls import path
from . import views

urlpatterns = [
    path("", views.recetas, name="recetas"),
    path("nueva/", views.crear_receta, name="crear_receta"),
    path("buscar-consultas/", views.buscar_consultas, name="buscar_consultas"),
    path("<int:receta_id>/editar/", views.editar_receta, name="editar_receta"),
    path("<int:receta_id>/imprimir/", views.imprimir_receta,name="imprimir_receta"),
    path("<int:receta_id>/", views.detalle_receta, name="detalle_receta"),
]