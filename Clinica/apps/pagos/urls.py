from django.urls import path
from . import views


urlpatterns = [ path("",views.pagos,name="pagos"),
  path("buscar-pacientes/", views.buscar_pacientes, name="buscar_pacientes"),
  path("paciente/<int:pk>/datos/", views.datos_paciente, name="datos_paciente"),
  path("pagos/<int:pk>/marcar-pagado/", views.marcar_pagado, name="marcar_pagado"),
  path("mis-pagos/", views.mis_pagos, name="mis_pagos"),
  ]