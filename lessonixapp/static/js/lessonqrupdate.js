let updateInterval = 30;
let countdown = updateInterval;

function updateQRCode() {
    fetch(generateQrUrl, {
        method: 'GET',
        headers: {
            'X-CSRFToken': '{{ csrf_token }}',
        },
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.qr_code) {
            document.querySelector('.qr-code img').src = `data:image/png;base64,${data.qr_code}`;
            console.log("QR code updated!");
        } else {
            console.error("Failed to update QR code", data);
        }
        countdown = updateInterval;
    })
    .catch(error => console.error("Error fetching QR code:", error));
}

function updateCountdownText() {
    const countdownElement = document.getElementById('countdown-text');
    countdownElement.textContent = `Оновлення QR через: ${countdown}`;
}

setInterval(() => {
    if (countdown <= 0) {
        updateQRCode();
    } else {
        countdown--;
        updateCountdownText();
    }
}, 1000);