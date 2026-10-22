from django.urls import path

from . import views

urlpatterns = [
    path("", views.configuracion, name="configuracion"),
    path("usuarios/nuevo/", views.usuario_nuevo, name="usuario_nuevo"),
    path("usuarios/<int:pk>/editar/", views.usuario_editar, name="usuario_editar"),
]