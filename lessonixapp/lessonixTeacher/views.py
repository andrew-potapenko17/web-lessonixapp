'''
 Lessonix views file
'''
import random
import string

from . import cfg
from io import BytesIO
from datetime import datetime, timezone

import base64
import jwt
import pytz
import qrcode
import pyrebase
import traceback

from urllib.parse import quote
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from django.utils.dateparse import parse_datetime
from openpyxl import Workbook
from PIL import Image, ImageDraw


firebase = pyrebase.initialize_app(cfg.cfg)
auth = firebase.auth()
db = firebase.database()


'''
 Authentication Function
'''

def authenticate(request):
    token = request.GET.get('token')

    if not token:
        return JsonResponse({'error': 'Token is required'}, status=400)

    try:
        # Decode the token
        payload = jwt.decode(token, cfg.JWT_SECRET, algorithms=[cfg.JWT_ALGORITHM])

        # Check if the token is expired
        exp_time = payload.get('exp')
        if not exp_time or datetime.fromtimestamp(exp_time, tz=timezone.utc) < datetime.now(timezone.utc):
            return JsonResponse({'error': 'Token is expired'}, status=401)

        # Token is valid, return the decoded payload or process it as needed

        email = payload.get('email')
        password = payload.get('password')

        try:
            user = auth.sign_in_with_email_and_password(email, password)
            session_id = user['idToken']
            user_id = user['localId']

            user_data = db.child("users").child(user_id).get().val()
            if user_data:
                full_name = user_data.get('full_name', 'Unknown')
                school_id = user_data.get('school_id', '0')
                classes = user_data.get('classes', {})
                role = user_data.get('role', 'Unknown')
                lvl = user_data.get('lvl', 1)

            request.session['uid'] = str(session_id)
            request.session['user_id'] = str(user_id)
            request.session['email'] = str(email)
            request.session['full_name'] = full_name
            request.session['school_id'] = str(school_id)
            request.session['classes'] = list(classes.keys())
            request.session['students'] = []
            request.session['role'] = role
            request.session['lvl'] = lvl

            messages.success(request, "Successfully logged in")
            return redirect('home')
        except Exception as e:
            messages.error(request, f"Invalid credentials. Please try again. Error: {str(e)}")
            return redirect('authenticate')


    except jwt.ExpiredSignatureError:
        return JsonResponse({'error': 'Token has expired'}, status=401)

    except jwt.InvalidTokenError as e:
        return JsonResponse({'error': f'Invalid token. Error: {str(e)}'}, status=401)

    
def endLesson(request):
    user_id = request.session.get('user_id')
    school_id = request.session.get('school_id')

    try:
        # Get the school status of the user
        school_status = db.child("users").child(user_id).get().val().get('schoolStatus')

        # Extract class name and subject from school status
        if school_status:
            lessonID = school_status
            lesson_data = db.child("schoollessons").child(school_id).child("lessons").child(lessonID).get().val()

            subject = lesson_data.get('subject', 'Unknown')
            class_name = lesson_data.get('class_name', 'Unknown')
        else:
            class_name = None
            subject = None

        if class_name:
            class_info = db.child("school_classes").child(school_id).child(class_name).get().val()
            student_ids = class_info.get('students', [])
            students = []

            # Initialize counts
            absent_count = 0
            ill_count = 0
            present_count = 0

            for student_id in student_ids:
                student_detail = db.child("students").child(school_id).child(student_id).get().val()

                if student_detail:
                    student_status = student_detail.get('studentStatus')

                    # Update student status if not 'outschool'
                    if student_status != 'outschool':
                        new_status = 'inschool'
                        school_status = 'nolesson'

                        if student_status in ['ill', 'med_home']:
                            new_status = student_status  # Keep the medical status

                        db.child("students").child(school_id).child(student_id).update({
                            "studentStatus": new_status,
                            "schoolStatus": school_status
                        })

                    # Update students list with translated status
                    status_translation = {
                        'outschool': 'н',
                        'inschool': 'н',
                        'inclass': '',
                        'wc': '',
                        'med': '',
                        'med_home': 'хв',
                        'med_back': '',
                        'ill': 'хв',
                    }

                    # Translate the status for counting
                    translated_status = status_translation.get(student_status, "error")
                    students.append({
                        'id': student_id,
                        'studentStatus': translated_status,
                    })

            # Count statuses based on translated values
            for student in students:
                if student['studentStatus'] == 'н':  # 'н' means absent
                    absent_count += 1
                elif student['studentStatus'] == 'хв':  # 'хв' means ill
                    ill_count += 1
                else:  # Any other status can be considered present
                    present_count += 1

            # Save student statuses and get report path
            report_path = save_student_statuses(school_id, class_name, subject, students)

            # Save lesson end time and report path
            end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            db.child("users").child(user_id).child("lessonstats").update({
                "ended": end_time,
                "absent_count": absent_count,
                "ill_count": ill_count,
                "present_count": present_count,
                "report_path": report_path,  # Save the report path
            })

        # Update user status
        db.child("users").child(user_id).update({'schoolStatus': 'nolesson'})

        # Update daily statistics
        daily_stats = db.child("users").child(user_id).child("dailystats").get().val() or {}
        lessons_completed = daily_stats.get('lessonscompleted', 0) + 1
        db.child("users").child(user_id).child("dailystats").update({'lessonscompleted': lessons_completed})

        messages.success(request, "Lesson ended successfully.")
    except Exception as e:
        print(f"Error in endLesson: {e}")
        messages.error(request, f"Failed to end the lesson. Error: {str(e)}")

    return redirect('lesson_completed')


