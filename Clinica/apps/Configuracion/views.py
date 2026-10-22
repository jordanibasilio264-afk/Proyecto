from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.db import transaction
from django.http import Http404
from django.shortcuts import redirect, render
from django.core.paginator import Paginator
from apps.usuarios.models import (Especialidad, HorarioMedico, Medico,
                                  Paciente, Usuarios,)
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.urls import reverse

from .models import NOTIF_POR_ROL, ConfiguracionConsultorio, PreferenciasUsuario
from .forms import DatosClinicaForm, UsuarioAdminForm

PLANTILLAS = {
    "ADMIN": "configuracion_administrador.html",
    "MEDICO": "configuracion_medico.html",
    "RECEPCIONISTA": "configuracion_recepcionista.html",
    "PACIENTE": "configuracion_cliente.html",
}
DIAS = "LMXJVSD"  # índice = HorarioMedico.dia_semana (0=Lunes ... 6=Domingo)


def _errores(request, errores):
    for e in errores:
        messages.error(request, e)


def _errores_form(request, form):
    _errores(request, [e for lista in form.errors.values() for e in lista])


# ---------------------------------------------------------------- perfil
def guardar_perfil(request):
    u = request.user
    nombre = request.POST.get("nombre", "").strip()
    email = request.POST.get("email", "").strip()
    telefono = request.POST.get("telefono", "").strip()

    if not nombre or not email:
        return _errores(request, ["El nombre y el correo son obligatorios."])
    if Usuarios.objects.filter(email__iexact=email).exclude(pk=u.pk).exists():
        return _errores(request, ["Ese correo ya está en uso."])

    nombres, _, apellidos = nombre.partition(" ")
    ficha = getattr(u, "perfil_paciente", None) if u.es_paciente else None

    with transaction.atomic():
        if ficha:
            # Paciente.save() sincroniza nombre, teléfono y correo hacia Usuarios
            ficha.nombres, ficha.apellidos = nombres, apellidos
            ficha.email, ficha.telefono = email, telefono
            ficha.fecha_nacimiento = request.POST.get("fecha_nacimiento") or None
            ficha.direccion = request.POST.get("direccion", "").strip()
            ficha.save()
        else:
            u.first_name, u.last_name = nombres, apellidos
            u.email, u.telefono = email, telefono
            u.save()

        if u.es_medico and hasattr(u, "perfil_medico"):
            esp = Especialidad.objects.filter(pk=request.POST.get("especialidad")).first()
            if esp:
                u.perfil_medico.especialidades.set([esp])

    messages.success(request, "Perfil actualizado.")

# ---------------------------------------------------------------- password
def cambiar_password(request):
    form = PasswordChangeForm(request.user, {
        "old_password": request.POST.get("password_actual"),
        "new_password1": request.POST.get("password_nueva"),
        "new_password2": request.POST.get("password_confirmar"),
    })
    if form.is_valid():
        update_session_auth_hash(request, form.save())
        messages.success(request, "Contraseña cambiada.")
    else:
        _errores_form(request, form)


# ---------------------------------------------------------------- notificaciones
def guardar_notificaciones(request, prefs):
    claves = NOTIF_POR_ROL.get(request.user.rol, [])
    prefs.notificaciones = {k: f"notif_{k}" in request.POST for k in claves}
    medio = request.POST.get("medio")
    if medio in ("notificacion", "correo", "sms"):
        prefs.medio_aviso = medio
    prefs.save()
    messages.success(request, "Notificaciones guardadas.")


# ---------------------------------------------------------------- clínica (admin)
def guardar_clinica(request, consultorio):
    if not request.user.tiene_permiso("configuracion.editar"):
        raise Http404
    form = DatosClinicaForm(request.POST, instance=consultorio)
    if form.is_valid():
        form.save()
        messages.success(request, "Datos de la clínica guardados.")
    else:
        _errores_form(request, form)


# ---------------------------------------------------------------- paciente: emergencia
def guardar_emergencia(request):
    ficha = getattr(request.user, "perfil_paciente", None)
    if not ficha:
        return _errores(request, ["No tienes una ficha de paciente asociada."])
    ficha.contacto_emergencia_nombre = request.POST.get("emergencia_nombre", "").strip()
    ficha.contacto_emergencia_telefono = request.POST.get("emergencia_telefono", "").strip()
    ficha.save()
    messages.success(request, "Contacto de emergencia guardado.")


