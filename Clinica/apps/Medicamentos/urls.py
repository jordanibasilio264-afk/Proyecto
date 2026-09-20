from django.urls import path

from . import views


urlpatterns = [

    path(
        '',
        views.medicamentos_view,
        name='medicamentos'
    ),

]