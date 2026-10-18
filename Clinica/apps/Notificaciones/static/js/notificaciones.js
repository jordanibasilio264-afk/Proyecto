(function () {
    'use strict';

    // Botón "Notificaciones automáticas": activar / desactivar
    var boton = document.getElementById('notif-auto-btn');
    if (boton) {
        boton.addEventListener('click', function () {
            var activo = boton.getAttribute('aria-pressed') !== 'true';
            boton.setAttribute('aria-pressed', String(activo));
            boton.textContent = activo ? '✓ Activadas' : 'Desactivadas';
        });
    }

    // La fecha de la cita no puede ser anterior a hoy
    var fecha = document.getElementById('notif-fecha');
    if (fecha) {
        var hoy = new Date();
        var mes = String(hoy.getMonth() + 1).padStart(2, '0');
        var dia = String(hoy.getDate()).padStart(2, '0');
        fecha.min = hoy.getFullYear() + '-' + mes + '-' + dia;
    }
})();
