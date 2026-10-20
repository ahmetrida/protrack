from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from portal.models import UserProfile, PastProjectArchive, ProjectGroup, ProjectProposal, WeeklyLog, Notification
from portal.similarity import calculate_abstract_similarity

class Command(BaseCommand):
    help = 'Seeds ProTrack v3.0 with real Student Roster, Faculty Names, and ahmetrida/protrack links'

    def handle(self, *args, **kwargs):
        # 1. Create Faculty & Staff Accounts
        faculty_data = [
            ('guide1', 'Guide@123', 'GUIDE', 'Professor Saurabh Pagar', 'FAC-101'),
            ('coordinator1', 'Admin@123', 'COORDINATOR', 'Professor Prajakta Borse', 'FAC-001'),
            ('examiner1', 'Viva@123', 'EXAMINER', 'Professor Secretly Anonymous', 'EXT-501'),
        ]
        faculty_users = {}
        for uname, pwd, role, full_name, emp_id in faculty_data:
            u, _ = User.objects.update_or_create(username=uname, defaults={'first_name': full_name})
            u.set_password(pwd)
            u.save()
            UserProfile.objects.update_or_create(user=u, defaults={'role': role, 'roll_or_emp_id': emp_id})
            faculty_users[role] = u

        # 2. Create the 5 Student Accounts for Team Claudeus
        students_data = [
            ('student1', 'Student@123', 'Mohammad Mustafa', 'TY-CS-01'),
            ('student2', 'Student@123', 'Ahmed Raza', 'TY-CS-02'),
            ('student3', 'Student@123', 'Momin Muneeb', 'TY-CS-03'),
            ('student4', 'Student@123', 'Umar Farroque', 'TY-CS-04'),
            ('student5', 'Student@123', 'Faizan Mansuri', 'TY-CS-05'),
        ]
        student_objs = []
        for uname, pwd, full_name, roll in students_data:
            u, _ = User.objects.update_or_create(username=uname, defaults={'first_name': full_name})
            u.set_password(pwd)
            u.save()
            UserProfile.objects.update_or_create(user=u, defaults={'role': 'STUDENT', 'roll_or_emp_id': roll})
            student_objs.append(u)

        # 3. Seed Past Departmental Archives
        past_projects = [
            ("Automated Attendance System Using Face Recognition",
             "A computer vision application using OpenCV and face recognition to capture student faces from a classroom webcam and log attendance into an Excel sheet automatically.",
             "2024-25", "Computer Vision"),
            ("Library Book Management and Fine Calculation System",
             "A web application for college libraries to issue books, track return deadlines, manage book inventory, and calculate overdue student fines.",
             "2023-24", "Web Development"),
            ("Online Hospital Appointment and Patient Record Portal",
             "A centralized healthcare portal enabling patients to book doctor appointments online and store digital medical prescriptions and lab reports.",
             "2024-25", "Healthcare IT"),
            ("E-Commerce Grocery Delivery Platform with Chatbot",
             "An online shopping cart for local grocery stores featuring product recommendations, online payment checkout, and an automated support chatbot.",
             "2023-24", "E-Commerce"),
            ("Smart Campus Placement and Alumni Tracking Portal",
             "A college web portal where final year students upload resumes, apply for campus placement drives, and connect with industry alumni.",
             "2024-25", "EdTech"),
            ("Fake News Detection Using Natural Language Processing",
             "A machine learning text classification model using TF-IDF vectorization and Logistic Regression to classify news articles as real or fake.",
             "2024-25", "AI / NLP"),
        ]
        for title, abst, yr, dom in past_projects:
            PastProjectArchive.objects.update_or_create(title=title, defaults={'abstract': abst, 'batch_year': yr, 'domain': dom})

        # 4. Create Team Claudeus Group with all 5 Members & https://github.com/ahmetrida/protrack
        grp, _ = ProjectGroup.objects.update_or_create(
            group_name="Team Claudeus (G-01)",
            defaults={
                'guide': faculty_users['GUIDE'],
                'current_stage': 'IN_PROGRESS',
                'github_repo_link': 'https://github.com/ahmetrida/protrack'
            }
        )
        grp.members.set(student_objs)

        title = "ProTrack: Web-Based Academic Project and Viva Management Portal"
        abstract = (
            "A centralized web portal built with Python, Django, and Scikit-Learn to manage student project registrations, "
            "detect duplicate project abstracts using hybrid N-gram cosine similarity, track weekly guide sign-offs, and conduct rubric-based viva grading."
        )
        score, match_t, match_s, _ = calculate_abstract_similarity(title, abstract, exclude_group_id=grp.id)
        ProjectProposal.objects.update_or_create(
            group=grp,
            defaults={
                'proposed_title': title,
                'abstract_text': abstract,
                'tech_stack': 'Python, Django, Scikit-Learn, Chart.js',
                'similarity_score': score,
                'closest_match_title': match_t,
                'closest_match_source': match_s,
                'status': 'APPROVED',
                'reviewer_remarks': 'Approved by Professor Saurabh Pagar. Well-scoped architecture and low similarity.'
            }
        )

        WeeklyLog.objects.update_or_create(
            group=grp, week_number=1,
            defaults={
                'tasks_completed': 'Completed requirement analysis, synopsis approval, and 6-table relational database schema.',
                'commit_or_doc_link': 'https://github.com/ahmetrida/protrack',
                'guide_remarks': 'Signed off by Professor Saurabh Pagar. Proceed to similarity engine.',
                'approval_status': 'APPROVED'
            }
        )
        WeeklyLog.objects.update_or_create(
            group=grp, week_number=2,
            defaults={
                'tasks_completed': 'Implemented custom royal-violet 8pt grid UI, stateful action buttons, and hybrid TF-IDF similarity engine.',
                'commit_or_doc_link': 'https://github.com/ahmetrida/protrack',
                'guide_remarks': 'Awaiting guide review',
                'approval_status': 'PENDING'
            }
        )

        # 5. Secondary Demo Group to showcase High Similarity Warning
        grp2, _ = ProjectGroup.objects.update_or_create(
            group_name="Group Alpha (G-02)",
            defaults={'guide': faculty_users['GUIDE'], 'current_stage': 'TOPIC_PENDING'}
        )
        dup_title = "Smart Classroom Attendance System via Webcam Face Recognition"
        dup_abs = "A Python OpenCV face recognition system that captures live classroom video from a webcam and logs student attendance into an Excel sheet automatically."
        s2, mt2, ms2, _ = calculate_abstract_similarity(dup_title, dup_abs, exclude_group_id=grp2.id)
        ProjectProposal.objects.update_or_create(
            group=grp2,
            defaults={
                'proposed_title': dup_title,
                'abstract_text': dup_abs,
                'tech_stack': 'Python, OpenCV, Pandas',
                'similarity_score': s2,
                'closest_match_title': mt2,
                'closest_match_source': ms2,
                'status': 'PENDING',
            }
        )

        Notification.objects.all().delete()
        for stu in student_objs:
            Notification.objects.create(
                recipient=stu,
                message="Professor Saurabh Pagar approved your proposal 'ProTrack'!",
                level='success'
            )
            Notification.objects.create(
                recipient=stu,
                message="Week 1 progress log signed off by Professor Saurabh Pagar.",
                level='info'
            )

        self.stdout.write(self.style.SUCCESS("✅ ProTrack v3.0 Seeded with Custom Roster & Repository Links!"))
