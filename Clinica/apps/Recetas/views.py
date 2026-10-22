from datetime import date
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import render , redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from apps.Medicamentos.models import Medicamento, Receta , DetalleReceta
from apps.usuarios.models import Medico, Paciente
from apps.Expedientes.models import Consulta
from django.core.exceptions import PermissionDenied


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
# Total de recetas creadas hoy, sin depender de los filtros de la tabla.
    recetas_hoy = recetas_lista.filter(
    fecha__date=hoy
).count()
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
        "recetas_hoy": recetas_hoy,
        "recetas_vigentes": sum(
            receta.estado_codigo == "vigente"
            for receta in recetas_administrativas
        ),
        "busqueda": busqueda,
        "estado_filtro": estado_filtro,
        "fecha_filtro": fecha_filtro,
    }

    return render(request, "recetas.html", contexto)

@login_required
def crear_receta(request):
    usuario = request.user

    # Solo los médicos autorizados pueden crear recetas.
    if not usuario.tiene_permiso("recetas.crear"):
        return HttpResponseForbidden(
            "No tienes permiso para crear recetas médicas."
        )
    # El administrador puede trabajar con consultas de cualquier médico.
    if usuario.rol == "ADMIN":
        consultas = Consulta.objects.filter(
            expediente__activo=True,
        )

    # El médico necesita un perfil activo y solo puede usar sus consultas.
    elif usuario.rol == "MEDICO":
        try:
            medico = Medico.objects.get(
                usuario=usuario,
                activo=True,
            )
        except Medico.DoesNotExist:
            return HttpResponseForbidden(
                "No tienes un perfil médico activo."
            )

        consultas = Consulta.objects.filter(
            medico=medico,
            expediente__activo=True,
        )

    else:
        return HttpResponseForbidden(
            "Tu rol no tiene acceso a la creación de recetas."
        )

    # Datos relacionados para mostrar al paciente y al médico responsable.
    consultas = consultas.select_related(
        "expediente__paciente",
        "medico__usuario",
    ).order_by("-fecha")


    medicamentos = Medicamento.objects.filter(
    activo=True
).order_by("id")

    errores = []

    if request.method == "POST":
        consulta_id = request.POST.get("consulta")
        vigente_hasta_texto = request.POST.get("vigente_hasta", "").strip()
        indicaciones_generales = request.POST.get(
            "indicaciones_generales", ""
        ).strip()

        # Cada medicamento se envía como una fila independiente.
        medicamentos_ids = request.POST.getlist("medicamento_id[]")
        dosis_lista = request.POST.getlist("dosis[]")
        frecuencias = request.POST.getlist("frecuencia[]")
        duraciones = request.POST.getlist("duracion_dias[]")
        vias = request.POST.getlist("via_administracion[]")
        cantidades = request.POST.getlist("cantidad[]")
        instrucciones_lista = request.POST.getlist("instrucciones[]")

        # Validar la consulta dentro del conjunto permitido.
        consulta = consultas.filter(pk=consulta_id).first()

        if consulta is None:
            errores.append(
                "Selecciona una consulta válida que te corresponda."
            )

        # La fecha de vigencia es opcional, pero no puede estar vencida.
        vigente_hasta = None

        if vigente_hasta_texto:
            vigente_hasta = parse_date(vigente_hasta_texto)

            if vigente_hasta is None:
                errores.append("La fecha de vigencia no es válida.")
            elif vigente_hasta < timezone.localdate():
                errores.append(
                    "La fecha de vigencia no puede estar en el pasado."
                )

        total_filas = len(medicamentos_ids)

        if total_filas == 0:
            errores.append("Agrega al menos un medicamento.")

        # Comprobar que todas las listas tengan el mismo número de filas.
        listas = [
            dosis_lista,
            frecuencias,
            duraciones,
            vias,
            cantidades,
            instrucciones_lista,
        ]

        if any(len(lista) != total_filas for lista in listas):
            errores.append(
                "Los datos de los medicamentos están incompletos. "
                "Revisa las filas del formulario."
            )

        detalles = []
        medicamentos_vistos = set()

        if not errores:
            for i, medicamento_id in enumerate(medicamentos_ids):
                medicamento = medicamentos.filter(
                    pk=medicamento_id
                ).first()

                if medicamento is None:
                    errores.append(
                        f"El medicamento de la fila {i + 1} "
                        "no es válido o está inactivo."
                    )
                    continue

                if medicamento.pk in medicamentos_vistos:
                    errores.append(
                        f"No puedes repetir {medicamento.nombre_comercial} "
                        "en la misma receta."
                    )
                    continue

                medicamentos_vistos.add(medicamento.pk)

                dosis = dosis_lista[i].strip()
                frecuencia = frecuencias[i].strip()
                duracion_texto = duraciones[i].strip()
                via = vias[i].strip()
                cantidad_texto = cantidades[i].strip()
                instrucciones = instrucciones_lista[i].strip()

                if not dosis:
                    errores.append(
                        f"Indica la dosis del medicamento de la fila {i + 1}."
                    )

                if not frecuencia:
                    errores.append(
                        f"Indica la frecuencia del medicamento de la fila {i + 1}."
                    )

                try:
                    cantidad = int(cantidad_texto)
                    if cantidad < 1 or cantidad > 32767:
                        raise ValueError
                except (ValueError, TypeError):
                    errores.append(
                        f"La cantidad de la fila {i + 1} debe ser "
                        "un número entero positivo."
                    )
                    cantidad = None

                duracion = None

                if duracion_texto:
                    try:
                        duracion = int(duracion_texto)
                        if duracion < 1 or duracion > 32767:
                            raise ValueError
                    except (ValueError, TypeError):
                        errores.append(
                            f"La duración de la fila {i + 1} debe ser "
                            "un número entero positivo."
                        )

                if len(dosis) > 100 or len(frecuencia) > 100:
                    errores.append(
                        f"La dosis o frecuencia de la fila {i + 1} "
                        "supera la longitud permitida."
                    )

                if len(via) > 50 or len(instrucciones) > 255:
                    errores.append(
                        f"La vía o las instrucciones de la fila {i + 1} "
                        "superan la longitud permitida."
                    )

                detalles.append({
                    "medicamento": medicamento,
                    "dosis": dosis,
                    "frecuencia": frecuencia,
                    "duracion_dias": duracion,
                    "via_administracion": via,
                    "cantidad": cantidad,
                    "instrucciones": instrucciones,
                })

        if not errores:
            try:
                with transaction.atomic():
                    receta = Receta.objects.create(
                        consulta=consulta,
                        vigente_hasta=vigente_hasta,
                        indicaciones_generales=indicaciones_generales,
                    )

                    for detalle in detalles:
                        DetalleReceta.objects.create(
                            receta=receta,
                            **detalle,
                        )

            except Exception:
                # Evita mostrar detalles internos de la base de datos.
                errores.append(
                    "No se pudo guardar la receta. "
                    "Verifica los datos e inténtalo nuevamente."
                )
            else:
                return redirect("recetas")

    contexto = {
        "consultas": consultas,
        "medicamentos": medicamentos,
        "errores": errores,
        "hoy": date.today().isoformat(),
    }

    return render(request, "crear_receta.html", contexto)

