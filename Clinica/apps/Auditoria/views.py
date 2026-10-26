from functools import wraps

from django.contrib.auth import get_user_model
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.shortcuts import render
from django.utils import timezone

from .forms import FiltroAccesoForm, FiltroAuditoriaForm
from .models import RegistroAcceso, RegistroAuditoria

POR_PAGINA_ACTIVIDADES = 15
POR_PAGINA_ACCESOS = 10


def rol_requerido(*roles):
    def decorador(vista):
        @wraps(vista)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if request.user.rol not in roles:   # ajusta a como guardas el rol
                raise PermissionDenied
            return vista(request, *args, **kwargs)
        return wrapper
    return decorador


def _filtrar(form, qs):
    return form.filtrar(qs) if form.is_valid() else qs


def _paginar(request, qs, param, por_pagina):
    """Devuelve (página, querystring sin el parámetro de esa página)."""
    paginator = Paginator(qs, por_pagina)
    pagina = paginator.get_page(request.GET.get(param))
    pagina.rango = list(paginator.get_elided_page_range(
        pagina.number, on_each_side=1, on_ends=1))
    params = request.GET.copy()
    params.pop(param, None)
    return pagina, params.urlencode()


@rol_requerido("ADMIN", "RECEPCIONISTA", "MEDICO")
def auditoria(request):
    datos = request.GET or None            # sin filtros -> formulario sin enlazar
    form = FiltroAuditoriaForm(datos)
    registros_qs = _filtrar(form, RegistroAuditoria.objects.select_related("usuario"))
    accesos_qs = _filtrar(FiltroAccesoForm(datos), RegistroAcceso.objects.select_related("usuario"))

    registros, qs_act = _paginar(
        request, registros_qs.order_by("-fecha", "-id"), "pag_act", POR_PAGINA_ACTIVIDADES)
    accesos, qs_acc = _paginar(
        request, accesos_qs.order_by("-fecha", "-id"), "pag_acc", POR_PAGINA_ACCESOS)

    hoy = timezone.localdate()
    Evento = RegistroAcceso.Evento
    accesos_hoy = RegistroAcceso.objects.filter(fecha__date=hoy)

    return render(request, "auditoria.html", {
        "form": form,
        "acciones_hoy": RegistroAuditoria.objects.filter(fecha__date=hoy).count(),
        "accesos_hoy": accesos_hoy.filter(evento=Evento.LOGIN).count(),
        "accesos_fallidos": accesos_hoy.filter(evento=Evento.LOGIN_FALLIDO).count(),
        "usuarios_activos": get_user_model().objects.filter(is_active=True).count(),
        "total_registros": registros.paginator.count,
        "total_accesos": accesos.paginator.count,
        "registros": registros,
        "accesos": accesos,
        "qs_act": qs_act,
        "qs_acc": qs_acc,
    })
