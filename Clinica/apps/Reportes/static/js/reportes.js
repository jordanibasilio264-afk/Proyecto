/* ==========================================================
   reportes.js  ·  static/js/reportes.js
   - Valida el período (Desde / Hasta)
   - Filtra las tarjetas según el tipo de reporte
   - Guarda el filtro en la URL (?tipo=&desde=&hasta=)
   - Botones PDF / Excel (por tarjeta y en "Exportar Reportes")
   - Avisos (toast) en lugar de alert()
   ========================================================== */
document.addEventListener('DOMContentLoaded', () => {
    'use strict';

    /* Ruta base de descarga. Ajústala a tu urls.py:
       /reportes/exportar/<tipo>/<pdf|excel>/?desde=AAAA-MM-DD&hasta=AAAA-MM-DD */
    const URL_EXPORTAR = '/reportes/exportar/';

    const selTipo  = document.getElementById('tipo-reporte');
    const inpDesde = document.getElementById('fecha-desde');
    const inpHasta = document.getElementById('fecha-hasta');
    const btnConsultar = document.getElementById('btn-consultar');
    const tarjetas = document.querySelector('.tarjetas');
    const cards = [...document.querySelectorAll('.tarjeta')];
    const subtitulo = document.querySelector('.zona-reportes .titulo p');
    const textoSubtitulo = subtitulo.textContent;

    /* ---------- Utilidades ---------- */
    const dosDigitos = n => String(n).padStart(2, '0');
    const aISO = d => `${d.getFullYear()}-${dosDigitos(d.getMonth() + 1)}-${dosDigitos(d.getDate())}`;
    const aLatino = iso => iso ? iso.split('-').reverse().join('/') : '';
    const nombreTipo = valor => selTipo.querySelector(`option[value="${valor}"]`)?.textContent.trim() || valor;

    function toast(mensaje, tipo = 'ok') {
        let contenedor = document.querySelector('.toast-contenedor');
        if (!contenedor) {
            contenedor = document.createElement('div');
            contenedor.className = 'toast-contenedor';
            contenedor.setAttribute('role', 'status');
            contenedor.setAttribute('aria-live', 'polite');
            document.body.appendChild(contenedor);
        }
        const el = document.createElement('div');
        el.className = `toast toast-${tipo}`;
        el.textContent = mensaje;
        contenedor.appendChild(el);
        setTimeout(() => {
            el.classList.add('saliendo');
            el.addEventListener('animationend', () => el.remove(), { once: true });
        }, 3200);
    }

    /* ---------- Estado inicial (URL o valores por defecto) ---------- */
    const params = new URLSearchParams(window.location.search);
    const hoy = new Date();
    const primerDia = new Date(hoy.getFullYear(), hoy.getMonth(), 1);

    const tipoInicial = params.get('tipo');
    selTipo.value = selTipo.querySelector(`option[value="${tipoInicial}"]`) ? tipoInicial : 'todos';
    inpDesde.value = params.get('desde') ?? aISO(primerDia);
    inpHasta.value = params.get('hasta') ?? aISO(hoy);

    const periodoCargado = { desde: inpDesde.value, hasta: inpHasta.value };

    /* ---------- Período ---------- */
    function sincronizarLimites() {
        inpHasta.min = inpDesde.value || '';
        inpDesde.max = inpHasta.value || '';
        inpDesde.classList.remove('invalido');
        inpHasta.classList.remove('invalido');
    }

    function periodoValido() {
        if (inpDesde.value && inpHasta.value && inpDesde.value > inpHasta.value) {
            inpDesde.classList.add('invalido');
            inpHasta.classList.add('invalido');
            toast('La fecha "Desde" no puede ser mayor que "Hasta".', 'error');
            return false;
        }
        return true;
    }

    inpDesde.addEventListener('change', sincronizarLimites);
    inpHasta.addEventListener('change', sincronizarLimites);
    sincronizarLimites();

    /* ---------- Filtro de tarjetas ---------- */
    function aplicarFiltro() {
        const tipo = selTipo.value;
        let visibles = 0;

        cards.forEach(card => {
            const mostrar = tipo === 'todos' || card.dataset.tipo === tipo;
            card.hidden = !mostrar;
            if (mostrar) visibles++;
        });

        tarjetas.classList.toggle('una-sola', visibles === 1);

        const periodo = (inpDesde.value || inpHasta.value)
            ? ` · ${aLatino(inpDesde.value) || '…'} – ${aLatino(inpHasta.value) || '…'}`
            : '';
        subtitulo.textContent = tipo === 'todos'
            ? textoSubtitulo + periodo
            : `Mostrando: Reporte de ${nombreTipo(tipo)}${periodo}`;
    }

    function consultar() {
        if (!periodoValido()) return;

        const nuevos = new URLSearchParams({ tipo: selTipo.value });
        if (inpDesde.value) nuevos.set('desde', inpDesde.value);
        if (inpHasta.value) nuevos.set('hasta', inpHasta.value);

        const cambioPeriodo = inpDesde.value !== periodoCargado.desde
                           || inpHasta.value !== periodoCargado.hasta;

        if (cambioPeriodo) {
            /* El período cambió: recarga para que la vista de Django
               recalcule los totales leyendo request.GET */
            window.location.search = nuevos.toString();
            return;
        }

        history.replaceState(null, '', `?${nuevos}`);
        aplicarFiltro();
        toast('Consulta aplicada.');
    }

    btnConsultar.addEventListener('click', consultar);
    [selTipo, inpDesde, inpHasta].forEach(el =>
        el.addEventListener('keydown', e => { if (e.key === 'Enter') consultar(); })
    );

    /* ---------- Exportar PDF / Excel ---------- */
    function exportar(tipo, formato, boton) {
        if (!periodoValido()) return;

        const query = new URLSearchParams();
        if (inpDesde.value) query.set('desde', inpDesde.value);
        if (inpHasta.value) query.set('hasta', inpHasta.value);

        const enlace = document.createElement('a');
        enlace.href = `${URL_EXPORTAR}${tipo}/${formato}/?${query}`;
        enlace.download = '';
        document.body.appendChild(enlace);
        enlace.click();
        enlace.remove();

        toast(`Generando reporte de ${nombreTipo(tipo)} en ${formato === 'pdf' ? 'PDF' : 'Excel'}…`);

        /* Evita dobles clics mientras se genera */
        const textoOriginal = boton.textContent;
        boton.disabled = true;
        boton.textContent = '…';
        setTimeout(() => {
            boton.disabled = false;
            boton.textContent = textoOriginal;
        }, 1500);
    }

    document.addEventListener('click', e => {
        const boton = e.target.closest('button');
        if (!boton) return;

        /* Botones dentro de cada tarjeta */
        const card = boton.closest('.tarjeta');
        if (card && (boton.classList.contains('pdf') || boton.classList.contains('excel'))) {
            exportar(card.dataset.tipo, boton.classList.contains('pdf') ? 'pdf' : 'excel', boton);
            return;
        }

        /* Botones de la sección "Exportar Reportes" */
        if (boton.classList.contains('boton-pdf') || boton.classList.contains('boton-excel')) {
            if (selTipo.value === 'todos') {
                toast('Elige un tipo de reporte para descargarlo.', 'aviso');
                selTipo.focus();
                return;
            }
            exportar(selTipo.value, boton.classList.contains('boton-pdf') ? 'pdf' : 'excel', boton);
        }
    });

    aplicarFiltro();
});
