document.addEventListener('DOMContentLoaded', () => {
  // ELEMENTOS MODAL
  const modalCrear = document.getElementById('modal-crear');
  const btnAbrirModal = document.getElementById('btn-abrir-modal');
  const btnCancelarModal = document.getElementById('btn-cancelar-modal');

  // ELEMENTOS SIDEBAR
  const sidebar = document.getElementById('sidebar');
  const btnToggleSidebar = document.getElementById('btn-toggle-sidebar');
  const sidebarOverlay = document.getElementById('sidebar-overlay');

  // ELEMENTOS PACIENTE
  const selPaciente = document.getElementById('paciente');
  const inpSangre = document.getElementById('tipo_sangre');
  const inpEdad = document.getElementById('edad');
  const inpSexo = document.getElementById('sexo');

  // Funciones Modal
  function abrirModal() {
    if (modalCrear) modalCrear.classList.remove('hidden');
  }

  function cerrarModal() {
    if (modalCrear) modalCrear.classList.add('hidden');
  }

  // Funciones Sidebar Móvil
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

  // Listeners Modal
  if (btnAbrirModal) btnAbrirModal.addEventListener('click', abrirModal);
  if (btnCancelarModal) btnCancelarModal.addEventListener('click', cerrarModal);

  // Listeners Sidebar
  if (btnToggleSidebar) btnToggleSidebar.addEventListener('click', abrirSidebar);
  if (sidebarOverlay) sidebarOverlay.addEventListener('click', cerrarSidebar);

  // Listener Paciente
  if (selPaciente) selPaciente.addEventListener('change', rellenarPaciente);
});