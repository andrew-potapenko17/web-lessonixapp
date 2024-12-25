function fetchStudents() {
    firebase.database().ref(`school_classes/${schoolId}/${className}/students`).on('value', function(snapshot) {
        console.log('Student data snapshot received:', snapshot.val());

        // Clear the existing students list on the page
        const studentsList = document.getElementById('students-list');
        studentsList.innerHTML = '';  // Clear current list

        // Create a map to store the student statuses
        const studentsStatusMap = {};

        // Iterate over each student ID from the snapshot
        snapshot.forEach(function(childSnapshot) {
            const studentId = childSnapshot.val(); // Get the student ID from the snapshot
            console.log('Processing student:', studentId);

            // Construct the student data path
            const studentPath = `students/${schoolId}/${studentId}`;
            console.log('Student data path:', studentPath); // Log the student path

            // Fetch student details from the 'students' node using the student ID
            firebase.database().ref(studentPath).once('value')
                .then(function(studentSnapshot) {
                    const student = studentSnapshot.val();
                    if (student) {
                        const fullName = student.full_name;
                        const studentStatus = student.studentStatus;
                        studentsStatusMap[studentId] = { fullName, studentStatus };

                        // Map the student status to a translated status
                        const statusTranslation = {
                            'outschool': 'не в школі',
                            'inschool': 'не в класі',
                            'inclass': 'в класі',
                            'wc': 'в туалеті',
                            'med': 'в медпункті',
                            'med_home': 'пішов додому',
                            'med_back': 'повертається з медпункту',
                            'ill': 'Захворів',
                        };

                        const translatedStatus = statusTranslation[studentStatus] || 'Unknown';

                        // Create student item HTML and append it to the students list
                        const studentItem = `
                            <div class="student-item" id="student-${studentId}">
                                <div class="student-icon">
                                    <img src="/static/img/student_ico.png" alt="Student Icon">
                                </div>
                                <div class="student-details">
                                    <p class="student-name">${fullName} (${translatedStatus})</p>
                                </div>
                                <div class="student-actions">
                                    ${getStudentActionButtons(studentStatus, studentId)}
                                </div>
                            </div>
                        `;

                        // Append the new student item to the students list in the HTML
                        studentsList.innerHTML += studentItem;
                    }
                })
                .catch(function(error) {
                    console.error('Error fetching student details:', error);
                });
        });

        // Set a timer to periodically check for student status updates
        setInterval(() => {
            Object.keys(studentsStatusMap).forEach(studentId => {
                const studentPath = `students/${schoolId}/${studentId}`;
                firebase.database().ref(studentPath).once('value')
                    .then(function(studentSnapshot) {
                        const student = studentSnapshot.val();
                        if (student) {
                            const newStatus = student.studentStatus;
                            if (newStatus !== studentsStatusMap[studentId].studentStatus) {
                                // Update the status in the map
                                studentsStatusMap[studentId].studentStatus = newStatus;

                                // Update the display
                                const statusTranslation = {
                                    'outschool': 'не в школі',
                                    'inschool': 'не в класі',
                                    'inclass': 'в класі',
                                    'wc': 'в туалеті',
                                    'med': 'в медпункті',
                                    'med_home': 'пішов додому',
                                    'med_back': 'повертається з медпункту',
                                    'ill': 'Захворів',
                                };

                                const translatedStatus = statusTranslation[newStatus] || 'Unknown';

                                // Update the relevant student item in the HTML
                                const studentItem = document.getElementById(`student-${studentId}`);
                                if (studentItem) {
                                    const nameElement = studentItem.querySelector('.student-name');
                                    if (nameElement) {
                                        nameElement.textContent = `${studentsStatusMap[studentId].fullName} (${translatedStatus})`;
                                    }

                                    // Update the action buttons for the student
                                    const actionsElement = studentItem.querySelector('.student-actions');
                                    if (actionsElement) {
                                        actionsElement.innerHTML = getStudentActionButtons(newStatus, studentId);
                                    }
                                }
                            }
                        }
                    })
                    .catch(function(error) {
                        console.error('Error fetching updated student details:', error);
                    });
            });
        }, 1000); // Check every second
    }, function(error) {
        console.error('Error fetching student data:', error);
    });
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

// Call the function to fetch students initially
fetchStudents();