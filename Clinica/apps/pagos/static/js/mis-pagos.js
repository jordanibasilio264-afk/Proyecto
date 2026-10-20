(function () {
    'use strict';

    const CLINICA = 'Clínica Médica General y Familiar';

    const tabla = document.getElementById('pagos-tabla');
    const datos = document.getElementById('mis-pagos-datos');
    if (!tabla) return;

    const paciente = datos ? datos.dataset.paciente : '';

    function esc(texto) {
        const div = document.createElement('div');
        div.textContent = texto || '';
        return div.innerHTML;
    }

    function hoy() {
        const d = new Date();
        const dia = String(d.getDate()).padStart(2, '0');
        const mes = String(d.getMonth() + 1).padStart(2, '0');
        return dia + '/' + mes + '/' + d.getFullYear();
    }

    function imprimirRecibo(fila) {
        const d = fila.dataset;

        const html = `<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><title>Recibo ${esc(d.recibo)}</title>
<style>
    * { box-sizing: border-box; }
    body { font-family: Arial, sans-serif; color: #123b5a; margin: 0; }
    .recibo { max-width: 560px; margin: 0 auto; padding: 40px 30px; }
    h1 { font-size: 20px; color: #075875; margin: 0 0 4px; text-align: center; }
    h2 { font-size: 16px; margin: 0; text-align: center; color: #07838a; }
    .numero { text-align: center; color: #71858c; font-size: 12px; margin: 8px 0 26px; }
    table { width: 100%; border-collapse: collapse; }
    th, td { text-align: left; padding: 10px 6px; border-bottom: 1px solid #e3eef0; font-size: 14px; }
    th { color: #71858c; font-weight: normal; width: 45%; }
    .total { font-size: 16px; text-align: right; margin: 22px 0 60px; }
    .total strong { font-size: 24px; color: #075875; }
    .firma { width: 220px; border-top: 1px solid #123b5a; text-align: center; padding-top: 6px; font-size: 12px; margin: 0 auto; }
    .gracias { text-align: center; color: #71858c; font-size: 12px; margin-top: 28px; }
</style></head><body>
<section class="recibo">
    <h1>${esc(CLINICA)}</h1>
    <h2>Recibo de pago</h2>
    <p class="numero">${esc(d.recibo)} · Emitido el ${hoy()}</p>
    <table>
        <tr><th>Paciente</th><td>${esc(paciente)}</td></tr>
        <tr><th>Concepto</th><td>${esc(d.concepto)}</td></tr>
        <tr><th>Fecha del pago</th><td>${esc(d.fecha)}</td></tr>
        <tr><th>Método de pago</th><td>${esc(d.metodo)}</td></tr>
        <tr><th>Total</th><td>${esc(d.total)}</td></tr>
        <tr><th>Cubierto por el seguro</th><td>${esc(d.seguro)}</td></tr>
    </table>
    <p class="total">Total pagado por el paciente: <strong>${esc(d.tuparte)}</strong></p>
    <div class="firma">Firma y sello</div>
    <p class="gracias">Gracias por su pago.</p>
</section></body></html>`;

        const viejo = document.querySelector('iframe.pagos-impresion');
        if (viejo) viejo.remove();

        const marco = document.createElement('iframe');
        marco.className = 'pagos-impresion';
        marco.setAttribute('aria-hidden', 'true');
        marco.style.cssText = 'position:fixed;right:0;bottom:0;width:0;height:0;border:0;';
        marco.onload = function () {
            marco.contentWindow.focus();
            marco.contentWindow.print();
        };
        marco.srcdoc = html;
        document.body.appendChild(marco);
    }

    tabla.addEventListener('click', function (evento) {
        const boton = evento.target.closest('.pagos-boton-recibo');
        if (!boton) return;
        const fila = boton.closest('tr');
        if (fila && fila.dataset.estado === 'pagado') imprimirRecibo(fila);
    });
})();