def consultas_permitidas(usuario):
    """
    Devuelve únicamente las consultas que el usuario puede utilizar.
    No confía en los identificadores enviados desde el navegador.
    """
    consultas = Consulta.objects.filter(expediente__activo=True)

    if usuario.rol == "ADMIN":
        return consultas

    if usuario.rol == "MEDICO":
        try:
            medico = Medico.objects.get(usuario=usuario, activo=True)
        except Medico.DoesNotExist:
            return Consulta.objects.none()

        return consultas.filter(medico=medico)

    return Consulta.objects.none()


def receta_permitida(usuario, receta_id):
    """
    Recupera una receta únicamente si el usuario tiene acceso a ella.
    """
    recetas_usuario = (
        Receta.objects
        .select_related(
            "consulta__expediente__paciente",
            "consulta__medico__usuario",
        )
        .prefetch_related("detalles__medicamento")
    )

    if usuario.rol == "ADMIN":
        return get_object_or_404(recetas_usuario, pk=receta_id)

    if usuario.rol == "MEDICO":
        return get_object_or_404(
            recetas_usuario,
            pk=receta_id,
            consulta__medico__usuario=usuario,
        )

    if usuario.rol == "PACIENTE":
        try:
            paciente = usuario.perfil_paciente
        except Paciente.DoesNotExist:
            raise PermissionDenied(
                "Tu usuario no tiene un perfil de paciente asociado."
            )

        return get_object_or_404(
            recetas_usuario,
            pk=receta_id,
            consulta__expediente__paciente=paciente,
        )

    raise PermissionDenied(
        "Tu rol no tiene acceso a esta receta."
    )



