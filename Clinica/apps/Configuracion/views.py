from django.http import Http404
from django.shortcuts import redirect, render

# Qué plantilla se muestra para cada rol
PLANTILLAS = {
    'administrador': 'configuracion_administrador.html',
    'medico': 'configuracion_medico.html',
    'recepcionista': 'configuracion_recepcionista.html',
    'cliente': 'configuracion_cliente.html',
}


def obtener_rol(request):
    """
    Devuelve el rol de quien está viendo la página.

    POR AHORA (sin base de datos) siempre es 'administrador'; para ver los
    otros roles se entra por la URL: /configuracion/medico/, etc.

    CUANDO TENGAS LA BASE DE DATOS, solo cambia esta función. Por ejemplo:
        return request.user.rol                    # si tu usuario tiene un campo "rol"
        return request.user.groups.first().name    # si usas los grupos de Django
    """
    return 'administrador'


def configuracion(request, rol=None):
    # Si la URL trae el rol (/configuracion/medico/) se usa ese; si no, el del usuario
    rol = rol or obtener_rol(request)

    if rol not in PLANTILLAS:
        raise Http404('Ese rol no existe.')

    # Los botones "Guardar" todavía no guardan nada (no hay base de datos):
    # solo vuelven a la página para que el navegador no pida "reenviar el formulario".
    if request.method == 'POST':
        return redirect(request.path)

    return render(request, PLANTILLAS[rol], {'rol': rol})