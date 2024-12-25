function searchSubjects() {
    const input = document.getElementById('searchInput');
    const filter = input.value.toLowerCase();
    const subjectList = document.getElementById('subjectList');
    const subjectItems = subjectList.getElementsByClassName('subject-item');

    for (let i = 0; i < subjectItems.length; i++) {
        const subjectName = subjectItems[i].getAttribute('data-subject-name').toLowerCase();
        if (subjectName.includes(filter)) {
            subjectItems[i].style.display = '';
        } else {
            subjectItems[i].style.display = 'none';
        }
    }
}
