"""apps/Auditoria/signals.py
1) Accesos: inicios y cierres de sesión, e intentos fallidos.
2) Historial automático: crear / modificar / eliminar en todos los
   modelos de tus apps (apps.*), con el usuario y la IP de la petición."""
from django.contrib.auth.signals import (
    user_logged_in, user_logged_out, user_login_failed,
)
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .middleware import obtener_request
from .models import RegistroAcceso
from .utils import Accion, auditar

Evento = RegistroAcceso.Evento

# Modelos que NO quieres en el historial, ej. {"notificaciones.Notificacion"}
MODELOS_EXCLUIDOS = set()
# Campos que nunca se guardan en el detalle de los cambios
SENSIBLES = ("password", "contrasena", "clave", "token", "last_login")


# ------------------------------------------------------------------
# 1) ACCESOS
# ------------------------------------------------------------------
def _registrar_acceso(evento, request, usuario=None, email=""):
    meta = request.META if request else {}
    RegistroAcceso.objects.create(
        usuario=usuario,
        email_intentado=email or getattr(usuario, "email", ""),
        evento=evento,
        ip=meta.get("REMOTE_ADDR") or None,
        user_agent=meta.get("HTTP_USER_AGENT", "")[:255],
    )


@receiver(user_logged_in)
def al_entrar(sender, request, user, **kwargs):
    _registrar_acceso(Evento.LOGIN, request, user)


@receiver(user_logged_out)
def al_salir(sender, request, user, **kwargs):
    _registrar_acceso(Evento.LOGOUT, request, user)


@receiver(user_login_failed)
def al_fallar(sender, credentials, request=None, **kwargs):
    email = credentials.get("email") or credentials.get("username", "")
    _registrar_acceso(Evento.LOGIN_FALLIDO, request, email=email)


# ------------------------------------------------------------------
# 2) HISTORIAL AUTOMÁTICO
# ------------------------------------------------------------------
def _auditable(sender):
    cfg = sender._meta.app_config
    return (
        cfg is not None
        and cfg.name.startswith("apps.")          # solo tus apps
        and cfg.label != "Auditoria"              # nunca auditar la auditoría
        and sender._meta.label not in MODELOS_EXCLUIDOS
    )


def _valor(v):
    return v if v is None or isinstance(v, (bool, int, float, str)) else str(v)


def _campos(instance):
    """Foto de los campos del objeto (sin datos sensibles ni automáticos)."""
    datos = {}
    for f in instance._meta.concrete_fields:
        nombre = f.name.lower()
        if getattr(f, "auto_now", False) or getattr(f, "auto_now_add", False):
            continue
        if any(s in nombre for s in SENSIBLES):
            continue
        datos[f.name] = _valor(getattr(instance, f.attname))
    return datos


def _nombre(instance):
    return str(instance._meta.verbose_name).capitalize()


@receiver(pre_save)
def antes_de_guardar(sender, instance, raw=False, **kwargs):
    """Si es una edición, compara con lo que hay en la base de datos."""
    instance._aud_cambios = None
    if raw or not _auditable(sender) or obtener_request() is None:
        return
    if instance.pk is None or instance._state.adding:
        return
    try:
        anterior = sender._base_manager.filter(pk=instance.pk).first()
        if anterior is None:
            return
        antes, despues = _campos(anterior), _campos(instance)
        instance._aud_cambios = {
            k: (antes[k], despues[k]) for k in despues if antes.get(k) != despues[k]
        }
    except Exception:
        instance._aud_cambios = None


@receiver(post_save)
def despues_de_guardar(sender, instance, created, raw=False, **kwargs):
    request = obtener_request()
    if raw or request is None or not _auditable(sender):
        return
    try:
        if created:
            auditar(request, Accion.CREAR, instance,
                    f"Creó {_nombre(instance).lower()}: {instance}",
                    despues=_campos(instance))
            return
        cambios = getattr(instance, "_aud_cambios", None)
        if not cambios:                      # se guardó sin cambiar nada
            return
        desactivado = "activo" in cambios and cambios["activo"][1] is False
        auditar(
            request,
            Accion.ELIMINAR if desactivado else Accion.EDITAR,
            instance,
            f"{'Desactivó' if desactivado else 'Modificó'} "
            f"{_nombre(instance).lower()}: {instance} ({', '.join(cambios)})",
            antes={k: v[0] for k, v in cambios.items()},
            despues={k: v[1] for k, v in cambios.items()},
        )
    except Exception:
        pass                                  # la auditoría nunca rompe la vista


@receiver(post_delete)
def despues_de_eliminar(sender, instance, **kwargs):
    request = obtener_request()
    if request is None or not _auditable(sender):
        return
    try:
        auditar(request, Accion.ELIMINAR, instance,
                f"Eliminó {_nombre(instance).lower()}: {instance}",
                antes=_campos(instance))
    except Exception:
        pass
