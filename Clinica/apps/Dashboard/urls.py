from django.urls import path
from . import views

urlpatterns = [ path("",views.dashboard,name="dashboard"),
               path("mi-panel/", views.mi_dashboard, name="mi_dashboard"),
]