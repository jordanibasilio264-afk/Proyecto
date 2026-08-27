from django.urls import path
from . import views

urlpatterns = [ path("",views.citas,name="citas"),]