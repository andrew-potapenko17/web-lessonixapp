document.addEventListener("DOMContentLoaded", function() {
    const days = ["Нд", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб"];
    const calendarContainer = document.getElementById('calendar-container');
    const mainTitle = document.getElementById('main-title');

    // Get today's date
    const today = new Date();

    // Fade in the title
    setTimeout(() => {
        mainTitle.classList.add('show'); // Add 'show' class to fade in the title
    }, 0); // Start immediately

    // Create squares for the calendar
    for (let i = -2; i <= 4; i++) {
        // Calculate the date for the square
        const currentDate = new Date(today);
        currentDate.setDate(today.getDate() + i);
        
        // Get the day index, day of the month, and month number
        const dayIndex = currentDate.getDay(); // 0-6 (Sun-Sat)
        const dayNum = currentDate.getDate();
        const monthNum = currentDate.getMonth() + 1; // Month is 0-indexed, so add 1
        const isToday = i === 0; // Check if it's today

        // Create the square element
        const square = document.createElement('div');
        square.className = 'calendar-square' + (isToday ? ' today' : ''); // Add 'today' class for today's square
        
        // Set day label with "(сьогодні)" if today
        const dayLabel = isToday ? `${days[dayIndex]} (сьогодні)` : days[dayIndex];

        square.innerHTML = `
            <div class="day-label">${dayLabel}</div> <!-- Day name -->
            <div class="date-label">${dayNum}/${monthNum}</div> <!-- Date -->
            ${isToday ? '<div class="today-indicator"></div>' : ''}
        `;
        
        // Append square to the container
        calendarContainer.appendChild(square);
        
        // Use setTimeout to fade in each square
        setTimeout(() => {
            square.classList.add('show'); // Add 'show' class to fade in
        }, (i + 2) * 500); // Delay for each square: 0ms, 500ms, etc.
    }
});
