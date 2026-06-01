// Live lesson view — polls the backend (no Firebase).
// `studentsUrl` is provided by lesson.html ({% url 'lesson_students' %}).

const STATUS_TRANSLATION = {
    'outschool': 'не в школі',
    'inschool': 'не в класі',
    'inclass': 'в класі',
    'wc': 'в туалеті',
    'med': 'в медпункті',
    'med_home': 'пішов додому',
    'med_back': 'повертається з медпункту',
    'ill': 'Захворів',
};

function renderStudents(students) {
    const list = document.getElementById('students-list');
    if (!list) return;
    list.innerHTML = students.map(function (s) {
        const translated = STATUS_TRANSLATION[s.status] || 'Unknown';
        return `
            <div class="student-item" id="student-${s.id}">
                <div class="student-icon">
                    <img src="/static/img/student_ico.png" alt="Student Icon">
                </div>
                <div class="student-details">
                    <p class="student-name">${s.full_name} (${translated})</p>
                </div>
                <div class="student-actions">
                    ${getStudentActionButtons(s.status, s.id)}
                </div>
            </div>`;
    }).join('');
}

function fetchStudents() {
    fetch(studentsUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(function (r) { return r.json(); })
        .then(function (data) { renderStudents(data.students || []); })
        .catch(function (error) { console.error('Error fetching students:', error); });
}

// Function to generate action buttons based on student status
function getStudentActionButtons(status, studentId) {
    let buttonsHtml = '';
    const updateStatusUrl = (newStatus) => `/update_status/${studentId}/${newStatus}/`;
    const redirect_to_med = (studentId) => `/redirect_med/${studentId}/`;

    switch (status) {
        case 'outschool':
            buttonsHtml += `
                <a href="${updateStatusUrl('inclass')}">
                    <img src="/static/img/green-btn.png" alt="Є в класі">
                </a>
                <a href="${updateStatusUrl('ill')}">
                    <img src="/static/img/ill-btn.png" alt="Захворів">
                </a>
            `;
            break;
        case 'inschool':
        case 'med_back':
            buttonsHtml += `
                <a href="${updateStatusUrl('inclass')}">
                    <img src="/static/img/green-btn.png" alt="Є в класі">
                </a>
            `;
            break;
        case 'inclass':
            buttonsHtml += `
                <a href="${updateStatusUrl('outschool')}">
                    <img src="/static/img/red-btn.png" alt="Не в класі">
                </a>
                <a href="${updateStatusUrl('wc')}">
                    <img src="/static/img/out-btn.png" alt="Відійшов">
                </a>
                <a href="${redirect_to_med(studentId)}">
                    <img src="/static/img/med-btn.png" alt="Відправити в медпункт">
                </a>
            `;
            break;
        case 'wc':
            buttonsHtml += `
                <a href="${updateStatusUrl('inclass')}">
                    <img src="/static/img/back-btn.png" alt="Повернувся">
                </a>
            `;
            break;
    }

    return buttonsHtml;
}

function openModal() {
    const modal = document.getElementById("slm");
    modal.classList.remove("hidden");
    setTimeout(() => { modal.classList.add("show"); }, 10);
}

function closeModal() {
    const modal = document.getElementById("slm");
    modal.classList.remove("show");
    setTimeout(() => { modal.classList.add("hidden"); }, 200);
}

window.onclick = function (event) {
    const modal = document.getElementById('slm');
    if (event.target === modal) {
        closeModal();
    }
};

// Initial load + poll every 2s for live status changes.
fetchStudents();
setInterval(fetchStudents, 2000);
