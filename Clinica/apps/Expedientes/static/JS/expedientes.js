document.addEventListener('DOMContentLoaded', () => {
  // MODAL
  const modalCrear = document.getElementById('modal-crear');
  const btnAbrirModal = document.getElementById('btn-abrir-modal');
  const btnCancelarModal = document.getElementById('btn-cancelar-modal');

  // SIDEBAR
  const sidebar = document.getElementById('sidebar');
  const btnToggleSidebar = document.getElementById('btn-toggle-sidebar');
  const sidebarOverlay = document.getElementById('sidebar-overlay');

  // PACIENTE
  const inpPaciente = document.getElementById('paciente_input');
  const hiddenId = document.getElementById('paciente_id');
  const lista = document.getElementById('pacientes-lista');

  // campo del formulario -> atributo data-* del <option>
  const campos = {
    fecha_nacimiento: 'nacimiento',
    sexo: 'sexo',
    tipo_sangre: 'sangre',
    cedula: 'cedula',
    telefono: 'telefono',
    direccion: 'direccion',
    nombre_contacto: 'contacto',
    telefono_contacto: 'telContacto',
  };

  const abrirModal = () => modalCrear && modalCrear.classList.remove('hidden');
  const cerrarModal = () => modalCrear && modalCrear.classList.add('hidden');

  function abrirSidebar() {
    if (sidebar && sidebarOverlay) {
      sidebar.classList.add('active');
      sidebarOverlay.classList.add('active');
    }
  }

  function cerrarSidebar() {
    if (sidebar && sidebarOverlay) {
      sidebar.classList.remove('active');
      sidebarOverlay.classList.remove('active');
    }
  }

  function rellenarPaciente() {
    const opt = [...lista.options].find(o => o.value === inpPaciente.value);
    hiddenId.value = opt ? opt.dataset.id : '';
    if (!opt) return;

    for (const [idCampo, dataKey] of Object.entries(campos)) {
      const el = document.getElementById(idCampo);
      if (el) el.value = opt.dataset[dataKey] || '';
    }
  }

  // Modal
  if (btnAbrirModal) btnAbrirModal.addEventListener('click', abrirModal);
  if (btnCancelarModal) btnCancelarModal.addEventListener('click', cerrarModal);
  if (modalCrear) {
    modalCrear.addEventListener('click', e => {
      if (e.target === modalCrear) cerrarModal();
    });
  }

  // Sidebar
  if (btnToggleSidebar) btnToggleSidebar.addEventListener('click', abrirSidebar);
  if (sidebarOverlay) sidebarOverlay.addEventListener('click', cerrarSidebar);

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