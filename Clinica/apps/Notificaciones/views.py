from django.shortcuts import render


def notificaciones(request):

    #recordatorios = 12
    #alertas = 3
    #cancelaciones = 2
    #total = 17

    #datos = {
        #"recordatorios": recordatorios,
        #"alertas": alertas,
        #"cancelaciones": cancelaciones,
        #"total": total,
    #}

    return render(request,"notificaciones.html")