def save_student_statuses(school_id, class_name, subject, students):
    current_date = datetime.now().strftime('%Y-%m-%d')
    statuses = {student['id']: student['studentStatus'] for student in students}

    base_report_path = f"reports/{school_id}/{class_name}/{subject}/{current_date}"
    report_path = base_report_path
    suffix = 1

    while db.child(report_path).get().val() is not None:
        report_path = f"{base_report_path}-{suffix}"
        suffix += 1

    db.child(report_path).set(statuses)
    return report_path  # Return the final report path for storage

def view_class_report(request):
    user_id = request.session.get('user_id')
    school_id = request.session.get('school_id')

    if not user_id:
        messages.error(request, "User not logged in. Please log in again.")
        return redirect('authenticate')

    selected_class = request.GET.get('class_name')
    selected_subject = request.GET.get('subject_name')

    if request.method == "POST":
        try:
            student_id = request.POST.get("student_id")
            date = request.POST.get("date")  # Date should be in 'YYYY-MM-DD' format
            class_name = request.POST.get('class_name')
            subject_name = request.POST.get('subject_name')
            current_status = request.POST.get("current_status")

            # Determine new status
            new_status = "" if current_status == "хв" else "н" if current_status == "" else "хв"

            # Update the database with the new status
            db.child("reports").child(school_id).child(class_name).child(subject_name).child(date).update({
                student_id: new_status
            })

            # Redirect back to the same URL with class and subject
            return redirect(f'/classreport/?class_name={class_name}&subject_name={subject_name}')

        except Exception as e:
            messages.error(request, f"Failed to update status: {str(e)}")
            return redirect('reports')
        
    if not selected_subject:
        try:
            user_info = db.child("users").child(user_id).get().val()
            user_subjects = user_info.get('subjects', []) if user_info else []
            report_data = db.child("reports").child(school_id).child(selected_class).get().val() or {}
            report_subjects = report_data.keys()
            available_subjects = [subject for subject in user_subjects if subject in report_subjects]

            context = {
                'selected_class': selected_class,
                'subjects': available_subjects,
                'class_name': selected_class,
            }
            return render(request, 'lessonixTeacher/subject_selection.html', context)

        except Exception as e:
            messages.error(request, f"Failed to load subjects: {str(e)}")
            return redirect('reports')
        
    try:
        class_info = db.child("school_classes").child(school_id).child(selected_class).get().val()
        student_ids = class_info.get('students', [])
        reports_data = db.child("reports").child(school_id).child(selected_class).child(selected_subject).get().val() or {}
        
        report_data = {}
        for date, statuses in reports_data.items():
            report_data[date] = {student_id: statuses.get(student_id, 'outschool') for student_id in student_ids}

            suffix = 1
            while True:
                suffixed_date = f"{date}-{suffix}"
                suffixed_report = reports_data.get(suffixed_date)
                
                if suffixed_report and suffixed_report != report_data[date]:
                    report_data[suffixed_date] = {
                        student_id: suffixed_report.get(student_id, 'outschool') for student_id in student_ids
                    }
                    suffix += 1
                else:
                    break

        full_names = {student_id: db.child("students").child(school_id).child(student_id).child("full_name").get().val() for student_id in student_ids}
        formatted_report_data = []
        for student_id in student_ids:
            student_statuses = {date: report_data.get(date, {}).get(student_id, 'н') for date in report_data}
            formatted_report_data.append({
                'student_id': student_id,
                'full_name': full_names.get(student_id, student_id),
                'statuses': student_statuses
            })

        context = {
            'selected_class': selected_class,
            'selected_subject': selected_subject,
            'report_data': formatted_report_data
        }

        return render(request, 'lessonixTeacher/class_report.html', context)

    except Exception as e:
        print(f"Error loading class report: {e}")
        messages.error(request, f"Failed to load report: {e}")
        return redirect('reports')

