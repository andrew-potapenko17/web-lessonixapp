function searchReports() {
    const input = document.getElementById('searchInput');
    const filter = input.value.toLowerCase();
    const reportList = document.getElementById('reportList');
    const reportItems = reportList.getElementsByClassName('class-report-item');

    for (let i = 0; i < reportItems.length; i++) {
        const className = reportItems[i].getAttribute('data-class-name').toLowerCase();
        if (className.includes(filter)) {
            reportItems[i].style.display = '';
        } else {
            reportItems[i].style.display = 'none';
        }
    }
}
