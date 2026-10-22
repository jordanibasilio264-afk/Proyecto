(function () {
    var rol = document.getElementById("id_rol");
    var campos = {
        id_especialidad: "MEDICO", id_exequatur: "MEDICO",
        id_consultorio: "MEDICO", id_duracion_cita_minutos: "MEDICO",
        id_fecha_nacimiento: "PACIENTE", id_sexo: "PACIENTE",
        id_tipo_sangre: "PACIENTE", id_direccion: "PACIENTE",
        id_contacto_emergencia_nombre: "PACIENTE",
        id_contacto_emergencia_telefono: "PACIENTE",
        id_hora_inicio: "MEDICO", id_hora_fin: "MEDICO",
    };
    function actualizar() {
        for (var id in campos) {
            var el = document.getElementById(id);
            if (el) el.closest(".campo").style.display = rol.value === campos[id] ? "" : "none";
        }
        document.getElementById("bloque-dias").style.display = rol.value === "MEDICO" ? "" : "none";
        document.getElementById("fila-medico-activo").style.display = rol.value === "MEDICO" ? "" : "none";
        document.getElementById("fila-paciente-activo").style.display = rol.value === "PACIENTE" ? "" : "none";
    }
    rol.addEventListener("change", actualizar);
    actualizar();
})();