def lesson_completed(request):
    user_id = request.session.get('user_id')
    school_id = request.session.get('school_id')

    if not user_id:
        messages.error(request, "User not logged in. Please log in again.")
        return redirect('authenticate')

    try:
        user_data = db.child("users").child(user_id).get().val()

        if not user_data or 'lessonstats' not in user_data:
            messages.error(request, "No lesson completion data found.")
            return redirect('home')

        lesson_stats = user_data['lessonstats']

        # Retrieve report path from lesson stats
        report_path = lesson_stats.get("report_path")
        if not report_path:
            messages.error(request, "No report data found.")
            return redirect('home')

        # Fetch report data
        report_data = db.child(report_path).get().val() or {}

        cabinet = lesson_stats.get('cabinet')
        class_name = lesson_stats.get('class')
        subject = lesson_stats.get('subject')
        start_time_str = lesson_stats.get('started')
        end_time_str = lesson_stats.get('ended')

        # Convert string to datetime
        start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
        end_time = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
        duration = (end_time - start_time)
        duration_minutes = int(duration.total_seconds() // 60)
        duration_seconds = int(duration.total_seconds() % 60)

        present_count = lesson_stats.get('present_count')
        ill_count = lesson_stats.get('ill_count')
        absent_count = lesson_stats.get('absent_count')

        # Get ordered list of student IDs from the class
        class_info = db.child("school_classes").child(school_id).child(class_name).get().val()
        student_ids = class_info.get('students', [])

        # Prepare report data for rendering in order
        rendered_report_data = []
        for student_id in student_ids:
            status = report_data.get(student_id, 'outschool')  # Default to 'outschool' if not found
            student_info = db.child("students").child(school_id).child(student_id).get().val()
            rendered_report_data.append({
                'full_name': student_info.get('full_name', 'Unknown'),
                'status': status
            })

        context = {
            'present_count': present_count,
            'ill_count': ill_count,
            'absent_count': absent_count,
            'cabinet': cabinet,
            'class_name': class_name,
            'subject': subject,
            'duration': f"{duration_minutes} хв {duration_seconds} с",
            'report_data': rendered_report_data
        }

        return render(request, 'lessonixTeacher/lessoncompleted.html', context)
    except Exception as e:
        print(f"Error loading lesson completion data: {e}")
        messages.error(request, f"Failed to load lesson completion data. Error: {str(e)}")
        return redirect('home')

def download_txt(request):
    user_id = request.session.get('user_id')

    if not user_id:
        messages.error(request, "User not logged in.")
        return HttpResponse(status=403)

    try:
        user_data = db.child("users").child(user_id).get().val()
        lesson_stats = user_data.get('lessonstats', {})
        
        class_name = lesson_stats.get('class', 'UnknownClass')
        subject = lesson_stats.get('subject', 'UnknownSubject')
        start_time_str = lesson_stats.get('started', 'Unknown Start Time')
        end_time_str = lesson_stats.get('ended', 'Unknown Start Time')
        
        start_time = parse_datetime(start_time_str) if start_time_str != 'Unknown Start Time' else None
        end_time = parse_datetime(end_time_str) if end_time_str != 'Unknown Start Time' else None
        lesson_date = start_time.date() if start_time else "UnknownDate"

        if start_time and end_time:
            duration = end_time - start_time
            duration_minutes = int(duration.total_seconds() // 60)
            duration_seconds = int(duration.total_seconds() % 60)
        else:
            duration_minutes = 0
            duration_seconds = 0

        # Створюємо ім'я файлу з українськими символами
        filename = f"{class_name}_{subject}_{lesson_date}.txt"
        encoded_filename = quote(filename)

        txt_content = (
            f"Дата уроку: {lesson_date}\n"
            f"Час початку: {start_time_str}\n"
            f"Час завершення: {end_time_str}\n"
            f"Тривалість уроку: {duration_minutes} хв {duration_seconds} с\n"
            f"Кабінет: {lesson_stats.get('cabinet', 'Unknown')}\n"
            f"Клас: {class_name}\n"
            f"Предмет: {subject}\n"
            f"Кількість учнів, які були на уроці: {lesson_stats.get('present_count', 0)}\n"
            f"Кількість учнів, які були відмічені як хворі: {lesson_stats.get('ill_count', 0)}\n"
            f"Кількість учнів, які не були присутніми на уроці: {lesson_stats.get('absent_count', 0)}\n"
        )

        response = HttpResponse(txt_content, content_type='text/plain')
        response['Content-Disposition'] = f"attachment; filename*=UTF-8''{encoded_filename}"

        return response

    except Exception as e:
        print(f"Error creating TXT file: {traceback.format_exc()}")
        messages.error(request, "Failed to download statistics.")
        return HttpResponse(status=500)
    
def download_xlsx(request):
    user_id = request.session.get('user_id')
    school_id = request.session.get('school_id')

    if not user_id:
        return HttpResponse(status=403)  # Не авторизований

    try:
        user_data = db.child("users").child(user_id).get().val()

        if not user_data or 'lessonstats' not in user_data:
            return HttpResponse(status=404)  # Дані про урок не знайдені

        lesson_stats = user_data['lessonstats']
        class_name = lesson_stats.get('class')
        subject = lesson_stats.get('subject')

        # Отримати дані про відвідуваність
        reports_data = db.child("reports").child(school_id).child(class_name).child(subject).get().val() or {}
        last_date = sorted(reports_data.keys())[-1] if reports_data else None
        student_statuses = reports_data.get(last_date, {})

        # Отримати інформацію про студентів
        class_info = db.child("school_classes").child(school_id).child(class_name).get().val()
        student_ids = class_info.get('students', [])

        report_data = []
        for student_id in student_ids:
            status = student_statuses.get(student_id, 'outschool')  # За замовчуванням 'outschool'
            student_info = db.child("students").child(school_id).child(student_id).get().val()
            report_data.append({
                'full_name': student_info.get('full_name', 'Unknown'),
                'status': status
            })

        # Створюємо новий workbook
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Відвідуваність"

        # Додаємо заголовки
        sheet.append(["Ім'я учня", "Статус"])

        # Додаємо дані про відвідуваність
        for student in report_data:
            sheet.append([student['full_name'], student['status']])

        # Створюємо вихідний потік для XLSX файлу
        output = BytesIO()
        workbook.save(output)
        output.seek(0)

        start_time_str = lesson_stats.get('started', 'Unknown Start Time')
        start_time = parse_datetime(start_time_str) if start_time_str != 'Unknown Start Time' else None

        lesson_date = start_time.date() if start_time else "UnknownDate"

        filename = f"{class_name}_{subject}_{lesson_date}.xlsx"
        encoded_filename = quote(filename)

        # Налаштовуємо відповідь для завантаження
        
        response = HttpResponse(output.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f"attachment; filename*=UTF-8''{encoded_filename}"

        return response
    except Exception as e:
        print(f"Error generating XLSX file: {e}")
        return HttpResponse(status=500)  # Внутрішня помилка сервера

def teacher_reports_page(request):
    user_id = request.session.get('user_id')

    if not user_id:
        messages.error(request, "User not logged in. Please log in again.")
        return redirect('authenticate')

    try:
        user_info = db.child("users").child(user_id).get().val()
        teacher_classes = user_info.get('classes', {})

        report_names = []
        for class_name in teacher_classes.keys():
            report_names.append({'class_name': class_name})

        context = {
            'report_names': report_names,
        }

        return render(request, 'lessonixTeacher/teacherreports.html', context)

    except Exception as e:
        print(f"Error loading reports: {e}")
        messages.error(request, f"Failed to load reports: {e}")
        return redirect('home')

def home(request):
    user_id = request.session.get('user_id')
    school_id = request.session.get('school_id')

    print(school_id)

    if not user_id:
        messages.error(request, "User not logged in. Please log in again.")
        return redirect('authenticate')

    #return render(request, 'lessonixTeacher/home.html', context)
    return render(request, 'lessonixTeacher/home.html')
    try:
        # Get messages for the specific school
        messages_data = db.child("schoolmessages").child(school_id).child("messages").get()

        messages_list = []

        # Check if messages_data exists and convert it to a list
        if messages_data.val():
            for message_id, message_info in messages_data.val().items():
                message_info['id'] = message_id  # Keep track of message ID

                # Fetch the author's full name
                author_full_name = db.child("users").child(message_info['author']).child("full_name").get().val()
                message_info['full_name'] = author_full_name if author_full_name else "Unknown"

                messages_list.append(message_info)

        messages_list = sorted(messages_list, key=lambda x: x['created'])

        messages_list = messages_list[:20]

        context = {
            'messagesc': messages_list,
        }

        
    except Exception as e:
        print(f"Error loading messages: {e}")
        messages.error(request, f"Failed to load messages. Error: {str(e)}")
        return HttpResponse(e)
        #return redirect('home')
    
def post_message(request):
    user_id = request.session.get('user_id')
    school_id = request.session.get('school_id')

    if not user_id:
        messages.error(request, "User not logged in. Please log in again.")
        return redirect('authenticate')

    if request.method == 'POST':
        try:
            message_text = request.POST.get('message')

            if not message_text:
                messages.error(request, "Message cannot be empty.")
                return redirect('home')

            # Get the current time in Europe/Kiev timezone
            tz = pytz.timezone('Europe/Kiev')
            current_time = datetime.now(tz)

            # Format the date as "HH:MM DD.MM"
            formatted_time = current_time.strftime("%d.%m %H:%M")

            # Prepare message data
            message_data = {
                'author': user_id,
                'created': formatted_time,  # Use the formatted time
                'text': message_text
            }

            # Reference to school messages
            db.child("schoolmessages").child(school_id).child("messages").push(message_data)

            messages.success(request, "Message sent successfully!")
            return redirect('home')

        except Exception as e:
            print(f"Error posting message: {e}")
            messages.error(request, f"Failed to send message. Error: {str(e)}")
            return redirect('home')

    messages.error(request, "Invalid request method.")
    return redirect('home')
    
def generate_unique_school_id():
    while True:
        school_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        if not db.child('schools').child(school_id).get().val():
            return school_id

def generate_random_password(length=8):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for i in range(length))

def myschoolPage(request):
    school_id = request.session.get('school_id')
    try:
        users = db.child("users").get().val()
        school_name = db.child('schools').child(school_id).get().val().get('school_name')
        if users:
            users_list = [
                {
                    'full_name': user_info['full_name'],
                    'user_id': user_id,
                    'role': user_info.get('role'),
                }
                for user_id, user_info in users.items()
                if user_info.get('school_id') == school_id and user_info.get('role') != 'student'
            ]
        else:
            users_list = []
    except Exception as e:
        users_list = []
        messages.error(request, f"Failed to retrieve users. Error: {str(e)}")

    return render(request, 'lessonixTeacher/myschool.html', {'school_name': school_name, 'users': users_list})

def schoolclassesPage(request):
    school_id = request.session.get('school_id')
    school_name = db.child('schools').child(school_id).get().val().get('school_name')
    try:
        classes = db.child("school_classes").child(school_id).get().val()
        classes_list = []

        if classes:
            for class_key, class_info in classes.items():
                students = []
                
                for student_id in class_info.get('students', []):
                    student_data = db.child("students").child(school_id).child(student_id).get().val()
                    if student_data:
                        full_name = student_data.get('full_name', 'Unknown')
                        students.append(f"{full_name}")

                classes_list.append({
                    'name': class_info.get('name', 'Unnamed class'),
                    'students': students,
                })
        else:
            classes_list = []

    except Exception as e:
        classes_list = []
        messages.error(request, f"Failed to retrieve classes. Error: {str(e)}")

    return render(request, 'lessonixTeacher/schoolclasses.html', {'classes': classes_list, 'school_id': school_id, "school_name": school_name})

def myclassesPage(request):
    user_id = request.session.get('user_id')
    school_id = request.session.get('school_id')

    if not user_id or not school_id:
        messages.error(request, "User not authenticated or school ID missing. Please log in.")
        return redirect('authenticate')

    try:
        user_data = db.child("users").child(user_id).get().val()
        if not user_data or 'classes' not in user_data:
            messages.info(request, "You have not added any classes yet.")
            return render(request, 'lessonixTeacher/myclasses.html', {'classes': [], 'school_id': school_id})

        user_classes = user_data.get('classes', {})
        classes_info = []

        for class_name in user_classes:
            class_data = db.child("school_classes").child(school_id).child(class_name).get().val()
            if class_data:
                students = []
                for student_id in class_data.get('students', []):
                    student_data = db.child("students").child(school_id).child(student_id).get().val()
                    if student_data:
                        full_name = student_data.get('full_name', 'Unknown')
                        registered = student_data.get('registered', False)
                        student_status = "(не зареестрований)" if not registered else ""
                        students.append(f"{full_name} {student_status}")

                classes_info.append({
                    'name': class_name,
                    'school_id': school_id,
                    'last': class_data.get('last', ''),
                    'students': students,
                })

        return render(request, 'lessonixTeacher/myclasses.html', {'classes': classes_info, 'school_id': school_id})

    except Exception as e:
        messages.error(request, f"Failed to load classes. Error: {str(e)}")
        return redirect('home')

def generate_registration_code():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=16))

