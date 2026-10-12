from django.shortcuts import render
from apps.usuarios.decorators import requiere_permiso

@requiere_permiso("reportes.ver")
def reportes(request):

    # Cantidad de información
    #pacientes = 248
    #citas = 156
    #consultas = 189
    #pagos = 124
    #diagnosticos = 215
    #medicos = 32

    # Dinero
    #ingresos = "RD$24,850.00"

    # Enviar los datos al HTML
    #datos = {
    #     "pacientes": pacientes,
    #     "citas": citas,
    #     "consultas": consultas,
    #     "pagos": pagos,
    #     "diagnosticos": diagnosticos,
    #     "medicos": medicos,
    #     "ingresos": ingresos,
    # }

    return render(request,"reportes.html")