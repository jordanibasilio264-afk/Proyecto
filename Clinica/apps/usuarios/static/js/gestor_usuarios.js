const openUserModal = document.getElementById("openUserModal");

const userModal = document.getElementById("userModal");

const closeUserModal = document.getElementById("closeUserModal");

const cancelUserModal = document.getElementById("cancelUserModal");

const toggleModal = (show) => {
    if (userModal) {
        userModal.classList.toggle("active", show);
    }
}

openUserModal?.addEventListener("click", ()=> toggleModal(true));
closeUserModal?.addEventListener("click", ()=> toggleModal(false));
cancelUserModal?.addEventListener("click", ()=> toggleModal(false));

document.addEventListener("keydown", (event)=>{
    if(event.key == "Escape" && userModal?.classList.contains("active")){
    toggleModal(false);
    }
})

document.addEventListener('DOMContentLoaded', () => {
    const menuBtn = document.getElementById('menuBtn');
    const sidebar = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebarOverlay');

    function toggleSidebar() {
        sidebar.classList.toggle('open');
        sidebarOverlay.classList.toggle('active');
    }

    if (menuBtn) {
        menuBtn.addEventListener('click', toggleSidebar);
    }

    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', toggleSidebar);
    }

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && sidebar.classList.contains('open')) {
            toggleSidebar();
        }
    });
});