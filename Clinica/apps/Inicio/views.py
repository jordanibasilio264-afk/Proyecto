from django.shortcuts import render


def inicio(request):
    return render(request, "inicio.html")


def login(request):
    return render(request, "login.html")


def registro(request):
    return render(request, "registro.html")