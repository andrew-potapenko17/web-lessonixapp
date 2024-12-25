document.addEventListener("DOMContentLoaded", function() {
    const headings = document.querySelectorAll("#start-lesson-page .statistics-container h2");

    headings.forEach((h2) => {
        setTimeout(() => {
            h2.classList.add('visible');
        }, 300);
    });
});