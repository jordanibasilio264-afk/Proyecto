document.addEventListener('DOMContentLoaded', () => {
  const modalCrear = document.getElementById('modal-crear');
  const btnAbrirModal = document.getElementById('btn-abrir-modal');
  const btnCancelarModal = document.getElementById('btn-cancelar-modal');

  const sidebar = document.getElementById('sidebar');
  const btnToggleSidebar = document.getElementById('btn-toggle-sidebar');
  const sidebarOverlay = document.getElementById('sidebar-overlay');

  function abrirModal() {
    if (modalCrear) modalCrear.classList.remove('hidden');
  }

  function cerrarModal() {
    if (modalCrear) modalCrear.classList.add('hidden');
  }

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

  if (btnAbrirModal) btnAbrirModal.addEventListener('click', abrirModal);
  if (btnCancelarModal) btnCancelarModal.addEventListener('click', cerrarModal);

  if (btnToggleSidebar) btnToggleSidebar.addEventListener('click', abrirSidebar);
  if (sidebarOverlay) sidebarOverlay.addEventListener('click', cerrarSidebar);
});