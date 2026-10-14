"""Ubicación: apps/Inicio/views.py"""
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render

from .forms import LoginForm, RegistroForm


def inicio(request):
    return render(request, "inicio.html")


def registro(request):
    if request.user.is_authenticated:
        return redirect("inicio")
    form = RegistroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = form.save()
        login(request, usuario)
        messages.success(request, "Cuenta creada correctamente.")
        return redirect("pagos")
    return render(request, "registro.html", {"form": form})


class IniciarSesion(LoginView):
    template_name = "login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True