@login_required
def detalle_receta(request, receta_id):
    usuario = request.user

    if not usuario.tiene_permiso("recetas.ver"):
        return HttpResponseForbidden(
            "No tienes permiso para consultar recetas."
        )

    receta = receta_permitida(usuario, receta_id)

    receta.estado_codigo, receta.estado_display = estado_efectivo(
        receta,
        timezone.localdate(),
    )

    puede_editar = (
        usuario.tiene_permiso("recetas.editar")
        and receta.estado not in (
            Receta.Estado.ANULADA,
            Receta.Estado.COMPLETADA,
        )
    )

    modo_impresion = request.GET.get("imprimir") == "1"

    if modo_impresion and not usuario.tiene_permiso("recetas.imprimir"):
        return HttpResponseForbidden(
            "No tienes permiso para imprimir recetas."
        )

    contexto = {
        "receta": receta,
        "puede_editar": puede_editar,
        "modo_impresion": modo_impresion,
    }

    return render(request, "detalle_receta.html", contexto)


@login_required
def buscar_consultas(request):
    """
    Búsqueda AJAX de consultas autorizadas.
    Devuelve un máximo de 20 resultados.
    """
    usuario = request.user

    if not usuario.tiene_permiso("recetas.crear"):
        return JsonResponse(
            {"error": "No tienes permiso para buscar consultas."},
            status=403,
        )

    termino = request.GET.get("q", "").strip()

    if len(termino) < 2:
        return JsonResponse({"resultados": []})

    consultas = consultas_permitidas(usuario).select_related(
        "expediente__paciente",
        "medico__usuario",
    )

    filtros = (
        Q(expediente__paciente__nombres__icontains=termino)
        | Q(expediente__paciente__apellidos__icontains=termino)
    )

    # Permite buscar por número de consulta si el término es numérico.
    if termino.isdigit():
        filtros |= Q(pk=int(termino))

    # También permite buscar por fecha con formato YYYY-MM-DD.
    fecha = parse_date(termino)
    if fecha:
        filtros |= Q(fecha__date=fecha)

    consultas = consultas.filter(filtros).order_by("-fecha")[:20]

    resultados = []

    for consulta in consultas:
        paciente = consulta.expediente.paciente
        medico = consulta.medico

        resultados.append({
            "id": consulta.pk,
            "texto": (
                f"Consulta #{consulta.pk} — "
                f"{paciente} — "
                f"{consulta.fecha:%d/%m/%Y}"
            ),
            "paciente": str(paciente),
            "medico": str(medico),
            "fecha": consulta.fecha.strftime("%d/%m/%Y"),
        })

    return JsonResponse({"resultados": resultados})


