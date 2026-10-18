(function () {
    'use strict';

    var tabla = document.getElementById('pagos-tabla');
    if (!tabla) return;

    var filas = Array.prototype.slice.call(tabla.querySelectorAll('tbody tr'));
    var formulario = document.getElementById('pagos-tabla-filtros');
    var inputPaciente = document.getElementById('filtro-paciente');
    var selectEstado = document.getElementById('filtro-estado');
    var selectMetodo = document.getElementById('filtro-metodo');
    var selectPorPagina = document.getElementById('pagos-por-pagina');
    var contenedorBotones = document.getElementById('pagos-paginacion-botones');
    var info = document.getElementById('pagos-info');
    var sinResultados = document.getElementById('pagos-sin-resultados');

    var paginaActual = 1;
    var filtradas = filas.slice();

    // Quita tildes y pasa a minúsculas: "María" coincide con "maria"
    function normalizar(texto) {
        return (texto || '')
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .toLowerCase()
            .trim();
    }

    // Cada palabra escrita debe ser una palabra COMPLETA del nombre.
    // "maria" encuentra "María Rodríguez" y "Ana María", pero no "Mariano" ni "Mariana".
    function coincidePalabras(nombre, busqueda) {
        if (!busqueda) return true;
        var palabrasNombre = normalizar(nombre).split(/\s+/);
        return busqueda.split(/\s+/).every(function (palabra) {
            return palabrasNombre.indexOf(palabra) !== -1;
        });
    }

    function aplicarFiltros() {
        var paciente = normalizar(inputPaciente.value);
        var estado = normalizar(selectEstado.value);
        var metodo = normalizar(selectMetodo.value);

        filtradas = filas.filter(function (fila) {
            var celdas = fila.cells;
            var coincidePaciente = coincidePalabras(celdas[0].textContent, paciente);
            var coincideMetodo = !metodo || normalizar(celdas[2].textContent) === metodo;
            var coincideEstado = !estado || normalizar(celdas[4].textContent) === estado;
            return coincidePaciente && coincideMetodo && coincideEstado;
        });

        paginaActual = 1;
        render();
    }

    function crearBoton(texto, pagina, opciones) {
        var boton = document.createElement('button');
        boton.type = 'button';
        boton.className = 'pagos-pag-btn';
        boton.textContent = texto;
        opciones = opciones || {};

        if (opciones.activo) {
            boton.classList.add('activo');
            boton.setAttribute('aria-current', 'page');
        }
        if (opciones.deshabilitado) {
            boton.disabled = true;
        }
        if (opciones.etiqueta) {
            boton.setAttribute('aria-label', opciones.etiqueta);
        }

        boton.addEventListener('click', function () {
            paginaActual = pagina;
            render();
        });
        return boton;
    }

    function crearPuntos() {
        var span = document.createElement('span');
        span.className = 'pagos-pag-puntos';
        span.textContent = '…';
        return span;
    }

    // Muestra: 1 … actual-1 actual actual+1 … última
    function numerosVisibles(total, actual) {
        var paginas = [];
        for (var i = 1; i <= total; i++) {
            if (i === 1 || i === total || Math.abs(i - actual) <= 1) {
                paginas.push(i);
            }
        }
        return paginas;
    }

    function dibujarBotones(totalPaginas) {
        contenedorBotones.innerHTML = '';

        contenedorBotones.appendChild(
            crearBoton('‹ Anterior', paginaActual - 1, {
                deshabilitado: paginaActual === 1,
                etiqueta: 'Página anterior'
            })
        );

        var anterior = 0;
        numerosVisibles(totalPaginas, paginaActual).forEach(function (numero) {
            if (anterior && numero - anterior > 1) {
                contenedorBotones.appendChild(crearPuntos());
            }
            contenedorBotones.appendChild(
                crearBoton(String(numero), numero, {
                    activo: numero === paginaActual,
                    etiqueta: 'Página ' + numero
                })
            );
            anterior = numero;
        });

        contenedorBotones.appendChild(
            crearBoton('Siguiente ›', paginaActual + 1, {
                deshabilitado: paginaActual === totalPaginas,
                etiqueta: 'Página siguiente'
            })
        );
    }

    function render() {
        var porPagina = parseInt(selectPorPagina.value, 10) || 5;
        var total = filtradas.length;
        var totalPaginas = Math.max(1, Math.ceil(total / porPagina));

        if (paginaActual > totalPaginas) paginaActual = totalPaginas;
        if (paginaActual < 1) paginaActual = 1;

        var inicio = (paginaActual - 1) * porPagina;
        var fin = Math.min(inicio + porPagina, total);

        filas.forEach(function (fila) {
            fila.hidden = true;
        });
        filtradas.slice(inicio, fin).forEach(function (fila) {
            fila.hidden = false;
        });

        if (total === 0) {
            info.textContent = 'Mostrando 0 de 0 pagos';
        } else {
            info.textContent = 'Mostrando ' + (inicio + 1) + '–' + fin + ' de ' + total + ' pagos';
        }

        sinResultados.hidden = total !== 0;
        tabla.parentElement.hidden = total === 0;
        contenedorBotones.hidden = total === 0;

        dibujarBotones(totalPaginas);
    }

    // Eventos
    formulario.addEventListener('submit', function (evento) {
        evento.preventDefault();
        aplicarFiltros();
    });

    // El reset limpia los campos; esperamos a que se vacíen antes de filtrar
    formulario.addEventListener('reset', function () {
        setTimeout(aplicarFiltros, 0);
    });

    // El filtro se aplica solo al presionar "Filtrar" (o Enter)

    selectPorPagina.addEventListener('change', function () {
        paginaActual = 1;
        render();
    });

    render();
})();
