from functools import wraps
from django.core.exceptions import PermissionDenied
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from django.utils import timezone
from apps.Expedientes.models import Consulta
from apps.Citas.models import Cita
from apps.pagos.models import Pago
from apps.usuarios.models import Paciente
from django.shortcuts import get_object_or_404, redirect, render
from apps.Documentos.models import Documento
from django.db.models import Q


def rol_requerido(*roles):
    def decorador(vista):
        @wraps(vista)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())
            if request.user.rol not in roles:    # ajusta a como guardas el rol
                raise PermissionDenied
            return vista(request, *args, **kwargs)
        return wrapper
    return decorador


@rol_requerido("ADMIN", "RECEPCIONISTA", "MEDICO","PACIENTE")
def dashboard(request):
    return render(request,"dashboard.html")

MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
         "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def ultimos_meses(n=6):
    """Lista de (año, mes) de los últimos n meses, del más antiguo al actual."""
    hoy = timezone.localdate()
    y, m = hoy.year, hoy.month
    out = []
    for _ in range(n):
        out.append((y, m))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return out[::-1]


@rol_requerido("ADMIN", "RECEPCIONISTA", "MEDICO","PACIENTE")
def dashboard(request):
    if request.user.rol == "PACIENTE":
        return redirect("mi_dashboard")
    hoy = timezone.localdate()
    E = Cita.Estado


    # AJUSTA: los valores de estado y el nombre del campo de fecha ("fecha")
    # según tu modelo Cita.
    citas = Cita.objects.all()
    atendidas = citas.filter(estado=E.ATENDIDA)      # AJUSTA
    canceladas = citas.filter(estado=E.CANCELADA)
    pendientes = citas.filter(estado__in=[E.PROGRAMADA, E.CONFIRMADA])
    no_asistio = citas.filter(estado=E.NO_ASISTIO) # AJUSTA

    total_citas = citas.count()
    n_atendidas = atendidas.count()
    tasa = round(n_atendidas * 100 / total_citas) if total_citas else 0

    ingresos = (Pago.objects.filter(estado=Pago.Estado.PAGADO,
                                    fecha_pago__year=hoy.year,
                                    fecha_pago__month=hoy.month)
                .aggregate(t=Sum("monto"))["t"] or 0)

    # --- Gráfico de barras: consultas atendidas por mes (últimos 6) ---
    consultas = Consulta.objects.all()
    meses = ultimos_meses(6)
    por_mes = (consultas
           .annotate(mes=TruncMonth("creado_en"))
           .values("mes").order_by()
           .annotate(n=Count("pk")))
    conteo = {(r["mes"].year, r["mes"].month): r["n"] for r in por_mes if r["mes"]}

    chart_data = {
        "meses": [MESES[m - 1] for _, m in meses],
        "consultas": [conteo.get(k, 0) for k in meses],
        "estados": {
            "etiquetas": ["Programadas", "Atendidas", "Canceladas","No asistió"],
            "valores": [pendientes.count(), n_atendidas,canceladas.count(), no_asistio.count()],
        },
    }

    return render(request, "dashboard.html", {
        "total_pacientes": Paciente.objects.filter(activo=True).count(),
        "citas_programadas": pendientes.filter(inicio__date=hoy).count(), # las de hoy
        "citas_atendidas": n_atendidas,
        "citas_canceladas": canceladas.count(),
        "consultas_realizadas": consultas.count(),
        "ingresos_generados": f"{ingresos:,.2f}",
        "tasa_atencion": tasa,
        "chart_data": chart_data,
    })


@rol_requerido("PACIENTE")
def mi_dashboard(request):
    # Mismo vínculo que ya usas en mis_pagos: paciente__usuario
    paciente = get_object_or_404(Paciente, usuario=request.user)
    ahora = timezone.now()
    E = Cita.Estado

    citas = Cita.objects.filter(paciente=paciente).select_related("medico")
    proximas = (citas.filter(estado__in=[E.PROGRAMADA, E.CONFIRMADA], inicio__gte=ahora)
                .order_by("inicio"))

    consultas = Consulta.objects.filter(
    Q(cita__paciente=paciente) | Q(expediente__paciente=paciente)
    ).distinct()
    documentos = Documento.objects.filter(paciente=paciente, activo=True)
    pagos = Pago.objects.filter(paciente=paciente).select_related("cita")

    def suma(estado):
        t = pagos.filter(estado=estado).aggregate(t=Sum("monto"))["t"] or 0
        return f"RD${t:,.2f}"

    return render(request, "mi_dashboard.html", {
        "paciente": paciente,
        "proxima_cita": proximas.first(),
        "citas_pendientes": proximas.count(),
        "total_consultas": consultas.count(),
        "total_documentos": documentos.count(),
        "total_pagado": suma(Pago.Estado.PAGADO),
        "total_pendiente": suma(Pago.Estado.PENDIENTE),
        "lista_citas": proximas[:5],
        "lista_consultas": consultas.order_by("-creado_en")[:5],
        "lista_pagos": pagos.exclude(estado=Pago.Estado.ANULADO)[:5],
        "lista_documentos": documentos[:5],
    })