from django.urls import path

from . import views

urlpatterns = [
    path('', views.configuracion, name='configuracion'),
    path('<str:rol>/', views.configuracion, name='configuracion_rol'),
]