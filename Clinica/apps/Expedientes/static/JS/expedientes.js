document.addEventListener('DOMContentLoaded', () => {

  // PACIENTE
  const inpPaciente = document.getElementById('paciente_input');
  const hiddenId = document.getElementById('paciente_id');
  const lista = document.getElementById('pacientes-lista');
  const inpSangre = document.getElementById('tipo_sangre');
  const inpNacimiento = document.getElementById('fecha_nacimiento');
  const inpSexo = document.getElementById('sexo');

  function rellenarPaciente() {
    const opt = [...lista.options].find(o => o.value === inpPaciente.value);
    hiddenId.value = opt ? opt.dataset.id : '';
    if (opt) {
      inpNacimiento.value = opt.dataset.nacimiento || '';
      inpSexo.value = opt.dataset.sexo || '';
      inpSangre.value = opt.dataset.sangre || '';
    }
  }

  // Paciente
  if (inpPaciente) {
    inpPaciente.addEventListener('input', rellenarPaciente);
    inpPaciente.form.addEventListener('submit', e => {
      if (!hiddenId.value) {
        e.preventDefault();
        alert('Seleccione un paciente de la lista.');
      }
    });
  }
});