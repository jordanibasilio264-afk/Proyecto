"""Ubicación: apps/Citas/views.py"""
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
import calendar
from collections import defaultdict
from datetime import date, timedelta

from apps.usuarios.decorators import requiere_permiso

from .forms import CancelarCitaForm, CitaForm, FiltroCitaForm, ReprogramarCitaForm
from .models import Cita


def _citas_visibles(usuario):
    """Cada rol ve solo lo que le corresponde."""
    citas = Cita.objects.select_related("paciente", "medico__usuario").prefetch_related(
        "medico__especialidades")
    if usuario.es_paciente:
        return citas.filter(paciente__usuario=usuario)
    if usuario.es_medico:
        return citas.filter(medico__usuario=usuario)
    if usuario.es_admin or usuario.es_recepcionista:
        return citas
    return citas.none()


def _pagina_formulario(request, form, titulo, boton="Guardar"):
    return render(request, "formulario.html", {
        "form": form, "titulo": titulo, "boton": boton, "volver": reverse("citas"),
    })


# ---- LISTA + FILTRO (GET)  +  CREAR desde el modal (POST) ---------------------
@requiere_permiso("citas.ver")
def citas(request):
    usuario = request.user
    form = CitaForm(usuario=usuario)
    abrir_modal = False

    if request.method == "POST":
        if not usuario.tiene_permiso("citas.crear"):
            raise Http404
        form = CitaForm(request.POST, usuario=usuario)
        if form.is_valid():
            form.save()
            messages.success(request, "Cita registrada correctamente.")
            return redirect("citas")
        abrir_modal = True  # vuelve a abrir el modal mostrando los errores

    lista = _citas_visibles(usuario)
    filtro = FiltroCitaForm(request.GET or None, usuario=usuario)
    filtrando = False
    if filtro.is_valid():
        lista = filtro.filtrar(lista)
        filtrando = any(filtro.cleaned_data.values())
    lista = lista.order_by("-inicio")
    if not filtrando and not request.GET.get("todas"):
        lista = lista[:10]  # "Citas recientes"

    return render(request, "citas.html", {
        "citas": lista, "filtro": filtro, "form": form,
        "abrir_modal": abrir_modal, "hoy": timezone.localdate(),
        "mostrando_todas": filtrando or bool(request.GET.get("todas")),
    })


# ---- EDITAR ------------------------------------------------------------------
@requiere_permiso("citas.editar")
def editar_cita(request, pk):
    cita = get_object_or_404(_citas_visibles(request.user), pk=pk)  # 404 si no es suya
    if cita.estado in ("ATENDIDA", "CANCELADA"):
        messages.error(request, "Esta cita ya no se puede editar.")
        return redirect("citas")
    form = CitaForm(request.POST or None, instance=cita, usuario=request.user)
    if form.is_valid():
        form.save()
        messages.success(request, "Cita actualizada.")
        return redirect("citas")
    return _pagina_formulario(request, form, "Editar cita")


# ---- CANCELAR (formulario con motivo) ----------------------------------------
@requiere_permiso("citas.cancelar")
def cancelar_cita(request, pk):
    cita = get_object_or_404(_citas_visibles(request.user), pk=pk)
    form = CancelarCitaForm(request.POST or None, cita=cita)
    if form.is_valid():
        form.guardar()
        messages.success(request, "Cita cancelada.")
        return redirect("citas")
    return _pagina_formulario(request, form, f"Cancelar cita de {cita.paciente}", "Cancelar cita")


# ---- REPROGRAMAR -------------------------------------------------------------
@requiere_permiso("citas.reprogramar")
def reprogramar_cita(request, pk):
    cita = get_object_or_404(_citas_visibles(request.user), pk=pk)
    form = ReprogramarCitaForm(request.POST or None, cita=cita, usuario=request.user)
    if form.is_valid():
        try:
            form.guardar()
        except ValidationError as e:
            form.add_error(None, e)
        else:
            messages.success(request, "Cita reprogramada.")
            return redirect("citas")
    return _pagina_formulario(request, form, "Reprogramar cita", "Reprogramar")


