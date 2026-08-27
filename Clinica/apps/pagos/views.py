from django.shortcuts import render


def pagos(request):

    # #total_pagos = 124
    # pagos_hoy = 8
    # ingresos = "RD$24,850.00"
    # pendientes = 5

    # datos = {
    #     "total_pagos": total_pagos,
    #     "pagos_hoy": pagos_hoy,
    #     "ingresos": ingresos,
    #     "pendientes": pendientes,
    # }

    return render(request,"pagos.html",)
