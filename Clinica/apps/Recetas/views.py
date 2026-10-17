
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.utils import timezone

from apps.Medicamentos.models import Receta
from apps.usuarios.models import Paciente


def estado_efectivo(receta, hoy):
    """
    Calcula el estado que debe mostrarse en pantalla.
    La anulación y la finalización tienen prioridad sobre el vencimiento.
    """
    if receta.estado == Receta.Estado.ANULADA:
        return "anulada", "Anulada"

    if receta.estado == Receta.Estado.COMPLETADA:
        return "completada", "Completada"

    if receta.vigente_hasta and receta.vigente_hasta < hoy:
        return "vencida", "Vencida"

    return "vigente", "Vigente"


@login_required
def recetas(request):
    usuario = request.user

    if not usuario.tiene_permiso("recetas.ver"):
        return HttpResponseForbidden(
            "No tienes permiso para consultar las recetas."
        )

    hoy = timezone.localdate()

    recetas_base = (
        Receta.objects
        .select_related(
            "consulta__expediente__paciente",
            "consulta__medico__usuario",
        )
        .prefetch_related("detalles__medicamento")
    )

    # PACIENTE: acceso exclusivo a sus propias recetas.
    if usuario.rol == "PACIENTE":
        try:
            paciente = usuario.perfil_paciente
        except Paciente.DoesNotExist:
            return HttpResponseForbidden(
                "Tu usuario no tiene un perfil de paciente asociado."
            )

        recetas_lista = recetas_base.filter(
            consulta__expediente__paciente=paciente
        )

        busqueda = request.GET.get("q", "").strip()
        estado_filtro = request.GET.get("estado", "").strip()

        if busqueda:
            recetas_lista = recetas_lista.filter(
                Q(numero__icontains=busqueda)
                | Q(
                    detalles__medicamento__nombre_comercial__icontains=busqueda
                )
                | Q(
                    detalles__medicamento__nombre_generico__icontains=busqueda
                )
                | Q(
                    consulta__medico__usuario__first_name__icontains=busqueda
                )
                | Q(
                    consulta__medico__usuario__last_name__icontains=busqueda
                )
            ).distinct()

        # Se calculan los estados antes de filtrar porque Vencida
        # es un estado derivado de la fecha límite.
        recetas_paciente = list(recetas_lista)

        for receta in recetas_paciente:
            receta.estado_codigo, receta.estado_display = estado_efectivo(
                receta, hoy
            )

        if estado_filtro in {
            "vigente", "vencida", "completada", "anulada"
        }:
            recetas_paciente = [
                receta for receta in recetas_paciente
                if receta.estado_codigo == estado_filtro
            ]

        recetas_vigentes = sum(
            receta.estado_codigo == "vigente"
            for receta in recetas_paciente
        )

        contexto = {
            "recetas": recetas_paciente,
            "total_recetas": len(recetas_paciente),
            "recetas_vigentes": recetas_vigentes,
            "busqueda": busqueda,
            "estado_filtro": estado_filtro,
        }

        return render(request, "pacientes_R.html", contexto)

    # ADMINISTRADOR: puede consultar todas las recetas.
    if usuario.rol == "ADMIN":
        recetas_lista = recetas_base

    # MÉDICO: solo consulta las recetas que ha emitido.
    elif usuario.rol == "MEDICO":
        recetas_lista = recetas_base.filter(
            consulta__medico__usuario=usuario
        )

    else:
        return HttpResponseForbidden(
            "Tu rol no tiene acceso a esta sección."
        )

    # Filtros de la página administrativa.
    busqueda = request.GET.get("buscar", "").strip()
    estado_filtro = request.GET.get("estado", "").strip()
    fecha_filtro = request.GET.get("fecha", "").strip()

    if busqueda:
        recetas_lista = recetas_lista.filter(
            Q(numero__icontains=busqueda)
            | Q(
                consulta__expediente__paciente__nombres__icontains=busqueda
            )
            | Q(
                consulta__expediente__paciente__apellidos__icontains=busqueda
            )
            | Q(
                consulta__medico__usuario__first_name__icontains=busqueda
            )
            | Q(
                consulta__medico__usuario__last_name__icontains=busqueda
            )
            | Q(
                detalles__medicamento__nombre_comercial__icontains=busqueda
            )
            | Q(
                detalles__medicamento__nombre_generico__icontains=busqueda
            )
        ).distinct()

    if fecha_filtro:
        recetas_lista = recetas_lista.filter(fecha__date=fecha_filtro)

    recetas_administrativas = list(recetas_lista)

    for receta in recetas_administrativas:
        receta.estado_codigo, receta.estado_display = estado_efectivo(
            receta, hoy
        )

    if estado_filtro in {
        "vigente", "vencida", "completada", "anulada"
    }:
        recetas_administrativas = [
            receta for receta in recetas_administrativas
            if receta.estado_codigo == estado_filtro
        ]

    contexto = {
        "recetas": recetas_administrativas,
        "total_recetas": len(recetas_administrativas),
        "recetas_hoy": sum(
            receta.fecha.date() == hoy
            for receta in recetas_administrativas
        ),
        "recetas_vigentes": sum(
            receta.estado_codigo == "vigente"
            for receta in recetas_administrativas
        ),
        "busqueda": busqueda,
        "estado_filtro": estado_filtro,
        "fecha_filtro": fecha_filtro,
    }

    return render(request, "recetas.html", contexto)


