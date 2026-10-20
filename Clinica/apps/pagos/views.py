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
from django.http import JsonResponse
from apps.Citas.models import Cita
from apps.SegurosMedicos.models import SeguroPaciente
from apps.usuarios.forms_base import buscar_texto
from apps.usuarios.models import Paciente
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError
from django.utils.http import url_has_allowed_host_and_scheme
from django.db.models import F, Sum


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

@rol_requerido(*ROLES_COBRO)
def buscar_pacientes(request):
    q = (request.GET.get("q") or "").strip()
    if len(q) < 2:
        return JsonResponse({"resultados": []})
    qs = buscar_texto(Paciente.objects.filter(activo=True), q, ["nombres", "apellidos"])[:10]
    return JsonResponse({"resultados": [{"id": p.pk, "texto": str(p)} for p in qs]})


@rol_requerido(*ROLES_COBRO)
def datos_paciente(request, pk):
    citas = Cita.objects.filter(paciente_id=pk).exclude(estado="CANCELADA")
    seguros = SeguroPaciente.objects.filter(paciente_id=pk, activo=True).select_related("seguro")
    return JsonResponse({
        "citas": [{"id": c.pk, "texto": str(c)} for c in citas],
        "seguros": [{"id": s.pk, "texto": str(s)} for s in seguros],
    })

@rol_requerido(*ROLES_COBRO)
@require_POST
def marcar_pagado(request, pk):
    pago = get_object_or_404(Pago, pk=pk)
    try:
        pago.marcar_pagado()
        messages.success(request, f"Pago {pago.numero_recibo} marcado como pagado.")
    except ValidationError as e:
        messages.error(request, e.messages[0])

    destino = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}):
        destino = "pagos"
    return redirect(destino)

@rol_requerido("PACIENTE")
def mis_pagos(request):
    # AJUSTA: el campo que une al usuario con su Paciente (el mismo que usaste en `pagos`)
    base = Pago.objects.filter(paciente__usuario=request.user).select_related("cita")

    filtro = FiltroPagoForm(request.GET or None)
    qs = base
    if filtro.is_valid():
        qs = filtro.filtrar(base)

    def suma(estado):
        total = qs.filter(estado=estado).aggregate(
            t=Sum(F("monto") - F("monto_cubierto_seguro")))["t"] or 0
        return f"RD${total:,.2f}"

    page_obj = Paginator(qs, 10).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)

    ultimo = qs.filter(estado=Pago.Estado.PAGADO).first()

    return render(request, "mis_pagos.html", {
        "filtro": filtro,
        "page_obj": page_obj,
        "querystring": params.urlencode(),
        "resumen_paginas": f"Página {page_obj.number} de {page_obj.paginator.num_pages} ({page_obj.paginator.count} pagos)",
        "paciente_nombre": request.user.get_full_name() or request.user.get_username(),
        "total_pagado": suma(Pago.Estado.PAGADO),
        "total_pendiente": suma(Pago.Estado.PENDIENTE),
        "cantidad": qs.count(),
        "ultimo_pago": ultimo.fecha_pago.strftime("%d/%m/%Y") if ultimo else "—",
    })

@rol_requerido("ADMIN", "RECEPCIONISTA", "MEDICO","PACIENTE")
def pagos(request):
    if request.user.rol == "PACIENTE":
        return redirect("mis_pagos")
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
