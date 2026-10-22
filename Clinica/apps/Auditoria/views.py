from functools import wraps

from django.contrib.auth import get_user_model
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.utils import timezone

from .forms import FiltroAccesoForm, FiltroAuditoriaForm
from .models import RegistroAcceso, RegistroAuditoria

LIMITE = 100  # filas máximas por tabla


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


@rol_requerido("ADMIN", "RECEPCIONISTA", "MEDICO")
def auditoria(request):
    datos = request.GET or None            # sin filtros -> formulario sin enlazar
    form = FiltroAuditoriaForm(datos)
    registros = _filtrar(form, RegistroAuditoria.objects.select_related("usuario"))
    accesos = _filtrar(FiltroAccesoForm(datos), RegistroAcceso.objects.select_related("usuario"))

    hoy = timezone.localdate()
    Evento = RegistroAcceso.Evento
    accesos_hoy = RegistroAcceso.objects.filter(fecha__date=hoy)

    return render(request, "auditoria.html", {
        "form": form,
        "acciones_hoy": RegistroAuditoria.objects.filter(fecha__date=hoy).count(),
        "accesos_hoy": accesos_hoy.filter(evento=Evento.LOGIN).count(),
        "accesos_fallidos": accesos_hoy.filter(evento=Evento.LOGIN_FALLIDO).count(),
        "usuarios_activos": get_user_model().objects.filter(is_active=True).count(),
        "total_registros": registros.count(),
        "total_accesos": accesos.count(),
        "registros": registros[:LIMITE],
        "accesos": accesos[:LIMITE],
    })
