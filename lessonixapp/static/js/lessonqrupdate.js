let updateInterval = 30; // Update every 30 seconds
let countdown = updateInterval; // Initial countdown value

function updateQRCode() {
    fetch(generateQrUrl, {
        method: 'GET',
        headers: {
            'X-CSRFToken': '{{ csrf_token }}', // Include CSRF token if needed
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
        // Reset the countdown after a successful update
        countdown = updateInterval;
    })
    .catch(error => console.error("Error fetching QR code:", error));
}

// Update the countdown timer text
function updateCountdownText() {
    const countdownElement = document.getElementById('countdown-text');
    countdownElement.textContent = `Оновлення QR через: ${countdown}`;
}

// Set up the interval to update the QR code
setInterval(() => {
    if (countdown <= 0) {
        updateQRCode();
    } else {
        countdown--;
        updateCountdownText();
    }
}, 1000); // Check and update every second