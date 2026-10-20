(function () {
    'use strict';
    const buscar = document.getElementById('pago-paciente-buscar');
    const oculto = document.getElementById('id_paciente');
    const lista = document.getElementById('pago-paciente-resultados');
    if (!buscar || !oculto || !lista) return;

    let timer;

    function elegir(p) {
        buscar.value = p.texto;
        oculto.value = p.id;
        lista.hidden = true;
    }

    buscar.addEventListener('input', () => {
        oculto.value = '';                       // si cambia el texto, invalida la selección
        clearTimeout(timer);
        const q = buscar.value.trim();
        if (q.length < 2) { lista.hidden = true; return; }

        timer = setTimeout(async () => {
            try {
                const r = await fetch(buscar.dataset.urlBuscar + '?q=' + encodeURIComponent(q));
                if (!r.ok) throw new Error('HTTP ' + r.status);
                const { resultados } = await r.json();

                lista.innerHTML = '';
                resultados.forEach((p) => {
                    const li = document.createElement('li');
                    li.textContent = p.texto;
                    li.style.cssText = 'padding:6px 10px;cursor:pointer';
                    li.addEventListener('click', () => elegir(p));
                    lista.appendChild(li);
                });
                if (!resultados.length) {
                    const li = document.createElement('li');
                    li.textContent = 'Sin resultados';
                    li.style.cssText = 'padding:6px 10px;color:#71858c';
                    lista.appendChild(li);
                }
                lista.hidden = false;
            } catch (e) {
                console.error('Error buscando pacientes:', e);
            }
        }, 250);
    });

    document.addEventListener('click', (e) => {
        if (e.target !== buscar && !lista.contains(e.target)) lista.hidden = true;
    });
})();

(function () {
    'use strict';
    const input = document.getElementById('filtro-paciente');
    const lista = document.getElementById('lista-pacientes');
    if (!input || !lista || !input.dataset.urlBuscar) return;
    let timer;
    input.addEventListener('input', () => {
        clearTimeout(timer);
        const q = input.value.trim();
        if (q.length < 2) { lista.innerHTML = ''; return; }
        timer = setTimeout(async () => {
            try {
                const r = await fetch(input.dataset.urlBuscar + '?q=' + encodeURIComponent(q));
                if (!r.ok) return;
                const { resultados } = await r.json();
                lista.innerHTML = '';
                resultados.forEach((p) => lista.appendChild(new Option(p.texto)));
            } catch (e) { console.error(e); }
        }, 250);
    });
})();