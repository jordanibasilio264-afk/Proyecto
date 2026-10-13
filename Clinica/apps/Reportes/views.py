 # Cantidad de información
    #pacientes = 248
    #citas = 156
    #consultas = 189
    #pagos = 124
    #diagnosticos = 215
    #medicos = 32

    # Dinero
    #ingresos = "RD$24,850.00"

    # Enviar los datos al HTML
    #datos = {
    #     "pacientes": pacientes,
    #     "citas": citas,
    #     "consultas": consultas,
    #     "pagos": pagos,
    #     "diagnosticos": diagnosticos,
    #     "medicos": medicos,
    #     "ingresos": ingresos,
    # }
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


@rol_requerido("ADMIN", "RECEPCIONISTA", "MEDICO")
def reportes(request):
    return render(request,"reportes.html")