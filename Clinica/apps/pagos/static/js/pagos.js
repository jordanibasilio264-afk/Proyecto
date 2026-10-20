/* =========================================================
   pagos.js — Interactividad de la página de Pagos
   Funciona SIN base de datos (modo demostración).
========================================================= */
(function () {
    'use strict';

    /* =====================================================
       CONFIGURACIÓN
       true  = modo demostración: los pagos nuevos se agregan solo
               en esta página (al recargar se pierden).
       false = cuando tengas la base de datos: el JavaScript solo
               valida, y Django guarda, filtra y calcula.
    ===================================================== */
    const MODO_DEMO = false;

    const CLINICA = 'Clínica Médica General y Familiar';

    /* ---------- Atajos ---------- */
    const $ = (selector, contexto = document) => contexto.querySelector(selector);
    const $$ = (selector, contexto = document) => Array.from(contexto.querySelectorAll(selector));

    const campoPaciente = $('#id_paciente');
    const campoMonto = $('#id_monto');
    const campoBuscar   = $('#pago-paciente-buscar');
    const campoFecha = $('#id_fecha_pago');
    const campoMetodo = $('#id_metodo');
    const campoDesde = $('#pagos-desde');
    const campoHasta = $('#pagos-hasta');
    const tbody = $('.pagos-tabla tbody');

    // Si falta algo de la página, no hacemos nada (así no se rompe)
    if (!campoPaciente || !campoBuscar || !campoMonto || !campoFecha || !campoMetodo ||
        !campoDesde || !campoHasta || !tbody) {
        return;
    }

    const formPago = campoPaciente.closest('form');
    const formFiltro = campoDesde.closest('form');

    // Los mensajes de error los mostramos nosotros, no el navegador
    formPago.noValidate = true;
    formFiltro.noValidate = true;


    /* =====================================================
       FECHAS Y DINERO
    ===================================================== */

    // Fecha de hoy en formato AAAA-MM-DD (usando la hora local)
    function hoyISO() {
        const d = new Date();
        const mes = String(d.getMonth() + 1).padStart(2, '0');
        const dia = String(d.getDate()).padStart(2, '0');
        return `${d.getFullYear()}-${mes}-${dia}`;
    }

    // 2026-08-20  ->  20/08/2026
    function isoADisplay(iso) {
        const [a, m, d] = iso.split('-');
        return `${d}/${m}/${a}`;
    }

    // 20/08/2026  ->  2026-08-20
    function displayAISO(texto) {
        const [d, m, a] = texto.trim().split('/');
        return `${a}-${m.padStart(2, '0')}-${d.padStart(2, '0')}`;
    }

    // 1500 -> RD$1,500.00
    function dinero(numero) {
        return 'RD$' + numero.toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    // "RD$1,500.00" -> 1500
    function textoANumero(texto) {
        return parseFloat(texto.replace(/[^0-9.]/g, '')) || 0;
    }

    // Evita que un texto raro se interprete como HTML
    function esc(texto) {
        const div = document.createElement('div');
        div.textContent = texto;
        return div.innerHTML;
    }


    /* =====================================================
       MENSAJES Y ERRORES
    ===================================================== */
    let temporizadorMensaje;

    // tipo: 'exito' | 'error' | 'aviso' | 'info'
    function mensaje(texto, tipo = 'exito') {
        let caja = $('.pagos-mensaje');

        if (!caja) {
            caja = document.createElement('div');
            caja.setAttribute('role', 'status');
            caja.setAttribute('aria-live', 'polite');
            $('.pagos-encabezado').insertAdjacentElement('afterend', caja);
        }

        caja.className = `pagos-mensaje pagos-mensaje-${tipo}`;
        caja.textContent = texto;
        caja.style.display = 'block';

        clearTimeout(temporizadorMensaje);
        temporizadorMensaje = setTimeout(() => { caja.style.display = 'none'; }, 7000);
    }

    function errorCampo(campo, texto) {
        const contenedor = campo.closest('.pagos-campo');
        contenedor.classList.add('pagos-campo-error');
        campo.setAttribute('aria-invalid', 'true');

        let aviso = $('.pagos-error-texto', contenedor);
        if (!aviso) {
            aviso = document.createElement('small');
            aviso.className = 'pagos-error-texto';
            contenedor.appendChild(aviso);
        }
        aviso.textContent = texto;
    }

    function limpiarError(campo) {
        const contenedor = campo.closest('.pagos-campo');
        contenedor.classList.remove('pagos-campo-error');
        campo.removeAttribute('aria-invalid');
        const aviso = $('.pagos-error-texto', contenedor);
        if (aviso) aviso.remove();
    }

    // En cuanto el usuario corrige un campo, se quita su error
    [campoPaciente,campoBuscar ,campoMonto, campoFecha, campoMetodo, campoDesde, campoHasta].forEach((campo) => {
        campo.addEventListener('input', () => limpiarError(campo));
        campo.addEventListener('change', () => limpiarError(campo));
    });


    /* =====================================================
       LA TABLA DE PAGOS
       Cada fila guarda sus datos en atributos data-*,
       leídos del propio HTML (así funciona igual con filas
       escritas a mano o generadas por Django).
    ===================================================== */
    let siguienteId = 1;

    function prepararFila(fila) {
        const celdas = fila.cells;
        if (celdas.length < 6) return;

        const estado = celdas[4].textContent.trim().toLowerCase();

        fila.dataset.id = siguienteId++;
        fila.dataset.fecha = displayAISO(celdas[1].textContent);
        fila.dataset.monto = fila.dataset.monto || textoANumero(celdas[3].textContent);
        fila.dataset.estado = estado === 'pagado' ? 'pagado' : 'pendiente';

        // En modo demostración, un pago pendiente se puede marcar como pagado
        if (MODO_DEMO && fila.dataset.estado === 'pendiente') {
            const etiqueta = $('.pagos-estado', fila);
            etiqueta.title = 'Clic para marcar como pagado';
            etiqueta.tabIndex = 0;
        }
    }

    function filasPagos() {
        return $$('tr', tbody).filter((fila) => fila.dataset.id);
    }

    function datosDeFila(fila) {
        const c = fila.cells;
        return {
            id: Number(fila.dataset.id),
            paciente: c[0].textContent.trim(),
            fecha: c[1].textContent.trim(),
            metodo: c[2].textContent.trim(),
            monto: Number(fila.dataset.monto),
            pagado: fila.dataset.estado === 'pagado',
        };
    }

    $$('tr', tbody).forEach(prepararFila);


    /* =====================================================
       FILTRO POR FECHAS + RESUMEN
    ===================================================== */
    const filtro = { desde: '', hasta: '' };

    function setResumen(etiqueta, valor) {
        $$('.pagos-resumen-card').forEach((tarjeta) => {
            const nombre = $('.pagos-resumen-datos span', tarjeta);
            const numero = $('.pagos-resumen-datos strong', tarjeta);
            if (nombre && numero && nombre.textContent.trim().toLowerCase() === etiqueta) {
                numero.textContent = valor;
            }
        });
    }

    // Muestra solo las filas dentro del filtro y recalcula las tarjetas de resumen
    function refrescar() {
        const hoy = hoyISO();
        const todas = filasPagos();
        let visibles = 0;
        let pagosVisibles = 0;
        let ingresos = 0;

        todas.forEach((fila) => {
            const f = fila.dataset.fecha;
            const dentro = (!filtro.desde || f >= filtro.desde) && 
                    (!filtro.hasta || f <= filtro.hasta);
            fila.dataset.fuera = dentro ? '' : '1';      // en vez de style.display
            if (dentro) { visibles++;
                if (fila.dataset.estado === 'pagado') {
                    ingresos += Number(fila.dataset.monto);
                    pagosVisibles++;
                }
            }
        });

        // Fila "no hay pagos"
        

        setResumen('total de pagos', todas.length);
        setResumen('pagos de hoy', todas.filter((f) => f.dataset.fecha === hoy).length);
        setResumen('pendientes', todas.filter((f) => f.dataset.estado === 'pendiente').length);
        setResumen('ingresos', dinero(ingresos));

        document.dispatchEvent(new Event('pagos:actualizado'));
        return { visibles, pagosVisibles, ingresos };
    }


    /* =====================================================
       FORMULARIO: REGISTRAR PAGO
    ===================================================== */


    // Al salir del campo, el monto queda con 2 decimales (1500 -> 1500.00)
    campoMonto.addEventListener('blur', () => {
        const valor = parseFloat(campoMonto.value);
        if (!isNaN(valor) && valor > 0) campoMonto.value = valor.toFixed(2);
    });

    function validarPago() {
        let primero = null;
        const fallo = (campo, texto) => {
            errorCampo(campo, texto);
            if (!primero) primero = campo;
        };

        if (!campoPaciente.value) fallo(campoBuscar, 'Elige un paciente de la lista.');

        const monto = parseFloat(campoMonto.value);
        if (!campoMonto.value || isNaN(monto) || monto <= 0) {
            fallo(campoMonto, 'Monto mayor que 0.');
        } else if (monto > 999999.99) {
            fallo(campoMonto, 'Monto demasiado alto.');
        }

        if (!campoFecha.value) {
            fallo(campoFecha, 'Elige la fecha.');
        } else if (campoFecha.value.slice(0, 10) > hoyISO()) {
            fallo(campoFecha, 'Fecha futura no permitida.');
        }

        if (!campoMetodo.value) fallo(campoMetodo, 'Elige el método.');

        if (primero) {
            primero.focus();
            return false;
        }
        return true;
    }

    function agregarPago() {
        const metodo = campoMetodo.options[campoMetodo.selectedIndex].text;
        const monto = Math.round(parseFloat(campoMonto.value) * 100) / 100;
        const nombre = campoBuscar.value.trim();

        const fila = document.createElement('tr');
        fila.innerHTML =
            `<td>${esc(nombre)}</td>` +
            `<td>${isoADisplay(campoFecha.value)}</td>` +
            `<td>${esc(metodo)}</td>` +
            `<td>${dinero(monto)}</td>` +
            `<td><span class="pagos-estado pagado">Pagado</span></td>` +
            `<td><button class="pagos-boton-recibo" type="button">PDF</button></td>`;

        tbody.appendChild(fila);
        prepararFila(fila);

        // Se quita el filtro para que el pago nuevo siempre se vea
        filtro.desde = '';
        filtro.hasta = '';
        campoDesde.value = '';
        campoHasta.value = '';
        refrescar();

        fila.classList.add('pagos-fila-nueva');
        fila.scrollIntoView({ behavior: 'smooth', block: 'center' });
        setTimeout(() => fila.classList.remove('pagos-fila-nueva'), 2600);
        

        mensaje(`Pago de ${dinero(monto)} registrado para ${nombre}.`, 'exito');
    }

    formPago.addEventListener('submit', (evento) => {
        if (!validarPago()) {
            evento.preventDefault();
            return;
        }

        if (MODO_DEMO) {
            evento.preventDefault();
            agregarPago();
            const selCita = $('#id_cita'), selSeguro = $('#id_seguro_paciente');
            [selCita, selSeguro].forEach(s => { if (s) s.innerHTML = '<option value="">---------</option>'; });
            formPago.reset();
            campoFecha.value = hoyISO();
        }
        // Si MODO_DEMO es false, el formulario se envía normalmente a Django
    });


    /* =====================================================
       FORMULARIO: CONSULTAR INGRESOS
    ===================================================== */
    formFiltro.addEventListener('submit', (evento) => {
        const desde = campoDesde.value;
        const hasta = campoHasta.value;

        if (desde && hasta && desde > hasta) {
            evento.preventDefault();
            errorCampo(campoHasta, 'No puede ser antes de "Desde".');
            campoHasta.focus();
            return;
        }

        if (!MODO_DEMO) return; // Django hará la consulta

        evento.preventDefault();
        filtro.desde = desde;
        filtro.hasta = hasta;
        const r = refrescar();

        const cantidad = r.pagosVisibles === 1 ? '1 pago pagado' : `${r.pagosVisibles} pagos pagados`;
        let periodo = 'Todos los pagos';
        if (desde && hasta) periodo = `Del ${isoADisplay(desde)} al ${isoADisplay(hasta)}`;
        else if (desde) periodo = `Desde el ${isoADisplay(desde)}`;
        else if (hasta) periodo = `Hasta el ${isoADisplay(hasta)}`;

        mensaje(`${periodo}: ${dinero(r.ingresos)} en ingresos (${cantidad}).`, 'info');
    });


    /* =====================================================
       MARCAR UN PAGO PENDIENTE COMO PAGADO (solo demostración)
    ===================================================== */
    function marcarPagado(etiqueta) {
        const fila = etiqueta.closest('tr');
        const paciente = fila.cells[0].textContent.trim();

        if (!confirm(`¿Marcar como pagado el pago de ${paciente}?`)) return;

        etiqueta.textContent = 'Pagado';
        etiqueta.className = 'pagos-estado pagado';
        etiqueta.removeAttribute('title');
        etiqueta.removeAttribute('tabindex');
        fila.dataset.estado = 'pagado';

        refrescar();
        mensaje(`El pago de ${paciente} quedó como pagado.`, 'exito');
    }

    tbody.addEventListener('click', (evento) => {
        const etiqueta = evento.target.closest('.pagos-estado.pendiente');
        if (MODO_DEMO && etiqueta) marcarPagado(etiqueta);
    });

    tbody.addEventListener('keydown', (evento) => {
        if (evento.key !== 'Enter') return;
        const etiqueta = evento.target.closest('.pagos-estado.pendiente');
        if (MODO_DEMO && etiqueta) marcarPagado(etiqueta);
    });


    /* =====================================================
       RECIBOS EN PDF
       Abre la ventana de impresión del navegador con los
       recibos; ahí se elige "Guardar como PDF".
    ===================================================== */
    function numeroRecibo(id) {
        return 'REC-' + String(id).padStart(4, '0');
    }

    function imprimirRecibos(pagos) {
        if (!pagos.length) {
            mensaje('No hay pagos pagados para generar recibos.', 'aviso');
            return;
        }

        const emitido = isoADisplay(hoyISO());

        const hojas = pagos.map((p) => `
            <section class="recibo">
                <h1>${esc(CLINICA)}</h1>
                <h2>Recibo de pago</h2>
                <p class="numero">${numeroRecibo(p.id)} · Emitido el ${emitido}</p>

                <table>
                    <tr><th>Paciente</th><td>${esc(p.paciente)}</td></tr>
                    <tr><th>Fecha del pago</th><td>${esc(p.fecha)}</td></tr>
                    <tr><th>Método de pago</th><td>${esc(p.metodo)}</td></tr>
                    <tr><th>Estado</th><td>Pagado</td></tr>
                </table>

                <p class="total">Total pagado: <strong>${dinero(p.monto)}</strong></p>

                <div class="firma">Firma y sello</div>
                <p class="gracias">Gracias por su pago.</p>
                ${MODO_DEMO ? '<p class="demo">Recibo de demostración · sin valor legal</p>' : ''}
            </section>`).join('');

        const html = `<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><title>Recibos de pago</title>
<style>
    * { box-sizing: border-box; }
    body { font-family: Arial, sans-serif; color: #123b5a; margin: 0; }
    .recibo { max-width: 560px; margin: 0 auto; padding: 40px 30px; page-break-after: always; }
    .recibo:last-child { page-break-after: auto; }
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
    .demo { text-align: center; color: #c94c4c; font-size: 11px; font-weight: bold; }
</style></head><body>${hojas}</body></html>`;

        // Se imprime desde un marco invisible (no abre ventanas emergentes)
        const viejo = $('iframe.pagos-impresion');
        if (viejo) viejo.remove();

        const marco = document.createElement('iframe');
        marco.className = 'pagos-impresion';
        marco.setAttribute('aria-hidden', 'true');
        marco.style.cssText = 'position:fixed;right:0;bottom:0;width:0;height:0;border:0;';
        marco.onload = () => {
            marco.contentWindow.focus();
            marco.contentWindow.print();
        };
        marco.srcdoc = html;
        document.body.appendChild(marco);

        mensaje('Se abrió la ventana de impresión: elige "Guardar como PDF" como destino.', 'info');
    }

    // Botón "PDF" de cada fila
    tbody.addEventListener('click', (evento) => {
        const boton = evento.target.closest('.pagos-boton-recibo');
        if (!boton) return;

        const fila = boton.closest('tr');
        if (fila.dataset.estado !== 'pagado') {
            mensaje('Este pago está pendiente: el recibo se puede generar cuando esté pagado.', 'aviso');
            return;
        }
        imprimirRecibos([datosDeFila(fila)]);
    });

    // Botón "Descargar Recibo PDF": todos los pagos pagados que se están viendo
    const botonExportar = $('.pagos-exportar button');
    if (botonExportar) {
        botonExportar.addEventListener('click', () => {
            const lista = filasPagos()
                .filter((fila) => fila.dataset.fuera !== '1' && fila.dataset.estado === 'pagado')
                .map(datosDeFila);
            imprimirRecibos(lista);
        });
    }


    /* =====================================================
       AL CARGAR LA PÁGINA
    ===================================================== */
    if (MODO_DEMO) refrescar(); // llena las tarjetas de resumen con los datos de la tabla
})();