def generate_unique_student_id():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=10))

def add_to_your_classes(request, class_name):
    user_id = request.session.get('user_id')

    if not user_id:
        messages.error(request, "User not logged in. Please log in to add classes.")
        return redirect('authenticate')

    try:
        user_data = db.child("users").child(user_id).get().val()
        if user_data:
            classes = user_data.get('classes', {})
            if not isinstance(classes, dict):
                classes = {}

            if class_name not in classes:
                classes[class_name] = class_name
                db.child("users").child(user_id).update({"classes": classes})

                request.session['classes'] = list(classes.keys())
                messages.success(request, f"Class '{class_name}' added to your classes.")
            else:
                messages.info(request, f"Class '{class_name}' is already in your classes.")
    except Exception as e:
        messages.error(request, f"Failed to add class. Error: {str(e)}")

    return redirect('my_classes')

def profilePage(request, user_id):
    try:
        user_data = db.child("users").child(user_id).get().val()
        school_name = db.child('schools').child(request.session.get('school_id')).get().val().get('school_name')

        if user_data:
            return render(request, 'lessonixTeacher/profile.html', {'school_name': school_name, 'user': user_data})
        else:
            messages.error(request, "User not found.")
            return redirect('home')
    except Exception as e:
        messages.error(request, f"Failed to retrieve user profile. Error: {str(e)}")
        return redirect('home')

