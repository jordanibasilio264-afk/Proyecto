from django.shortcuts import render
from functools import wraps
from django.core.exceptions import PermissionDenied

def rol_requerido(*roles):
    def decorador(vista):
        @wraps(vista)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())
            if request.user.rol not in roles:   # ajusta a como guardas el rol
                raise PermissionDenied
            return vista(request, *args, **kwargs)
        return wrapper
    return decorador


@rol_requerido("ADMIN", "RECEPCIONISTA", "MEDICO","PACIENTE")
def notificaciones(request):
    return render(request,"notificaciones.html")

    #recordatorios = 12
    #alertas = 3
    #cancelaciones = 2
    #total = 17

    #datos = {
        #"recordatorios": recordatorios,
        #"alertas": alertas,
        #"cancelaciones": cancelaciones,
        #"total": total,
    #}

