const openMedicineModal = document.getElementById("openMedicineModal");
const medicineModal = document.getElementById("medicineModal");
const closeMedicineModal = document.getElementById("closeMedicineModal");
const cancelMedicineModal = document.getElementById("cancelMedicineModal");

const toggleModal = (show) => {
    if (medicineModal) {
        medicineModal.classList.toggle("active", show);
    }
};

openMedicineModal?.addEventListener("click", () => toggleModal(true));
closeMedicineModal?.addEventListener("click", () => toggleModal(false));
cancelMedicineModal?.addEventListener("click", () => toggleModal(false));

document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && medicineModal?.classList.contains("active")) {
        toggleModal(false);
    }
});