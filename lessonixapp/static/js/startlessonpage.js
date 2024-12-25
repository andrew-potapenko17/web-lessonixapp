function openModal() {
    const modal = document.getElementById("slm");
    modal.classList.remove("hidden");  // Ensure it's visible
    setTimeout(() => {
        modal.classList.add("show");   // Add the show class to trigger animation
    }, 10); // Small timeout to allow DOM to register the change
}

function closeModal() {
    const modal = document.getElementById("slm");
    modal.classList.remove("show");    // Start hiding the modal

    // Add a timeout to wait for the transition to complete before adding hidden
    setTimeout(() => {
        modal.classList.add("hidden"); // Fully hide it after the animation
    }, 200); // Match the duration of the transition
}

window.onclick = function(event) {
    const modal = document.getElementById('slm');
    if (event.target === modal) {
        closeModal();
    }
};