# ---- CONFIRMAR (botón simple) ------------------------------------------------
@require_POST
@requiere_permiso("citas.confirmar")
def confirmar_cita(request, pk):
    cita = get_object_or_404(_citas_visibles(request.user), pk=pk)
    try:
        cita.confirmar()
        messages.success(request, "Cita confirmada.")
    except ValidationError as e:
        messages.error(request, "; ".join(e.messages))
    return redirect("citas")

# ---- AGENDA (diaria / semanal / mensual) --------------------------------------
def _rango(vista, fecha):
    if vista == "dia":
        return fecha, fecha
    if vista == "semana":
        ini = fecha - timedelta(days=fecha.weekday())  # lunes
        return ini, ini + timedelta(days=6)
    ini = fecha.replace(day=1)
    return ini, ini.replace(day=calendar.monthrange(fecha.year, fecha.month)[1])


def _navegacion(vista, fecha):
    if vista == "dia":
        return fecha - timedelta(days=1), fecha + timedelta(days=1)
    if vista == "semana":
        return fecha - timedelta(days=7), fecha + timedelta(days=7)
    primero = fecha.replace(day=1)
    anterior = (primero - timedelta(days=1)).replace(day=1)
    siguiente = (primero + timedelta(days=32)).replace(day=1)
    return anterior, siguiente


@requiere_permiso("citas.ver")
def agenda(request):
    vista = request.GET.get("vista", "dia")
    if vista not in ("dia", "semana", "mes"):
        vista = "dia"
    try:
        fecha = date.fromisoformat(request.GET.get("fecha", ""))
    except ValueError:
        fecha = timezone.localdate()

    ini, fin = _rango(vista, fecha)
    qs = (
        _citas_visibles(request.user)
        .exclude(estado="REPROGRAMADA")  # la nueva cita ya la reemplaza
        .filter(inicio__date__range=(ini, fin))
        .order_by("inicio")
    )

    por_dia = defaultdict(list)
    for c in qs:
        por_dia[timezone.localtime(c.inicio).date()].append(c)

    contexto = {"vista": vista, "fecha": fecha, "hoy": timezone.localdate(),
                "ini": ini, "fin": fin, "total": len(qs)}
    contexto["anterior"], contexto["siguiente"] = _navegacion(vista, fecha)

    if vista == "dia":
        contexto["citas"] = por_dia.get(fecha, [])
    elif vista == "semana":
        contexto["dias"] = [
            {"fecha": ini + timedelta(days=i), "citas": por_dia.get(ini + timedelta(days=i), [])}
            for i in range(7)
        ]
    else:
        semanas = calendar.Calendar(firstweekday=0).monthdatescalendar(fecha.year, fecha.month)
        contexto["semanas"] = [
            [{"fecha": d, "citas": por_dia.get(d, []), "en_mes": d.month == fecha.month}
             for d in semana]
            for semana in semanas
        ]
    return render(request, "agenda.html", contexto)

@require_POST
@requiere_permiso("citas.atender")
def atender_cita(request, pk):
    cita = get_object_or_404(_citas_visibles(request.user), pk=pk)
    try:
        cita.marcar_atendida()
        messages.success(request, "Cita marcada como atendida.")
    except ValidationError as e:
        messages.error(request, "; ".join(e.messages))
    return redirect(request.POST.get("next") or "citas")


@require_POST
@requiere_permiso("citas.atender")
def no_asistio_cita(request, pk):
    cita = get_object_or_404(_citas_visibles(request.user), pk=pk)
    try:
        cita.marcar_no_asistio()
        messages.success(request, "Cita marcada como 'No asistió'.")
    except ValidationError as e:
        messages.error(request, "; ".join(e.messages))
    return redirect(request.POST.get("next") or "citas")