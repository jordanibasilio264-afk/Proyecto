from django.urls import path
from . import views

app_name = "usuarios"

urlpatterns = [
    path("", views.EspecialidadListView.as_view(), name="especialidad_lista"),
    path("especialidades/nueva/", views.EspecialidadCreateView.as_view(), name="especialidad_create"),
    path("especialidades/<int:pk>/editar/", views.EspecialidadUpdateView.as_view(), name="especialidad_update"),
    path("especialidades/<int:pk>/eliminar/", views.EspecialidadDeleteView.as_view(), name="especialidad_delete"),
]