def class_detail(request, schoolID, name):
    try:
        class_info = db.child("school_classes").child(schoolID).child(name).get().val()
        if not class_info:
            raise ValueError("Class not found.")
        
        student_ids = class_info.get('students', [])
        students = []

        for student_id in student_ids:
            student_detail = db.child("students").child(schoolID).child(student_id).get().val()
            if student_detail:
                students.append({
                    'id': student_id,
                    'full_name': student_detail.get('full_name', 'Unknown'),
                    'status': student_detail.get('status', 'Unknown')
                })
        
    except Exception as e:
        messages.error(request, f"Failed to load class details. Error: {str(e)}")
        students = []

    return render(request, 'lessonixTeacher/class_detail.html', {
        'class_name': name,
        'school_id': schoolID,
        'students': students
    })

def delete_class(request, class_name):
    user_id = request.session.get('user_id')
    
    if not user_id:
        messages.error(request, "User not logged in. Please log in again.")
        return redirect('authenticate')

    try:
        user_data = db.child("users").child(user_id).get().val()
        if user_data:
            classes = user_data.get('classes', {})
            if not isinstance(classes, dict):
                classes = {}

            if class_name in classes:
                del classes[class_name]
                db.child("users").child(user_id).update({"classes": classes})
                
                request.session['classes'] = list(classes.keys())
                messages.success(request, f"Class '{class_name}' removed from your classes.")
            else:
                messages.error(request, f"Class '{class_name}' not found in your classes.")
        else:
            messages.error(request, "User data not found.")
    except Exception as e:
        messages.error(request, f"Failed to remove class. Error: {str(e)}")
    
    return redirect('my_classes')

def student_detail(request, school_id, student_id):
    if not school_id:
        messages.error(request, "School ID is missing. Please log in again.")
        return redirect('authenticate')

    try:
        student_data = db.child("students").child(school_id).child(student_id).get().val()
        
        if student_data:
            context = {
                'full_name': student_data.get('full_name', 'Unknown'),
                'school_id': school_id,
                'school_status': student_data.get('studentStatus', 'Unknown'),
                'register_code': student_data.get('registercode', 'Unknown'),
                'school_name': db.child('schools').child(school_id).get().val().get('school_name'),
            }
            return render(request, 'lessonixTeacher/singlestudentprofile.html', context)
        else:
            messages.error(request, "Student not found.")
            return redirect('home')
    except Exception as e:
        messages.error(request, f"Failed to retrieve student details. Error: {str(e)}")
        return redirect('home')
    
def startlessonPage(request):
    user_id = request.session['user_id']
    schoolID = request.session.get('school_id')
    user_classes = db.child('users').child(user_id).child('classes').get().val()
    user_cabs = db.child('users').child(user_id).child('cabs').get().val()
    user_subjects = db.child('users').child(user_id).child('subjects').get().val()

    if db.child("users").child(user_id).get().val().get("schoolStatus") != "nolesson":
        return redirect('lesson')

    if not user_classes:
        user_classes = []
    if not user_cabs:
        user_cabs = []
    if not user_subjects:
        user_subjects = []

    daily_stats = db.child("users").child(user_id).child("dailystats").get().val() or {}
    lessonscompleted = daily_stats.get('lessonscompleted', 0)
    studentschecked = daily_stats.get('studentschecked', 0)
    
    context = {
        'user_classes': user_classes,
        'user_cabs': user_cabs,
        'user_subjects': user_subjects,
        'lessonscompleted': lessonscompleted,
        'studentschecked': studentschecked,
    }

    if request.method == 'POST':
        class_name = request.POST.get('class')
        cabinet = request.POST.get('cabinet')
        subject = request.POST.get('subject')

        student_school_status = "{" + subject + "} " + "{" + cabinet + "}" 

        students = db.child("school_classes").child(schoolID).child(class_name).child("students").get()

        for student in students.each():
            studentID = student.val()  # Отримуємо ID студента
            db.child("students").child(schoolID).child(studentID).update({"schoolStatus": student_school_status})

        if user_id and class_name and cabinet and subject:
            ukrainian_tz = pytz.timezone('Europe/Kiev')
            timestarted = datetime.now(pytz.utc).astimezone(ukrainian_tz).strftime('%Y-%m-%d %H:%M:%S')

            
            lessonstats_update = {
                "class": class_name,
                "subject": subject,
                "cabinet": cabinet,
                "started": timestarted  # Store the start time in Ukrainian time
            }

            ukrainian_tz = pytz.timezone('Europe/Kiev')
            date = datetime.now(pytz.utc).astimezone(ukrainian_tz).strftime('%Y-%m-%d')

            lessonID = generate_qr_hash(10)

            db.child("schoollessons").child(schoolID).child("lessons").child(lessonID).update({
                        "subject": subject,
                        "cabinet": cabinet,
                        "date": date,
                        "class_name": class_name,
                    })
            
            db.child("users").child(user_id).update({"schoolStatus": lessonID})
            db.child("users").child(user_id).child("lessonstats").update(lessonstats_update)
            
            return redirect('lesson')

    return render(request, 'lessonixTeacher/startlessonpage.html', context)

