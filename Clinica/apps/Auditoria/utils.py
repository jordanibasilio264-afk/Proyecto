"""apps/Auditoria/utils.py
Ayudantes para llenar el historial de actividades."""
import logging

from .models import RegistroAuditoria

logger = logging.getLogger(__name__)
Accion = RegistroAuditoria.Accion


def auditar(request, accion, objeto=None, descripcion="", modelo=None,
            antes=None, despues=None):
    """Guarda una acción en el historial.

    auditar(request, Accion.CREAR, cita, "Registró la cita de Ana Gómez")
    Nunca interrumpe la vista: si falla, solo escribe el error en el log.
    """
    try:
        usuario = getattr(request, "user", None)
        if not getattr(usuario, "is_authenticated", False):
            usuario = None
        if modelo is None and objeto is not None:
            modelo = objeto._meta.label            # ej. "Citas.Cita"
        texto = descripcion or (str(objeto) if objeto is not None else "")
        RegistroAuditoria.objects.create(
            usuario=usuario,
            accion=accion,
            modelo=modelo or "",
            objeto_id=str(getattr(objeto, "pk", "") or ""),
            descripcion=texto[:255],
            datos_anteriores=antes,
            datos_nuevos=despues,
            ip=request.META.get("REMOTE_ADDR") or None,
        )
    except Exception:
        logger.exception("No se pudo registrar la auditoría")


class AuditarMixin:
    """Para CreateView / UpdateView: registra al guardar el formulario.

    class CitaCreateView(AuditarMixin, ..., CreateView):
        accion_auditoria = Accion.CREAR
        def descripcion_auditoria(self):
            return f"Registró la cita de {self.object.paciente}"
    """
    accion_auditoria = Accion.OTRO

    def descripcion_auditoria(self):
        return ""

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        auditar(self.request, self.accion_auditoria, self.object,
                self.descripcion_auditoria())
        return respuesta
