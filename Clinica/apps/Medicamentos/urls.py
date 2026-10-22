from django.urls import path
from . import views

urlpatterns = [
    path("", views.medicamentos_view, name="medicamentos"),
    path("nuevo/", views.crear_medicamento, name="crear_medicamento"),
    path(
        "<int:medicamento_id>/editar/",
        views.editar_medicamento,
        name="editar_medicamento",
    ),
    path(
        "<int:medicamento_id>/estado/",
        views.cambiar_estado_medicamento,
        name="cambiar_estado_medicamento",
    ),
    path(
        "<int:medicamento_id>/eliminar/",
        views.eliminar_medicamento,
        name="eliminar_medicamento",
    ),
]
