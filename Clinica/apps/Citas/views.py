"""Ubicación: apps/Citas/views.py"""
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

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
    return citas


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
    filtro = FiltroCitaForm(request.GET or None)
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