from functools import wraps
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.usuarios.models import Paciente
from .models import Expediente


def rol_requerido(*roles):
    def decorador(vista):
        @wraps(vista)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())
            if request.user.rol not in roles:
                raise PermissionDenied
            return vista(request, *args, **kwargs)
        return wrapper
    return decorador


@rol_requerido("ADMIN", "RECEPCIONISTA", "MEDICO")
def expedientes(request):
    q = request.GET.get("q", "").strip()

    lista = Expediente.objects.select_related("paciente")
    if q:
        lista = lista.filter(
            Q(codigo__icontains=q)
            | Q(paciente__nombres__icontains=q)
            | Q(paciente__apellidos__icontains=q)
        )

    pacientes = Paciente.objects.filter(activo=True).order_by("apellidos", "nombres")

    return render(request, "expedientes.html", {
        "expedientes": lista,
        "pacientes": pacientes,
        "query": q,
        "today_date": timezone.localdate().isoformat(),
    })


@rol_requerido("ADMIN", "RECEPCIONISTA", "MEDICO")
def crear_expediente(request):
    if request.method == "POST":
        paciente = get_object_or_404(Paciente, pk=request.POST.get("paciente"))
        Expediente.objects.create(
            paciente=paciente,
            alergias=request.POST.get("alergias", ""),
            fecha_apertura=request.POST.get("fecha_apertura", None),
            antecedentes_personales=request.POST.get("antecedentes", ""),
            # agrega aquí los demás campos de tu modelo Expediente
        )
        messages.success(request, "Expediente creado.")
    return redirect("expedientes")
