document.addEventListener("DOMContentLoaded", function() {
    const downloadXlsxButton = document.getElementById("download-xlsx-btn");

    downloadXlsxButton.addEventListener("click", function(event) {
        event.preventDefault();

        fetch(downloadXlxsUrl, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => {
            if (response.ok) {
                const disposition = response.headers.get("Content-Disposition");
                let filename = "attendance_report.xlsx"; 
                if (disposition && disposition.includes("filename*=UTF-8''")) {
                    filename = disposition
                        .split("filename*=UTF-8''")[1]
                        .replace(/['"]/g, ""); // Remove quotes around filename if present
                    // Decode URI components
                    filename = decodeURIComponent(filename);
                } else if (disposition && disposition.includes("filename=")) {
                    filename = disposition
                        .split("filename=")[1]
                        .replace(/['"]/g, ""); // Remove quotes around filename if present
                }
                return response.blob().then(blob => ({ blob, filename }));
            } else {
                alert("Не вдалося завантажити файл. Спробуйте ще раз.");
                throw new Error("Network response was not ok.");
            }
        })
        .then(({ blob, filename }) => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.style.display = "none";
            a.href = url;
            a.download = filename;  
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
        })
        .catch(error => console.error("Error downloading file:", error));
    });
});
