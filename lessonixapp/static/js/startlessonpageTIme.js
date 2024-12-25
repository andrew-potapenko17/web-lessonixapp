function updateDateTime() {
    const days = ["Нд", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб"];
    const now = new Date();
    const day = days[now.getDay()] + ",";
    const date = `${now.getDate()}/${now.getMonth() + 1}`;

    document.getElementById('day').textContent = day;
    document.getElementById('date').textContent = date;

    // Format time to local Ukrainian time (no seconds)
    const options = { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'Europe/Kiev' };
    document.getElementById('current-time').textContent = now.toLocaleTimeString('uk-UA', options);
}

setInterval(updateDateTime, 60000);

updateDateTime();