def addCabinet(request):
    if request.method == 'POST':
        cab_num = request.POST.get('cab_num')
        user_id = request.session['user_id']

        if not user_id:
            messages.error(request, "User not logged in. Please log in to add cabinet.")
            return redirect('authenticate')

        try:
            user_data = db.child("users").child(user_id).get().val()
            if user_data:
                cabs = user_data.get('cabs', {})
                if not isinstance(cabs, dict):
                    cabs = {}

                if cab_num not in cabs:
                    cabs[cab_num] = cab_num
                    db.child("users").child(user_id).update({"cabs": cabs})
                    
                    request.session['cabs'] = list(cabs.keys())
                    messages.success(request, f"Cabinet '{cab_num}' added to your cabinets.")
                    return redirect('start_lesson_page')
                else:
                    messages.info(request, f"Cabinet '{cab_num}' is already in your cabinets.")
        except Exception as e:
            messages.error(request, f"Failed to add cabinet. Error: {str(e)}")
        
    return render(request, 'lessonixTeacher/addcabinet.html')

def addSubject(request):
    if request.method == 'POST':
        subject_name = request.POST.get('subject_name')
        user_id = request.session['user_id']

        if not user_id:
            messages.error(request, "User not logged in. Please log in to add subject.")
            return redirect('authenticate')

        try:
            user_data = db.child("users").child(user_id).get().val()
            if user_data:
                subjects = user_data.get('subjects', {})
                if not isinstance(subjects, dict):
                    subjects = {}

                if subject_name not in subjects:
                    subjects[subject_name] = subject_name
                    db.child("users").child(user_id).update({"subjects": subjects})
                    
                    request.session['subjects'] = list(subjects.keys())
                    messages.success(request, f"Subject '{subject_name}' added to your subjects.")
                    return redirect('start_lesson_page')
                else:
                    messages.info(request, f"Subject '{subject_name}' is already in your subjects.")
        except Exception as e:
            messages.error(request, f"Failed to add subject. Error: {str(e)}")

    return render(request, 'lessonixTeacher/addsubject.html')

def generate_qr_hash(length=10):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choices(characters, k=length))

def updateLessonQr(request, lessonID, subject, cabinet, date, class_name):

    school_id = request.session.get('school_id')

    qrhash = generate_qr_hash()

    qr_data = f"subject: {subject}\ncabinet: {cabinet}\ndate: {date}\nclass: {class_name}\nqrhash: {qrhash}"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill="black", back_color="white").convert("RGB")

    # Додаємо білий квадрат 150x150 у центрі QR-коду
    draw = ImageDraw.Draw(qr_img)
    
    # Параметри для білого квадрата (150x150)
    square_size = 150
    square_x0 = (qr_img.size[0] - square_size) // 2
    square_y0 = (qr_img.size[1] - square_size) // 2
    square_x1 = square_x0 + square_size
    square_y1 = square_y0 + square_size

    # Малюємо білий квадрат
    draw.rectangle([square_x0, square_y0, square_x1, square_y1], fill="white")

    # Завантажуємо зображення для вставки в центр
    overlay_image = Image.open("static/img/qr-base.png").convert("RGBA")

    # Вираховуємо позицію для вставки зображення в центр
    overlay_x = square_x0 + (square_size - overlay_image.size[0]) // 2
    overlay_y = square_y0 + (square_size - overlay_image.size[1]) // 2

    # Накладаємо зображення
    qr_img.paste(overlay_image, (overlay_x, overlay_y), overlay_image)

    # Перетворення зображення QR-коду у формат base64 для передачі в HTML
    buffer = BytesIO()
    qr_img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    db.child("schoollessons").child(school_id).child("lessons").child(lessonID).update({
                "hash": qrhash,
            })

    return qr_base64

def generate_qr(request, lessonID):
    # Get necessary data (subject, cabinet, date, class_name) from the database or session
    school_id = request.session.get('school_id')
    lesson_data = db.child("schoollessons").child(school_id).child("lessons").child(lessonID).get().val()

    if not lesson_data:
        return JsonResponse({'error': 'Lesson not found'}, status=404)

    subject = lesson_data.get('subject', 'Unknown')
    cabinet = lesson_data.get('cabinet', 'Unknown')
    date = lesson_data.get('date', 'Unknown')
    class_name = lesson_data.get('class_name', 'Unknown')

    # Generate QR code
    qr_base64 = updateLessonQr(request, lessonID, subject, cabinet, date, class_name)

    return JsonResponse({'qr_code': qr_base64})

def lessonPage(request):
    # Отримуємо дані користувача та школи з сесії
    user_id = request.session.get('user_id')
    school_id = request.session.get('school_id')

    # Перевіряємо поточний статус уроку для користувача
    school_status = db.child("users").child(user_id).get().val().get('schoolStatus')

    if school_status == "nolesson":
        return redirect('start_lesson_page')
    
    lessonID = school_status

    lesson_data = db.child("schoollessons").child(school_id).child("lessons").child(lessonID).get().val()

    subject = lesson_data.get('subject', 'Unknown')
    cabinet = lesson_data.get('cabinet', 'Unknown')
    date = lesson_data.get('date', 'Unknown')
    class_name = lesson_data.get('class_name', 'Unknown')

    # Створення QR-коду
    qr = updateLessonQr(request, lessonID, subject, cabinet, date, class_name)
    
    # Додаткові дані для шаблону
    context = {
        'class_name': class_name,
        'subject': subject,
        'cabinet': cabinet,
        'school_id': school_id,
        'lessonID': lessonID,
        'qr_code': qr,  # Передаємо QR-код
    }

    return render(request, 'lessonixTeacher/lesson.html', context)

