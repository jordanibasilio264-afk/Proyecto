from django.urls import path
from . import views

urlpatterns = [ path("",views.expedientes,name="expedientes"),]