@login_required
def editar_receta(request, receta_id):
    usuario = request.user

    if not usuario.tiene_permiso("recetas.editar"):
        return HttpResponseForbidden(
            "No tienes permiso para editar recetas."
        )

    receta = receta_permitida(usuario, receta_id)

    # No se permite editar recetas anuladas o completadas.
    if receta.estado in (
        Receta.Estado.ANULADA,
        Receta.Estado.COMPLETADA,
    ):
        return HttpResponseForbidden(
            "No puedes editar una receta anulada o completada."
        )

    detalles_actuales = list(
        receta.detalles.select_related("medicamento").all()
    )

    # Se incluyen medicamentos activos y los que ya figuran
    # en esta receta, aunque posteriormente hayan sido desactivados.
    medicamentos = (
        Medicamento.objects
        .filter(
            Q(activo=True)
            | Q(usos_en_recetas__receta=receta)
        )
        .distinct()
        .order_by("id")
    )

    errores = []

    filas = [
        {
            "medicamento_id": detalle.medicamento_id,
            "dosis": detalle.dosis,
            "frecuencia": detalle.frecuencia,
            "duracion_dias": (
                detalle.duracion_dias
                if detalle.duracion_dias is not None
                else ""
            ),
            "via_administracion": detalle.via_administracion,
            "cantidad": detalle.cantidad,
            "instrucciones": detalle.instrucciones,
        }
        for detalle in detalles_actuales
    ]

    vigente_hasta_texto = (
        receta.vigente_hasta.isoformat()
        if receta.vigente_hasta
        else ""
    )
    indicaciones_generales = receta.indicaciones_generales

    if request.method == "POST":
        vigente_hasta_texto = request.POST.get(
            "vigente_hasta", ""
        ).strip()

        indicaciones_generales = request.POST.get(
            "indicaciones_generales", ""
        ).strip()

        ids = request.POST.getlist("medicamento_id[]")
        dosis_lista = request.POST.getlist("dosis[]")
        frecuencias = request.POST.getlist("frecuencia[]")
        duraciones = request.POST.getlist("duracion_dias[]")
        vias = request.POST.getlist("via_administracion[]")
        cantidades = request.POST.getlist("cantidad[]")
        instrucciones_lista = request.POST.getlist("instrucciones[]")

        filas = []
        listas = [
            dosis_lista,
            frecuencias,
            duraciones,
            vias,
            cantidades,
            instrucciones_lista,
        ]

        if not ids:
            errores.append("Agrega al menos un medicamento.")

        if any(len(lista) != len(ids) for lista in listas):
            errores.append(
                "Los datos de los medicamentos están incompletos. "
                "Revisa las filas del formulario."
            )

        vigente_hasta = None

        if vigente_hasta_texto:
            vigente_hasta = parse_date(vigente_hasta_texto)

            if vigente_hasta is None:
                errores.append("La fecha de vigencia no es válida.")
            elif vigente_hasta < timezone.localdate():
                errores.append(
                    "La fecha de vigencia no puede estar en el pasado."
                )

        detalles_nuevos = []
        medicamentos_vistos = set()

        if not errores:
            medicamentos_existentes = {
                detalle.medicamento_id
                for detalle in detalles_actuales
            }

            for i, medicamento_id in enumerate(ids):
                dosis = dosis_lista[i].strip()
                frecuencia = frecuencias[i].strip()
                duracion_texto = duraciones[i].strip()
                via = vias[i].strip()
                cantidad_texto = cantidades[i].strip()
                instrucciones = instrucciones_lista[i].strip()

                filas.append({
                    "medicamento_id": medicamento_id,
                    "dosis": dosis,
                    "frecuencia": frecuencia,
                    "duracion_dias": duracion_texto,
                    "via_administracion": via,
                    "cantidad": cantidad_texto,
                    "instrucciones": instrucciones,
                })

                medicamento = medicamentos.filter(
                    pk=medicamento_id
                ).first()

                if medicamento is None:
                    errores.append(
                        f"El medicamento de la fila {i + 1} "
                        "no es válido."
                    )
                    continue

                if (
                    not medicamento.activo
                    and medicamento.pk not in medicamentos_existentes
                ):
                    errores.append(
                        f"El medicamento de la fila {i + 1} "
                        "está inactivo."
                    )
                    continue

                if medicamento.pk in medicamentos_vistos:
                    errores.append(
                        f"No puedes repetir "
                        f"{medicamento.nombre_comercial} "
                        "en la misma receta."
                    )
                    continue

                medicamentos_vistos.add(medicamento.pk)

                if not dosis or not frecuencia:
                    errores.append(
                        f"Completa la dosis y frecuencia "
                        f"de la fila {i + 1}."
                    )

                if len(dosis) > 100 or len(frecuencia) > 100:
                    errores.append(
                        f"La dosis o frecuencia de la fila "
                        f"{i + 1} es demasiado larga."
                    )

                if len(via) > 50 or len(instrucciones) > 255:
                    errores.append(
                        f"La vía o las instrucciones de la fila "
                        f"{i + 1} son demasiado largas."
                    )

                try:
                    cantidad = int(cantidad_texto)
                    if not 1 <= cantidad <= 32767:
                        raise ValueError
                except (ValueError, TypeError):
                    errores.append(
                        f"La cantidad de la fila {i + 1} "
                        "debe ser un entero positivo."
                    )
                    cantidad = None

                duracion = None

                if duracion_texto:
                    try:
                        duracion = int(duracion_texto)
                        if not 1 <= duracion <= 32767:
                            raise ValueError
                    except (ValueError, TypeError):
                        errores.append(
                            f"La duración de la fila {i + 1} "
                            "debe ser un entero positivo."
                        )

                detalles_nuevos.append({
                    "medicamento": medicamento,
                    "dosis": dosis,
                    "frecuencia": frecuencia,
                    "duracion_dias": duracion,
                    "via_administracion": via,
                    "cantidad": cantidad,
                    "instrucciones": instrucciones,
                })

        if not errores:
            try:
                with transaction.atomic():
                    receta.vigente_hasta = vigente_hasta
                    receta.indicaciones_generales = (
                        indicaciones_generales
                    )
                    receta.save(
                        update_fields=[
                            "vigente_hasta",
                            "indicaciones_generales",
                        ]
                    )

                    # Conservar los detalles que siguen en la receta,
                    # actualizar sus datos y crear los nuevos.
                    detalles_por_medicamento = {
                        detalle.medicamento_id: detalle
                        for detalle in detalles_actuales
                    }

                    ids_finales = {
                        detalle["medicamento"].pk
                        for detalle in detalles_nuevos
                    }

                    for detalle in detalles_actuales:
                        if detalle.medicamento_id not in ids_finales:
                            detalle.delete()

                    for datos in detalles_nuevos:
                        medicamento = datos["medicamento"]
                        detalle_existente = (
                            detalles_por_medicamento.get(
                                medicamento.pk
                            )
                        )

                        if detalle_existente:
                            detalle_existente.dosis = datos["dosis"]
                            detalle_existente.frecuencia = (
                                datos["frecuencia"]
                            )
                            detalle_existente.duracion_dias = (
                                datos["duracion_dias"]
                            )
                            detalle_existente.via_administracion = (
                                datos["via_administracion"]
                            )
                            detalle_existente.cantidad = (
                                datos["cantidad"]
                            )
                            detalle_existente.instrucciones = (
                                datos["instrucciones"]
                            )
                            detalle_existente.save()
                        else:
                            DetalleReceta.objects.create(
                                receta=receta,
                                **datos,
                            )

            except Exception:
                errores.append(
                    "No se pudo actualizar la receta. "
                    "Verifica los datos e inténtalo nuevamente."
                )
            else:
                return redirect(
                    "detalle_receta",
                    receta_id=receta.pk,
                )

    contexto = {
        "receta": receta,
        "medicamentos": medicamentos,
        "filas": filas,
        "errores": errores,
        "vigente_hasta": vigente_hasta_texto,
        "indicaciones_generales": indicaciones_generales,
    }

    return render(request, "editar_receta.html", contexto)



@login_required
def imprimir_receta(request, receta_id):
    url = reverse(
        "detalle_receta",
        kwargs={"receta_id": receta_id},
    )

    return redirect(f"{url}?imprimir=1")