def get_student_status(request):
    user_id = request.session['user_id']
    school_id = request.session['school_id']

    school_status = db.child("users").child(user_id).get().val().get('schoolStatus')

    if school_status:
        stripped_status = school_status.strip('{}')
        parts = stripped_status.split('} {')

        class_name = parts[0]
    else:
        return JsonResponse({'error': 'No active lesson'}, status=400)

    try:
        # Getting class information
        class_info = db.child("school_classes").child(school_id).child(class_name).get().val()
        if not class_info:
            return JsonResponse({'error': 'Class not found'}, status=404)
        
        student_ids = class_info.get('students', [])
        students = []

        for student_id in student_ids:
            student_detail = db.child("students").child(school_id).child(student_id).get().val()
            if student_detail:
                # Mapping statuses to readable forms
                status_translation = {
                    'outschool': 'не в школі',
                    'inschool': 'не в класі',
                    'inclass': 'в класі',
                    'wc': 'в туалеті',
                    'med': 'в медпункті',
                    'med_home': 'пішов додому',
                    'med_back': 'повертається з медпункту',
                    'ill': 'Захворів',
                }
                student_status = student_detail.get('studentStatus', 'Unknown')
                translated_status = status_translation.get(student_status, 'Unknown')

                # Add medExtra field if status is 'med_back' or 'med_home'
                med_extra = None
                if student_status in ['med_back', 'med_home']:
                    med_extra = student_detail.get('medExtra', '')

                students.append({
                    'id': student_id,
                    'status': student_status,
                    'name_and_status': f"{student_detail.get('full_name', 'Unknown')} ({translated_status})",
                    'med_extra': med_extra
                })

        return JsonResponse({'students': students}, status=200)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def update_student_status(request, student_id, new_status):
    school_id = request.session.get('school_id')
    user_id = request.session['user_id']

    try:
        daily_stats = db.child("users").child(user_id).child("dailystats").get().val() or {}
        if new_status == "outschool":
            db.child("students").child(school_id).child(student_id).update({"studentStatus": new_status, "blocked": 1})
            studentschecked = daily_stats.get('studentschecked', 0) + 1
            db.child("users").child(user_id).child("dailystats").update({'studentschecked': studentschecked})
        elif new_status == "inclass":
            db.child("students").child(school_id).child(student_id).update({"studentStatus": new_status, "blocked": 0})
            studentschecked = daily_stats.get('studentschecked', 0) + 1
            db.child("users").child(user_id).child("dailystats").update({'studentschecked': studentschecked})
        else:
            db.child("students").child(school_id).child(student_id).update({"studentStatus": new_status})

        

    except Exception as e:
        messages.error(request, f"Failed to update student status. Error: {str(e)}")

    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

def redirect_to_med(request, student_id):
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        school_id = request.session['school_id']

        db.child("students").child(school_id).child(student_id).update({"studentStatus": "med"})
        db.child("med_req").child(school_id).child(student_id).set({"reason": reason})

        return redirect('lesson')

    context = {
        'student_id': student_id
    }
    return render(request, 'lessonixTeacher/gomedpage.html', context)

def set_primary_class(request, school_id, class_name):
    user_id = request.session['user_id']
    db.child("users").child(user_id).update({
        'primaryclass': class_name
    })

    return redirect('class_detail', schoolID=school_id, name=class_name)

def myclass(request):
    schoolID = request.session['school_id']
    user_id = request.session['user_id']
    name = db.child('users').child(user_id).get().val().get('primaryclass')

    try:
        class_info = db.child("school_classes").child(schoolID).child(name).get().val()
        if not class_info:
            raise ValueError("Class not found.")
        
        student_ids = class_info.get('students', [])
        students = []

        status_translation = {
            'outschool': 'не в школі',
            'inschool': 'не в класі',
            'inclass': 'в класі',
            'wc': 'в туалеті',
            'med': 'в медпункті',
            'med_home': 'пішов додому',
            'med_back': 'повертається з медпункту',
            'ill': 'Захворів',
        }

        for student_id in student_ids:
            student_detail = db.child("students").child(schoolID).child(student_id).get().val()
            if student_detail:
                # Translate status
                student_status = student_detail.get('studentStatus', 'Unknown')
                translated_status = status_translation.get(student_status, 'Unknown')

                # Add medExtra field if status is 'med_back' or 'med_home'
                med_extra = None
                if student_status in ['med_back', 'med_home']:
                    med_extra = student_detail.get('medExtra', '')

                # Add student details with translated status and medExtra (if applicable)
                students.append({
                    'id': student_id,
                    'full_name': student_detail.get('full_name', 'Unknown'),
                    'status': student_status,
                    'translated_status': translated_status,
                    'med_extra': med_extra
                })

    except Exception as e:
        messages.error(request, f"Failed to load class details. Error: {str(e)}")
        students = []

    return render(request, 'lessonixTeacher/myclass.html', {
        'class_name': name,
        'school_id': schoolID,
        'students': students
    })

