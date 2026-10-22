/* static/js/auditoria.js
   - Mantiene coherente el período (Hasta >= Desde)
   - Envía el formulario al cambiar la acción
   - No envía campos vacíos (URL limpia: ?accion=EDITAR&desde=...) */
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('filtros-auditoria');
    if (!form) return;
    const { desde, hasta, accion } = form.elements;

    const sincronizar = () => {
        hasta.min = desde.value;
        desde.max = hasta.value;
    };
    desde.addEventListener('change', sincronizar);
    hasta.addEventListener('change', sincronizar);
    sincronizar();

    accion.addEventListener('change', () => form.requestSubmit());

    form.addEventListener('formdata', e => {
        [...e.formData].forEach(([clave, valor]) => {
            if (valor === '') e.formData.delete(clave);
        });
    });
});
