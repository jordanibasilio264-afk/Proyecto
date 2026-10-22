"""apps/Auditoria/middleware.py
Guarda la petición actual para que las señales sepan QUÉ usuario
hizo el cambio y desde qué IP."""
from contextvars import ContextVar

_request_actual = ContextVar("auditoria_request", default=None)


def obtener_request():
    return _request_actual.get()


class AuditoriaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = _request_actual.set(request)
        try:
            return self.get_response(request)
        finally:
            _request_actual.reset(token)
