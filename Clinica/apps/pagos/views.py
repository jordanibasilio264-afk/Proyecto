"""Ubicación: apps/pagos/views.py"""
from functools import wraps

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import FiltroPagoForm, PagoForm
from .models import Pago


def rol_requerido(*roles):
    def decorador(vista):
        @wraps(vista)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())
            if request.user.rol not in roles:   # ajusta a como guardas el rol
                raise PermissionDenied
            return vista(request, *args, **kwargs)
        return wrapper
    return decorador


# Solo estos roles pueden registrar pagos
ROLES_COBRO = ("ADMIN", "RECEPCIONISTA")


@rol_requerido("ADMIN", "RECEPCIONISTA", "MEDICO", "PACIENTE")
def pagos(request):
    puede_cobrar = request.user.rol in ROLES_COBRO

    # ---- Registrar pago ----
    form = None
    if puede_cobrar:
        if request.method == "POST":
            form = PagoForm(request.POST, usuario=request.user)
            if form.is_valid():
                pago = form.save()
                messages.success(request, f"Pago registrado: {pago.numero_recibo}")
                return redirect("pagos")
        else:
            form = PagoForm(usuario=request.user)
    elif request.method == "POST":
        raise PermissionDenied

    # ---- Consulta base ----
    base = Pago.objects.select_related("paciente", "cita")
    if request.user.rol == "PACIENTE":
        # AJUSTA: el campo que une al usuario con su Paciente
        base = base.filter(paciente__usuario=request.user)

    # ---- Filtros (buscar, estado, método, desde, hasta) ----
    filtro = FiltroPagoForm(request.GET or None)
    qs = base
    if filtro.is_valid():
        qs = filtro.filtrar(base)

    # ---- Tarjetas de resumen ----
    ingresos = qs.filter(estado=Pago.Estado.PAGADO).aggregate(t=Sum("monto"))["t"] or 0

    # ---- Paginación (10 por página) ----
    page_obj = Paginator(qs, 10).get_page(request.GET.get("page"))

    params = request.GET.copy()
    params.pop("page", None)

    contexto = {
        "form": form,
        "filtro": filtro,
        "page_obj": page_obj,
        "querystring": params.urlencode(),   # para los enlaces de página
        "puede_cobrar": puede_cobrar,
        "total_pagos": qs.count(),
        "pagos_hoy": base.filter(fecha_pago__date=timezone.localdate()).count(),
        "ingresos": f"RD${ingresos:,.2f}",
        "pendientes": qs.filter(estado=Pago.Estado.PENDIENTE).count(),
    }
    return render(request, "pagos.html", contexto)