# ---------------------------------------------------------------- médico: horario
def guardar_horario(request):
    medico = getattr(request.user, "perfil_medico", None)
    if not medico:
        return _errores(request, ["Tu usuario no tiene perfil de médico."])
    try:
        inicio = request.POST["hora_inicio"]
        fin = request.POST["hora_fin"]
        duracion = int(request.POST["duracion_consulta"])
    except (KeyError, ValueError):
        return _errores(request, ["Revisa los datos del horario."])
    if fin <= inicio:
        return _errores(request, ["La hora de fin debe ser posterior a la de inicio."])

    dias = [DIAS.index(d) for d in request.POST.getlist("dias") if d in DIAS]
    with transaction.atomic():
        medico.duracion_cita_minutos = duracion
        medico.save(update_fields=["duracion_cita_minutos"])
        # Un horario por día marcado; los desmarcados se desactivan
        for i in range(7):
            if i in dias:
                HorarioMedico.objects.update_or_create(
                    medico=medico, dia_semana=i,
                    defaults={"hora_inicio": inicio, "hora_fin": fin, "activo": True},
                )
            else:
                HorarioMedico.objects.filter(medico=medico, dia_semana=i).update(activo=False)
    messages.success(request, "Horario guardado.")


ACCIONES = {
    "perfil": guardar_perfil,
    "password": cambiar_password,
    "emergencia": guardar_emergencia,
    "horario": guardar_horario,
}

@login_required
def configuracion(request):
    u = request.user
    if u.rol not in PLANTILLAS or not u.tiene_permiso("configuracion.ver"):
        raise Http404

    prefs = PreferenciasUsuario.obtener(u)
    consultorio = ConfiguracionConsultorio.obtener()

    if request.method == "POST":
        accion = request.POST.get("accion")
        if accion == "notificaciones":
            guardar_notificaciones(request, prefs)
        elif accion == "clinica":
            guardar_clinica(request, consultorio)
        elif accion in ACCIONES:
            ACCIONES[accion](request)
        return redirect("configuracion")

    nombre = u.get_full_name() or u.email
    ctx = {
        "rol": u.rol,
        "rol_texto": u.get_rol_display(),
        "nombre_completo": nombre,
        "iniciales": "".join(p[0] for p in nombre.split()[:2]).upper(),
        "notifs": prefs.notificaciones,
        "medio": prefs.medio_aviso,
        "consultorio": consultorio,
        "duraciones": [15, 30, 45, 60],
    }

    if u.es_medico and hasattr(u, "perfil_medico"):
        medico = u.perfil_medico
        horarios = {h.dia_semana: h for h in medico.horarios.filter(activo=True)}
        primero = next(iter(sorted(horarios.values(), key=lambda h: h.dia_semana)), None)
        ctx.update({
            "medico": medico,
            "dias_activos": DIAS_ACTIVOS(horarios),
            "hora_inicio": primero.hora_inicio.strftime("%H:%M") if primero else "08:00",
            "hora_fin": primero.hora_fin.strftime("%H:%M") if primero else "16:00",
            "especialidades": Especialidad.objects.filter(activa=True),
            "especialidad_actual": medico.especialidades.first(),
        })
    if u.es_paciente:
        ctx["ficha"] = getattr(u, "perfil_paciente", None)

    if u.tiene_permiso("usuarios.ver"):
        qs = Usuarios.objects.order_by("first_name", "last_name", "email")
        if u.rol == "RECEPCIONISTA":
            qs = qs.filter(rol="PACIENTE")
        paginador = Paginator(qs, 10)
        pagina = paginador.get_page(request.GET.get("page"))
        for x in pagina:
            x.iniciales = ((x.first_name[:1] + x.last_name[:1]) or x.email[:1]).upper()
        ctx["usuarios"] = pagina

    return render(request, PLANTILLAS[u.rol], ctx)


def DIAS_ACTIVOS(horarios):
    """Letras de los días con horario activo, ej. 'LMXJV'."""
    return "".join(DIAS[i] for i in sorted(horarios))

def _volver_a_usuarios():
    return reverse("configuracion") + "#usuarios"


def _form_usuario(request, usuario=None):
    form = UsuarioAdminForm(request.POST or None, instance=usuario,solicitante=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Usuario actualizado." if usuario else "Usuario creado.")
        return redirect(_volver_a_usuarios())

    nombre = request.user.get_full_name() or request.user.email
    return render(request, "configuracion_usuario_form.html", {
        "form": form,
        "usuario": usuario,
        "volver": _volver_a_usuarios(),
        "nombre_completo": nombre,
        "rol_texto": request.user.get_rol_display(),
    })


@login_required
def usuario_nuevo(request):
    if not request.user.tiene_permiso("usuarios.crear"):
        raise PermissionDenied
    return _form_usuario(request)


@login_required
def usuario_editar(request, pk):
    if request.user.rol == "RECEPCIONISTA" or not request.user.tiene_permiso("usuarios.editar"):
        raise PermissionDenied
    if not request.user.tiene_permiso("usuarios.editar"):
        raise PermissionDenied
    # Los administradores no se pueden editar: ni por botón ni por URL
    editables = Usuarios.objects.exclude(rol="ADMIN").exclude(is_superuser=True)
    return _form_usuario(request, get_object_or_404(editables, pk=pk))