document.addEventListener('DOMContentLoaded', () => {
const openRegistro = document.getElementById("openRegistro");
const resgistroModal = document.getElementById("resgistroModal");
const cancelRegistModal = document.getElementById("cancelRegistModal");

const sidebar = document.getElementById('menu-lateral');
const btnToggleSidebar = document.getElementById('btn-toggle-sidebar');
const sidebarOverlay = document.getElementById('menu-overlay');

const toggleModal = (show) => {
    if (resgistroModal) {
        resgistroModal.classList.toggle("active", show);
    }
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

openRegistro?.addEventListener("click", ()=> toggleModal(true));
cancelRegistModal?.addEventListener("click", ()=> toggleModal(false));
if (btnToggleSidebar) btnToggleSidebar.addEventListener('click', abrirSidebar);
if (sidebarOverlay) sidebarOverlay.addEventListener('click', cerrarSidebar);
});