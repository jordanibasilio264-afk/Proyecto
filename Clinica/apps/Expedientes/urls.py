from django.urls import path
from . import views

urlpatterns = [ 
path("", views.expedientes, name="expedientes"),
path("crear/", views.crear_expediente, name="crear_expediente"),]