def delete_class(request, class_name):
    user_id = request.session.get('user_id')
    
    if not user_id:
        messages.error(request, "User not logged in. Please log in again.")
        return redirect('authenticate')

    try:
        user_data = db.child("users").child(user_id).get().val()
        if user_data:
            classes = user_data.get('classes', {})
            if not isinstance(classes, dict):
                classes = {}

            if class_name in classes:
                del classes[class_name]
                db.child("users").child(user_id).update({"classes": classes})
                
                request.session['classes'] = list(classes.keys())
                messages.success(request, f"Class '{class_name}' removed from your classes.")
            else:
                messages.error(request, f"Class '{class_name}' not found in your classes.")
        else:
            messages.error(request, "User data not found.")
    except Exception as e:
        messages.error(request, f"Failed to remove class. Error: {str(e)}")
    
    return redirect('my_classes')

def generate_event_hash(schoolID):
    while True:
        eventHash = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        if not db.child("events").child(schoolID).child(eventHash).get().val():
            return eventHash

def eventsPage(request):
    schoolID = request.session['school_id']
    user_id = request.session['user_id']

    user_cabs = db.child('users').child(user_id).child('cabs').get().val()

    user_events = db.child('users').child(user_id).child('events').get().val()

    if not user_cabs:
        user_cabs = []
    
    user_events_context = []

    if user_events:
        for event_hash in user_events:
            # Fetch event details from the global events collection
            event_data = db.child("events").child(schoolID).child(event_hash).get().val()
            if event_data:
                match event_data.get("started", 0):
                    case 0:
                        started = "Не розпочато"
                    case 1:
                        started = "Триває"
                    case 2:
                        started = "Завершено"
                    case _:
                        started = "Unknown"
                user_events_context.append({
                    "name": event_data.get("topic", "Unknown Topic"),
                    "started": started,
                    "time": event_data.get("time", "Unknown"),
                    "hash": event_hash,
                })

    context = {
        'user_cabs': user_cabs,
        'user_events': user_events_context,
    }

    if request.method == 'POST':
        topic = request.POST.get('topic')
        cabinet = request.POST.get('cabinet')
        time = request.POST.get('time')

        eventHash = generate_event_hash(schoolID)

        db.child("events").child(schoolID).child(eventHash).set({
            "topic": topic,
            "cabinet": cabinet,
            "time": time,
            "started": 0,
            "organizator": user_id,
        })
        
        full_name = db.child('users').child(user_id).child("full_name").get().val()

        db.child("events").child(schoolID).child(eventHash).child("users").update({
            full_name + " ( Організатор )": full_name + " ( Організатор )",
        })

        user_data = db.child("users").child(user_id).get().val()
        events = user_data.get('events', {})
        if not isinstance(events, dict):
            events = {}

        if eventHash not in events:
            events[eventHash] = eventHash
            db.child("users").child(user_id).update({"events": events})
                    
            request.session['events'] = list(events.keys())

        return redirect('events')

    return render(request, "lessonixTeacher/events.html", context)

def singleEventPage(request, eventHash):
    schoolID = request.session['school_id']
    user_id = request.session['user_id']
    event_data = db.child("events").child(schoolID).child(eventHash).get().val()
    cabinet = event_data.get("cabinet", "xxx")
    qr = Image.open("static/img/qr-base.png").convert("RGBA")

    if event_data:
        match event_data.get("started", 0):
            case 0:
                started = "Не розпочато"
                actionButton = "Розпочати захід"
            case 1:
                started = "Триває"
                actionButton = "Завершити захід"
                qr = generateEventQR(eventHash, cabinet, schoolID)
            case 2:
                started = "Завершено"
                actionButton = "Захід завершено"
            case _:
                started = "Unknown"
                actionButton = "EVENT_ACTION"
        
        persons = db.child('events').child(schoolID).child(eventHash).child('users').get().val()

        if not persons:
            persons = []

        context = {
            "name": event_data.get("topic", "Unknown Topic"),
            "started": started,
            "actionButton": actionButton,
            "time": event_data.get("time", "Unknown"),
            "hash": eventHash,
            "qr_code": qr,
            "persons": persons,
        }
    return render(request, 'lessonixTeacher/eventPage.html', context)

def eventAction(request, eventHash):
    schoolID = request.session['school_id']
    user_id = request.session['user_id']

    event_data = db.child("events").child(schoolID).child(eventHash).get().val()

    if user_id!=event_data.get("organizator", "Unknown"):
        return redirect('eventPage', eventHash)

    started = event_data.get("started", 0)

    if started <=1:
        started+=1
    else:
        return redirect('eventPage', eventHash)
    
    db.child("events").child(schoolID).child(eventHash).update({
        "started": started,
    })
    
    return redirect('eventPage', eventHash)

def generateEventQR(eventHash, cabinet, schoolID):
    qr_data = f"hash: {eventHash}\ncabinet: {cabinet}\nschoolID: {schoolID}"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill="black", back_color="white").convert("RGB")

    # Додаємо білий квадрат 150x150 у центрі QR-коду
    draw = ImageDraw.Draw(qr_img)
    
    # Параметри для білого квадрата (150x150)
    square_size = 150
    square_x0 = (qr_img.size[0] - square_size) // 2
    square_y0 = (qr_img.size[1] - square_size) // 2
    square_x1 = square_x0 + square_size
    square_y1 = square_y0 + square_size

    # Малюємо білий квадрат
    draw.rectangle([square_x0, square_y0, square_x1, square_y1], fill="white")

    # Завантажуємо зображення для вставки в центр
    overlay_image = Image.open("static/img/qr-base.png").convert("RGBA")

    # Вираховуємо позицію для вставки зображення в центр
    overlay_x = square_x0 + (square_size - overlay_image.size[0]) // 2
    overlay_y = square_y0 + (square_size - overlay_image.size[1]) // 2

    # Накладаємо зображення
    qr_img.paste(overlay_image, (overlay_x, overlay_y), overlay_image)

    # Перетворення зображення QR-коду у формат base64 для передачі в HTML
    buffer = BytesIO()
    qr_img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    return qr_base64