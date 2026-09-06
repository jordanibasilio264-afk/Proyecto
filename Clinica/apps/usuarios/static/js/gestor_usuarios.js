const openUserModal = document.getElementById("openUserModal");

const userModal = document.getElementById("userModal");

const closeUserModal = document.getElementById("closeUserModal");

const cancelUserModal = document.getElementById("cancelUserModal");


openUserModal.addEventListener("click", function () {

    userModal.classList.add("active");

});
closeUserModal.addEventListener("click", function () {

    userModal.classList.remove("active");

});
cancelUserModal.addEventListener("click", function () {

    userModal.classList.remove("active");

});
userModal.addEventListener("click", function (event) {
    if (event.target === userModal) {

        userModal.classList.remove("active");
    }
});
document.addEventListener("keydown", function (event) {
    
    if (event.key === "Escape") {
        userModal.classList.remove("active");
    }
});