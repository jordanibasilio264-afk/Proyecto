const openRegistro = document.getElementById("openRegistro");

const resgistroModal = document.getElementById("resgistroModal");

const cancelRegistModal = document.getElementById("cancelRegistModal");

const toggleModal = (show) => {
    if (resgistroModal) {
        resgistroModal.classList.toggle("active", show);
    }
}

openRegistro?.addEventListener("click", ()=> toggleModal(true));
cancelRegistModal?.addEventListener("click", ()=> toggleModal(false));