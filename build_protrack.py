import os
import sys
import shutil
import subprocess

def write_file(path, content):
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content.strip() + '\n')
    print(f"  [OK] Created {path}")

# ==============================================================================
# 1. REQUIREMENTS.TXT & MANAGE.PY
# ==============================================================================
REQUIREMENTS_TXT = """
Django>=4.2,<5.2
scikit-learn>=1.3.0
pandas>=2.0.0
Pillow>=10.0.0
"""

MANAGE_PY = """
#!/usr/bin/env python
import os
import sys

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'protrack_config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError("Couldn't import Django.") from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
"""

# ==============================================================================
# 2. PROJECT CONFIGURATION (protrack_config)
# ==============================================================================
SETTINGS_PY = """
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = 'django-insecure-protrack-v4-enterprise-edition-secret-key'
DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'portal',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'protrack_config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'protrack_config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
"""

CONFIG_URLS_PY = """
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('portal.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
"""

WSGI_PY = """
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'protrack_config.settings')
application = get_wsgi_application()
"""

# ==============================================================================
# 3. DATABASE MODELS (portal/models.py)
# ==============================================================================
MODELS_PY = """
import random
import string
from django.db import models
from django.contrib.auth.models import User

def generate_join_code():
    return 'PT-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

class University(models.Model):
    name = models.CharField(max_length=200, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class College(models.Model):
    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name='colleges')
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('university', 'name')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.university.name})"

class Department(models.Model):
    college = models.ForeignKey(College, on_delete=models.CASCADE, related_name='departments')
    name = models.CharField(max_length=150)
    academic_year = models.CharField(max_length=30, default='2026-2027')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('college', 'name')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.college.name}"

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('STUDENT', 'Student'),
        ('GUIDE', 'Faculty Guide'),
        ('COORDINATOR', 'Department Coordinator'),
        ('EXAMINER', 'External Examiner'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='STUDENT')
    university = models.ForeignKey(University, on_delete=models.SET_NULL, null=True, blank=True)
    college = models.ForeignKey(College, on_delete=models.SET_NULL, null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    identifier = models.CharField(max_length=50, blank=True, help_text="Roll Number or Faculty ID")
    class_division = models.CharField(max_length=50, blank=True, default="TY-A")

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"

class ProjectGroup(models.Model):
    name = models.CharField(max_length=120)
    join_code = models.CharField(max_length=12, unique=True, default=generate_join_code)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='groups')
    guide = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='guided_groups')
    students = models.ManyToManyField(User, related_name='student_groups', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.join_code})"

class ProjectProposal(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Guide Review'),
        ('APPROVED', 'Approved'),
        ('CHANGES', 'Changes Requested'),
    ]
    group = models.OneToOneField(ProjectGroup, on_delete=models.CASCADE, related_name='proposal')
    title = models.CharField(max_length=250)
    domain = models.CharField(max_length=120)
    abstract = models.TextField()
    similarity_score = models.FloatField(default=0.0)
    closest_match_title = models.CharField(max_length=250, blank=True, default='None')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    guide_remarks = models.TextField(blank=True)
    report_file = models.FileField(upload_to='reports/', null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

class WeeklyLog(models.Model):
    group = models.ForeignKey(ProjectGroup, on_delete=models.CASCADE, related_name='logs')
    week_number = models.PositiveIntegerField()
    tasks_completed = models.TextField()
    next_week_plan = models.TextField()
    is_verified = models.BooleanField(default=False)
    guide_feedback = models.CharField(max_length=255, blank=True)
    logged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-week_number', '-logged_at']

    def __str__(self):
        return f"{self.group.name} - Week {self.week_number}"

class VivaEvaluation(models.Model):
    group = models.OneToOneField(ProjectGroup, on_delete=models.CASCADE, related_name='viva')
    examiner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='evaluations')
    problem_clarity = models.PositiveIntegerField(default=0)
    implementation = models.PositiveIntegerField(default=0)
    presentation = models.PositiveIntegerField(default=0)
    documentation = models.PositiveIntegerField(default=0)
    total_score = models.PositiveIntegerField(default=0)
    examiner_comments = models.TextField(blank=True)
    evaluated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.total_score = (
            int(self.problem_clarity) +
            int(self.implementation) +
            int(self.presentation) +
            int(self.documentation)
        )
        super().save(*args, **kwargs)

    @property
    def grade_badge(self):
        if self.total_score >= 85:
            return 'O (Outstanding)'
        elif self.total_score >= 75:
            return 'A+ (Excellent)'
        elif self.total_score >= 65:
            return 'A (Very Good)'
        elif self.total_score >= 55:
            return 'B+ (Good)'
        return 'B (Satisfactory)'

class PastProjectArchive(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='archives', null=True, blank=True)
    title = models.CharField(max_length=250)
    year = models.CharField(max_length=10, default='2025')
    domain = models.CharField(max_length=120, default='Computer Science')
    abstract = models.TextField()

    def __str__(self):
        return f"{self.title} ({self.year})"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
"""

# ==============================================================================
# 4. HYBRID AI TF-IDF SIMILARITY ENGINE (portal/similarity.py)
# ==============================================================================
SIMILARITY_PY = """
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .models import PastProjectArchive, ProjectProposal

FALLBACK_CORPUS = [
    {
        "title": "Automated Student Attendance System Using Facial Recognition (2024)",
        "abstract": "An automated classroom attendance monitoring application built with OpenCV, Haar cascades, and deep metric face encodings to mark student attendance in real time via webcam feeds and export CSV sheets."
    },
    {
        "title": "Smart Campus Placement & Alumni Recruitment Portal (2024)",
        "abstract": "A centralized web platform connecting final-year students with corporate recruiters, featuring resume parsing, CGPA eligibility filtering, interview scheduling, and automated placement analytics."
    },
    {
        "title": "Blockchain-Based Academic Certificate Verification System (2025)",
        "abstract": "A decentralized tamper-proof credential verification portal using smart contracts and cryptographic SHA-256 hashes to eliminate fake university diplomas and enable instant employer validation."
    },
    {
        "title": "Hospital Patient Queue & E-Prescription Management System (2025)",
        "abstract": "A healthcare web application enabling patients to book OPD appointments online, track live doctor consultation queues, and generate digital prescriptions with pharmacy inventory alerts."
    },
    {
        "title": "AI-Powered Crop Disease Detection and Farmer Advisory App (2025)",
        "abstract": "A machine learning agricultural support portal where farmers upload leaf images to detect plant diseases using convolutional neural networks and receive localized fertilizer treatment recommendations."
    }
]

def clean_text(text):
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\\s]', ' ', text)
    return re.sub(r'\\s+', ' ', text).strip()

def jaccard_token_overlap(t1, t2):
    s1 = set(clean_text(t1).split())
    s2 = set(clean_text(t2).split())
    if not s1 or not s2:
        return 0.0
    return len(s1.intersection(s2)) / len(s1.union(s2))

def check_abstract_similarity(new_title, new_abstract, department=None, exclude_group_id=None):
    query_combined = clean_text(f"{new_title} {new_title} {new_abstract}")
    if len(query_combined.split()) < 4:
        return {"score": 0.0, "closest_match": "Insufficient text length", "risk": "LOW"}

    corpus_records = []

    # 1. Department Past Archives
    archives = PastProjectArchive.objects.filter(department=department) if department else PastProjectArchive.objects.all()
    for a in archives:
        corpus_records.append({
            "title": f"{a.title} ({a.year} Archive)",
            "text": clean_text(f"{a.title} {a.title} {a.abstract}"),
            "raw_title": a.title
        })

    # 2. Existing Peer Proposals in the same Department
    proposals = ProjectProposal.objects.all()
    if department:
        proposals = proposals.filter(group__department=department)
    if exclude_group_id:
        proposals = proposals.exclude(group_id=exclude_group_id)

    for p in proposals:
        corpus_records.append({
            "title": f"{p.title} (Group: {p.group.name})",
            "text": clean_text(f"{p.title} {p.title} {p.abstract}"),
            "raw_title": p.title
        })

    # 3. Fallback Baseline Benchmark Corpus so fresh departments still get instant AI analysis
    for item in FALLBACK_CORPUS:
        corpus_records.append({
            "title": item["title"],
            "text": clean_text(f"{item['title']} {item['title']} {item['abstract']}"),
            "raw_title": item["title"]
        })

    if not corpus_records:
        return {"score": 0.0, "closest_match": "No matches found", "risk": "LOW"}

    documents = [r["text"] for r in corpus_records] + [query_combined]

    try:
        word_vec = TfidfVectorizer(stop_words='english', ngram_range=(1, 2))
        word_matrix = word_vec.fit_transform(documents)
        word_sims = cosine_similarity(word_matrix[-1], word_matrix[:-1]).flatten()

        char_vec = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5))
        char_matrix = char_vec.fit_transform(documents)
        char_sims = cosine_similarity(char_matrix[-1], char_matrix[:-1]).flatten()

        best_score = 0.0
        best_match = "No close match detected"

        for idx, rec in enumerate(corpus_records):
            w_score = float(word_sims[idx])
            c_score = float(char_sims[idx])
            t_overlap = jaccard_token_overlap(new_title, rec["raw_title"])
            hybrid = (0.50 * w_score) + (0.30 * c_score) + (0.20 * t_overlap)
            pct = round(min(hybrid * 100.0, 99.9), 1)
            if pct > best_score:
                best_score = pct
                best_match = rec["title"]

        if best_score >= 60.0:
            risk = "HIGH"
        elif best_score >= 30.0:
            risk = "MODERATE"
        else:
            risk = "LOW"

        return {
            "score": best_score,
            "closest_match": best_match if best_score >= 8.0 else "Unique Concept (No significant overlap)",
            "risk": risk
        }
    except Exception:
        return {"score": 0.0, "closest_match": "Unique Concept", "risk": "LOW"}
"""

# ==============================================================================
# 5. VIEWS & CONTROLLERS (portal/views.py)
# ==============================================================================
VIEWS_PY = """
import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Avg
from .models import (
    University, College, Department, UserProfile,
    ProjectGroup, ProjectProposal, WeeklyLog,
    VivaEvaluation, PastProjectArchive, Notification
)
from .similarity import check_abstract_similarity, FALLBACK_CORPUS

def notify_users(users, message):
    for u in users:
        if u:
            Notification.objects.create(user=u, message=message)

def api_hierarchy(request):
    \"\"\"Returns dynamic University -> College -> Department tree for cascading dropdowns.\"\"\"
    universities = list(University.objects.values('id', 'name'))
    colleges = list(College.objects.values('id', 'university_id', 'name'))
    departments = list(Department.objects.values('id', 'college_id', 'name', 'academic_year'))
    return JsonResponse({
        'universities': universities,
        'colleges': colleges,
        'departments': departments,
    })

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard_router')
    if request.method == 'POST':
        u = request.POST.get('username', '').strip()
        p = request.POST.get('password', '').strip()
        user = authenticate(request, username=u, password=p)
        if user:
            login(request, user)
            messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
            return redirect('dashboard_router')
        else:
            messages.error(request, "Invalid username or password. Need an account? Click 'Create Account' below.")
    return render(request, 'login.html', {
        'total_universities': University.objects.count(),
        'total_departments': Department.objects.count(),
        'total_users': UserProfile.objects.count(),
    })

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard_router')

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        role = request.POST.get('role', 'STUDENT').strip()
        identifier = request.POST.get('identifier', '').strip()
        class_division = request.POST.get('class_division', 'TY-A').strip()

        # Hierarchy resolution (supports selecting existing OR creating new inline)
        uni_id = request.POST.get('university_id', '')
        new_uni_name = request.POST.get('new_university', '').strip()

        col_id = request.POST.get('college_id', '')
        new_col_name = request.POST.get('new_college', '').strip()

        dept_id = request.POST.get('department_id', '')
        new_dept_name = request.POST.get('new_department', '').strip()

        if not full_name or not username or not password:
            messages.error(request, "Please fill in your full name, username, and password.")
            return redirect('signup')

        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, f"Username '{username}' is already taken. Please choose another.")
            return redirect('signup')

        # 1. Resolve University
        if new_uni_name:
            university, _ = University.objects.get_or_create(name=new_uni_name)
        elif uni_id and uni_id.isdigit():
            university = University.objects.filter(id=int(uni_id)).first()
        else:
            university = None

        if not university:
            messages.error(request, "Please select or enter a University.")
            return redirect('signup')

        # 2. Resolve College
        if new_col_name:
            college, _ = College.objects.get_or_create(university=university, name=new_col_name)
        elif col_id and col_id.isdigit():
            college = College.objects.filter(id=int(col_id), university=university).first()
        else:
            college = None

        if not college:
            messages.error(request, "Please select or enter a College under that University.")
            return redirect('signup')

        # 3. Resolve Department
        if new_dept_name:
            department, _ = Department.objects.get_or_create(college=college, name=new_dept_name)
        elif dept_id and dept_id.isdigit():
            department = Department.objects.filter(id=int(dept_id), college=college).first()
        else:
            department = None

        if not department:
            messages.error(request, "Please select or enter a Department.")
            return redirect('signup')

        # Split full name
        parts = full_name.split(' ', 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ''

        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        UserProfile.objects.create(
            user=user,
            role=role,
            university=university,
            college=college,
            department=department,
            identifier=identifier or f"{role[:3]}-{user.id:02d}",
            class_division=class_division
        )

        # Notify department coordinators of new registration
        coordinators = User.objects.filter(profile__department=department, profile__role='COORDINATOR').exclude(id=user.id)
        notify_users(coordinators, f"New {role.title()} registered in {department.name}: {full_name}")

        login(request, user)
        messages.success(request, f"Account created! Welcome to {department.name}, {full_name}.")
        return redirect('dashboard_router')

    return render(request, 'signup.html', {
        'universities': University.objects.all(),
        'colleges': College.objects.all(),
        'departments': Department.objects.all(),
    })

def logout_view(request):
    logout(request)
    messages.info(request, "You have been signed out safely.")
    return redirect('login')

@login_required
def dashboard_router(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if profile.role == 'GUIDE':
        return redirect('guide_dashboard')
    elif profile.role == 'COORDINATOR':
        return redirect('coordinator_dashboard')
    elif profile.role == 'EXAMINER':
        return redirect('examiner_dashboard')
    return redirect('student_dashboard')

@login_required
def mark_notifications_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect(request.META.get('HTTP_REFERER', 'dashboard_router'))

# ==============================================================================
# STUDENT WORKSPACE & DYNAMIC GROUP WIZARD
# ==============================================================================
@login_required
def student_dashboard(request):
    profile = request.user.profile
    dept = profile.department
    group = request.user.student_groups.first()

    # Available guides & unassigned students in the exact same department
    dept_guides = User.objects.filter(profile__department=dept, profile__role='GUIDE').select_related('profile')
    dept_students = User.objects.filter(
        profile__department=dept,
        profile__role='STUDENT',
        student_groups__isnull=True
    ).exclude(id=request.user.id).select_related('profile')
    open_groups = ProjectGroup.objects.filter(department=dept).prefetch_related('students', 'guide')

    if request.method == 'POST':
        action = request.POST.get('action')

        # 1. Create a New Project Group from Scratch
        if action == 'create_group' and not group:
            group_name = request.POST.get('group_name', '').strip()
            guide_id = request.POST.get('guide_id', '')
            teammate_ids = request.POST.getlist('teammate_ids')

            if not group_name:
                messages.error(request, "Please provide a name for your project group.")
                return redirect('student_dashboard')

            guide_user = User.objects.filter(id=guide_id, profile__department=dept, profile__role='GUIDE').first() if guide_id.isdigit() else None
            new_group = ProjectGroup.objects.create(
                name=group_name,
                department=dept,
                guide=guide_user
            )
            new_group.students.add(request.user)
            for tid in teammate_ids:
                if tid.isdigit():
                    tm = User.objects.filter(id=int(tid), profile__department=dept, profile__role='STUDENT').first()
                    if tm and not tm.student_groups.exists():
                        new_group.students.add(tm)
                        notify_users([tm], f"{request.user.get_full_name()} added you to project group '{new_group.name}'.")

            if guide_user:
                notify_users([guide_user], f"New group '{new_group.name}' selected you as their Faculty Guide.")
            messages.success(request, f"Group '{new_group.name}' created! Share join code {new_group.join_code} with teammates.")
            return redirect('student_dashboard')

        # 2. Join an Existing Group by Code or ID
        elif action == 'join_group' and not group:
            join_code = request.POST.get('join_code', '').strip().upper()
            target_group = ProjectGroup.objects.filter(join_code__iexact=join_code, department=dept).first()
            if not target_group:
                messages.error(request, f"No group found in {dept.name} with join code '{join_code}'.")
            else:
                target_group.students.add(request.user)
                notify_users(target_group.students.exclude(id=request.user.id), f"{request.user.get_full_name()} joined {target_group.name}!")
                messages.success(request, f"You have joined '{target_group.name}'!")
            return redirect('student_dashboard')

        # 3. Assign or Change Guide (if group has no guide yet)
        elif action == 'assign_guide' and group:
            guide_id = request.POST.get('guide_id', '')
            guide_user = User.objects.filter(id=guide_id, profile__department=dept, profile__role='GUIDE').first() if guide_id.isdigit() else None
            if guide_user:
                group.guide = guide_user
                group.save()
                notify_users([guide_user], f"Group '{group.name}' assigned you as their Faculty Guide.")
                messages.success(request, f"Assigned {guide_user.get_full_name()} as your Faculty Guide.")
            return redirect('student_dashboard')

        # 4. Submit / Update Project Proposal
        elif action == 'submit_proposal' and group:
            title = request.POST.get('title', '').strip()
            domain = request.POST.get('domain', '').strip()
            abstract = request.POST.get('abstract', '').strip()
            report_file = request.FILES.get('report_file')

            if not title or not abstract:
                messages.error(request, "Project title and abstract are required.")
                return redirect('student_dashboard')

            sim_res = check_abstract_similarity(title, abstract, department=dept, exclude_group_id=group.id)
            proposal, created = ProjectProposal.objects.get_or_create(group=group)
            proposal.title = title
            proposal.domain = domain or "Software Engineering"
            proposal.abstract = abstract
            proposal.similarity_score = sim_res['score']
            proposal.closest_match_title = sim_res['closest_match']
            proposal.status = 'PENDING'
            if report_file:
                proposal.report_file = report_file
            proposal.save()

            if group.guide:
                notify_users([group.guide], f"{group.name} submitted proposal '{title}' (Similarity: {sim_res['score']}%).")
            messages.success(request, f"Proposal submitted! AI Similarity Score: {sim_res['score']}%.")
            return redirect('student_dashboard')

        # 5. Submit Weekly Progress Log
        elif action == 'submit_log' and group:
            week_num = request.POST.get('week_number', '1')
            tasks = request.POST.get('tasks_completed', '').strip()
            plan = request.POST.get('next_week_plan', '').strip()
            if tasks and plan:
                WeeklyLog.objects.create(
                    group=group,
                    week_number=int(week_num) if week_num.isdigit() else 1,
                    tasks_completed=tasks,
                    next_week_plan=plan
                )
                if group.guide:
                    notify_users([group.guide], f"{group.name} logged Week {week_num} progress for your verification.")
                messages.success(request, f"Week {week_num} progress log recorded.")
            return redirect('student_dashboard')

    proposal = getattr(group, 'proposal', None) if group else None
    logs = group.logs.all() if group else []
    viva = getattr(group, 'viva', None) if group else None
    next_week = (logs.count() + 1) if group else 1

    return render(request, 'student_dashboard.html', {
        'group': group,
        'proposal': proposal,
        'logs': logs,
        'viva': viva,
        'next_week': next_week,
        'dept_guides': dept_guides,
        'dept_students': dept_students,
        'open_groups': open_groups,
        'notifications': request.user.notifications.filter(is_read=False)[:6],
    })

@login_required
def api_check_similarity(request):
    if request.method == 'POST':
        title = request.POST.get('title', '')
        abstract = request.POST.get('abstract', '')
        dept = request.user.profile.department
        group = request.user.student_groups.first()
        res = check_abstract_similarity(title, abstract, department=dept, exclude_group_id=group.id if group else None)
        return JsonResponse(res)
    return JsonResponse({'error': 'POST required'}, status=400)

# ==============================================================================
# FACULTY GUIDE WORKSPACE
# ==============================================================================
@login_required
def guide_dashboard(request):
    profile = request.user.profile
    dept = profile.department

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'claim_group':
            gid = request.POST.get('group_id')
            grp = get_object_or_404(ProjectGroup, id=gid, department=dept)
            grp.guide = request.user
            grp.save()
            notify_users(grp.students.all(), f"Prof. {request.user.get_full_name()} is now mentoring {grp.name}.")
            messages.success(request, f"You are now guiding '{grp.name}'.")

        elif action == 'review_proposal':
            pid = request.POST.get('proposal_id')
            decision = request.POST.get('decision')
            remarks = request.POST.get('guide_remarks', '').strip()
            prop = get_object_or_404(ProjectProposal, id=pid, group__guide=request.user)
            prop.status = decision
            prop.guide_remarks = remarks
            prop.save()
            status_label = "Approved" if decision == 'APPROVED' else "requested changes on"
            notify_users(prop.group.students.all(), f"Guide {request.user.get_full_name()} {status_label} your proposal '{prop.title}'.")
            messages.success(request, f"Updated proposal status for {prop.group.name}.")

        elif action == 'verify_log':
            lid = request.POST.get('log_id')
            feedback = request.POST.get('guide_feedback', '').strip()
            log_item = get_object_or_404(WeeklyLog, id=lid, group__guide=request.user)
            log_item.is_verified = True
            log_item.guide_feedback = feedback or "Verified & signed off by Faculty Guide."
            log_item.save()
            notify_users(log_item.group.students.all(), f"Week {log_item.week_number} log verified by Prof. {request.user.get_full_name()}.")
            messages.success(request, f"Verified Week {log_item.week_number} for {log_item.group.name}.")

        return redirect('guide_dashboard')

    my_groups = ProjectGroup.objects.filter(guide=request.user).prefetch_related('students', 'logs')
    unassigned_groups = ProjectGroup.objects.filter(department=dept, guide__isnull=True).prefetch_related('students')

    pending_proposals = ProjectProposal.objects.filter(group__guide=request.user, status='PENDING').count()
    approved_proposals = ProjectProposal.objects.filter(group__guide=request.user, status='APPROVED').count()
    unverified_logs = WeeklyLog.objects.filter(group__guide=request.user, is_verified=False).count()

    return render(request, 'guide_dashboard.html', {
        'my_groups': my_groups,
        'unassigned_groups': unassigned_groups,
        'pending_proposals': pending_proposals,
        'approved_proposals': approved_proposals,
        'unverified_logs': unverified_logs,
        'notifications': request.user.notifications.filter(is_read=False)[:6],
    })

# ==============================================================================
# DEPARTMENT COORDINATOR WORKSPACE & HIERARCHY ADMIN
# ==============================================================================
@login_required
def coordinator_dashboard(request):
    profile = request.user.profile
    dept = profile.department

    if request.method == 'POST':
        action = request.POST.get('action')

        # 1. Add Past Project Archive to Department TF-IDF Corpus
        if action == 'add_archive':
            title = request.POST.get('title', '').strip()
            year = request.POST.get('year', '2025').strip()
            domain = request.POST.get('domain', 'Computer Science').strip()
            abstract = request.POST.get('abstract', '').strip()
            if title and abstract:
                PastProjectArchive.objects.create(department=dept, title=title, year=year, domain=domain, abstract=abstract)
                messages.success(request, f"Added '{title}' to {dept.name} similarity corpus.")

        # 2. 1-Click Load Sample AI Corpus for the Department
        elif action == 'seed_corpus':
            added = 0
            for item in FALLBACK_CORPUS:
                _, created = PastProjectArchive.objects.get_or_create(
                    department=dept,
                    title=item["title"],
                    defaults={"year": "2025", "domain": "AI & Systems", "abstract": item["abstract"]}
                )
                if created:
                    added += 1
            messages.success(request, f"Loaded {added} benchmark academic abstracts into {dept.name}'s TF-IDF archive.")

        # 3. Create New Department under Current College (Descending Hierarchy Expansion)
        elif action == 'add_department':
            new_dept_name = request.POST.get('new_dept_name', '').strip()
            acad_year = request.POST.get('academic_year', '2026-2027').strip()
            if new_dept_name and profile.college:
                Department.objects.get_or_create(
                    college=profile.college,
                    name=new_dept_name,
                    defaults={'academic_year': acad_year}
                )
                messages.success(request, f"Department '{new_dept_name}' added under {profile.college.name}! Now live for student & faculty sign-ups.")

        # 4. Reassign Guide to Any Group in Department
        elif action == 'assign_guide':
            gid = request.POST.get('group_id')
            guide_id = request.POST.get('guide_id')
            grp = get_object_or_404(ProjectGroup, id=gid, department=dept)
            guide_user = get_object_or_404(User, id=guide_id, profile__department=dept, profile__role='GUIDE')
            grp.guide = guide_user
            grp.save()
            notify_users(grp.students.all(), f"Coordinator assigned Prof. {guide_user.get_full_name()} as your Faculty Guide.")
            messages.success(request, f"Assigned {guide_user.get_full_name()} to {grp.name}.")

        return redirect('coordinator_dashboard')

    groups = ProjectGroup.objects.filter(department=dept).prefetch_related('students', 'logs')
    dept_guides = User.objects.filter(profile__department=dept, profile__role='GUIDE')
    dept_students = User.objects.filter(profile__department=dept, profile__role='STUDENT')
    archives = PastProjectArchive.objects.filter(department=dept)

    approved_count = ProjectProposal.objects.filter(group__department=dept, status='APPROVED').count()
    pending_count = ProjectProposal.objects.filter(group__department=dept, status='PENDING').count()
    changes_count = ProjectProposal.objects.filter(group__department=dept, status='CHANGES').count()
    evaluated_count = VivaEvaluation.objects.filter(group__department=dept).count()

    return render(request, 'coordinator_dashboard.html', {
        'groups': groups,
        'dept_guides': dept_guides,
        'dept_students_count': dept_students.count(),
        'archives': archives,
        'approved_count': approved_count,
        'pending_count': pending_count,
        'changes_count': changes_count,
        'evaluated_count': evaluated_count,
        'college_departments': Department.objects.filter(college=profile.college) if profile.college else [],
        'notifications': request.user.notifications.filter(is_read=False)[:6],
    })

@login_required
def export_department_csv(request):
    dept = request.user.profile.department
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="ProTrack_{dept.name}_Gradebook.csv"'
    writer = csv.writer(response)
    writer.writerow(['Group Name', 'Join Code', 'Students', 'Faculty Guide', 'Proposal Title', 'Proposal Status', 'AI Similarity (%)', 'Verified Logs', 'Viva Score (/100)', 'Grade'])

    for g in ProjectGroup.objects.filter(department=dept):
        students_str = ", ".join([s.get_full_name() or s.username for s in g.students.all()])
        guide_str = g.guide.get_full_name() if g.guide else "Unassigned"
        prop = getattr(g, 'proposal', None)
        viva = getattr(g, 'viva', None)
        verified_logs = g.logs.filter(is_verified=True).count()
        writer.writerow([
            g.name,
            g.join_code,
            students_str,
            guide_str,
            prop.title if prop else "Not Submitted",
            prop.get_status_display() if prop else "No Proposal",
            f"{prop.similarity_score}%" if prop else "0%",
            verified_logs,
            viva.total_score if viva else "Pending",
            viva.grade_badge if viva else "Pending"
        ])
    return response

# ==============================================================================
# EXTERNAL EXAMINER RUBRIC WORKSPACE
# ==============================================================================
@login_required
def examiner_dashboard(request):
    dept = request.user.profile.department

    if request.method == 'POST':
        gid = request.POST.get('group_id')
        grp = get_object_or_404(ProjectGroup, id=gid, department=dept)
        p_score = min(max(int(request.POST.get('problem_clarity', 0) or 0), 0), 25)
        i_score = min(max(int(request.POST.get('implementation', 0) or 0), 0), 25)
        pr_score = min(max(int(request.POST.get('presentation', 0) or 0), 0), 25)
        d_score = min(max(int(request.POST.get('documentation', 0) or 0), 0), 25)
        comments = request.POST.get('examiner_comments', '').strip()

        viva, _ = VivaEvaluation.objects.get_or_create(group=grp)
        viva.examiner = request.user
        viva.problem_clarity = p_score
        viva.implementation = i_score
        viva.presentation = pr_score
        viva.documentation = d_score
        viva.examiner_comments = comments
        viva.save()

        notify_users(grp.students.all(), f"ExternalViva Evaluation published for {grp.name}: {viva.total_score}/100 ({viva.grade_badge}).")
        messages.success(request, f"Saved Viva Evaluation for {grp.name} ({viva.total_score}/100).")
        return redirect('examiner_dashboard')

    groups = ProjectGroup.objects.filter(department=dept).prefetch_related('students', 'logs')
    return render(request, 'examiner_viva.html', {
        'groups': groups,
        'notifications': request.user.notifications.filter(is_read=False)[:6],
    })
"""

# ==============================================================================
# 6. URL ROUTING & ADMIN REGISTRATION
# ==============================================================================
PORTAL_URLS_PY = """
from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_router, name='dashboard_router'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('student/', views.student_dashboard, name='student_dashboard'),
    path('guide/', views.guide_dashboard, name='guide_dashboard'),
    path('coordinator/', views.coordinator_dashboard, name='coordinator_dashboard'),
    path('coordinator/export-csv/', views.export_department_csv, name='export_department_csv'),
    path('examiner/', views.examiner_dashboard, name='examiner_dashboard'),
    path('notifications/read/', views.mark_notifications_read, name='mark_notifications_read'),
    path('api/check-similarity/', views.api_check_similarity, name='api_check_similarity'),
    path('api/hierarchy/', views.api_hierarchy, name='api_hierarchy'),
]
"""

ADMIN_PY = """
from django.contrib import admin
from .models import (
    University, College, Department, UserProfile,
    ProjectGroup, ProjectProposal, WeeklyLog,
    VivaEvaluation, PastProjectArchive, Notification
)

admin.site.register(University)
admin.site.register(College)
admin.site.register(Department)
admin.site.register(UserProfile)
admin.site.register(ProjectGroup)
admin.site.register(ProjectProposal)
admin.site.register(WeeklyLog)
admin.site.register(VivaEvaluation)
admin.site.register(PastProjectArchive)
admin.site.register(Notification)
"""

# ==============================================================================
# 7. TEMPLATES — GOOGLE WORKSPACE MATERIAL 3 DESIGN + GOOGLE SANS + LUCIDE ICONS
# ==============================================================================
BASE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ProTrack — Academic Project & Viva Management Cloud</title>
    <!-- Google Sans & Plus Jakarta Sans Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
    <!-- Bootstrap 5.3 Layout Grid -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Lucide High-Precision Vector Icons -->
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>
        :root {
            --m3-bg: #F8FAFD;
            --m3-surface: #FFFFFF;
            --m3-surface-tonal: #F0F4F9;
            --m3-primary: #0B57D0;
            --m3-primary-hover: #0842A0;
            --m3-primary-container: #D3E3FD;
            --m3-on-primary-container: #041E49;
            --m3-text: #1F1F1F;
            --m3-text-muted: #444746;
            --m3-border: #E1E5EA;
            --m3-success-bg: #E6F4EA;
            --m3-success-text: #137333;
            --m3-warning-bg: #FEF7E0;
            --m3-warning-text: #B06000;
            --m3-danger-bg: #FCE8E6;
            --m3-danger-text: #C5221F;
            --radius-xl: 24px;
            --radius-lg: 16px;
            --radius-pill: 9999px;
        }

        body {
            font-family: 'Google Sans', 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--m3-bg);
            color: var(--m3-text);
            font-size: 16px;
            line-height: 1.6;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            -webkit-font-smoothing: antialiased;
        }

        h1, h2, h3, h4, h5, h6 {
            font-family: 'Google Sans', 'Plus Jakarta Sans', sans-serif;
            letter-spacing: -0.015em;
            font-weight: 500;
        }

        /* Google Workspace Top Appbar */
        .m3-navbar {
            background: rgba(255, 255, 255, 0.92);
            backdrop-filter: blur(16px);
            border-bottom: 1px solid var(--m3-border);
            padding: 14px 28px;
            position: sticky;
            top: 0;
            z-index: 1030;
        }

        .brand-logo {
            display: inline-flex;
            align-items: center;
            gap: 12px;
            text-decoration: none;
            color: var(--m3-text);
            font-weight: 700;
            font-size: 1.35rem;
        }

        .brand-icon-box {
            width: 42px;
            height: 42px;
            border-radius: 12px;
            background: var(--m3-primary);
            color: #fff;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        /* Material 3 Elevated Cards */
        .m3-card {
            background: var(--m3-surface);
            border: 1px solid var(--m3-border);
            border-radius: var(--radius-xl);
            padding: 32px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02), 0 4px 16px rgba(11, 87, 208, 0.03);
            transition: box-shadow 0.2s ease, transform 0.2s ease;
        }

        .m3-card-tonal {
            background: var(--m3-surface-tonal);
            border: 1px solid transparent;
            border-radius: var(--radius-xl);
            padding: 28px;
        }

        /* Spacious Material 3 Controls */
        .form-label {
            font-weight: 500;
            font-size: 0.95rem;
            color: var(--m3-text);
            margin-bottom: 8px;
        }

        .form-control, .form-select {
            border-radius: 14px;
            padding: 14px 18px;
            font-size: 1rem;
            border: 1px solid #C4C7C5;
            background-color: #FFFFFF;
            color: var(--m3-text);
            transition: all 0.18s ease;
        }

        .form-control:focus, .form-select:focus {
            border-color: var(--m3-primary);
            box-shadow: 0 0 0 3px rgba(11, 87, 208, 0.16);
        }

        /* Material 3 Pill Buttons */
        .btn-m3-primary {
            background-color: var(--m3-primary);
            color: #FFFFFF;
            border: none;
            border-radius: var(--radius-pill);
            padding: 12px 26px;
            font-size: 0.98rem;
            font-weight: 500;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            transition: all 0.18s ease;
        }

        .btn-m3-primary:hover {
            background-color: var(--m3-primary-hover);
            color: #FFFFFF;
            box-shadow: 0 2px 8px rgba(11, 87, 208, 0.28);
        }

        .btn-m3-tonal {
            background-color: var(--m3-primary-container);
            color: var(--m3-on-primary-container);
            border: none;
            border-radius: var(--radius-pill);
            padding: 12px 24px;
            font-size: 0.96rem;
            font-weight: 500;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            transition: all 0.18s ease;
        }

        .btn-m3-tonal:hover {
            background-color: #B8D1FC;
            color: var(--m3-on-primary-container);
        }

        .btn-m3-outline {
            background-color: transparent;
            color: var(--m3-primary);
            border: 1px solid #747775;
            border-radius: var(--radius-pill);
            padding: 11px 24px;
            font-size: 0.96rem;
            font-weight: 500;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }

        .btn-m3-outline:hover {
            background-color: var(--m3-surface-tonal);
            border-color: var(--m3-primary);
        }

        /* Status & Context Chips */
        .m3-chip {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 14px;
            border-radius: var(--radius-pill);
            font-size: 0.875rem;
            font-weight: 500;
            white-space: nowrap;
        }

        .chip-tonal { background: var(--m3-primary-container); color: var(--m3-on-primary-container); }
        .chip-success { background: var(--m3-success-bg); color: var(--m3-success-text); }
        .chip-warning { background: var(--m3-warning-bg); color: var(--m3-warning-text); }
        .chip-danger { background: var(--m3-danger-bg); color: var(--m3-danger-text); }
        .chip-neutral { background: var(--m3-surface-tonal); color: var(--m3-text-muted); }

        .lucide {
            width: 20px;
            height: 20px;
            stroke-width: 2px;
        }

        /* Floating Toast Snackbar */
        .toast-stack {
            position: fixed;
            bottom: 28px;
            right: 28px;
            z-index: 1090;
            display: flex;
            flex-direction: column;
            gap: 12px;
            max-width: 420px;
        }

        .m3-snackbar {
            background: #1F1F1F;
            color: #FFFFFF;
            padding: 16px 22px;
            border-radius: 16px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 0.95rem;
        }
    </style>
</head>
<body>
    {% if user.is_authenticated %}
    <nav class="m3-navbar">
        <div class="container-fluid d-flex flex-wrap align-items-center justify-content-between gap-3">
            <div class="d-flex align-items-center gap-3 flex-wrap">
                <a href="{% url 'dashboard_router' %}" class="brand-logo">
                    <span class="brand-icon-box"><i data-lucide="graduation-cap"></i></span>
                    <span>ProTrack</span>
                </a>
                {% if user.profile.department %}
                <span class="m3-chip chip-neutral d-none d-lg-inline-flex">
                    <i data-lucide="building-2" style="width:16px;height:16px;"></i>
                    {{ user.profile.university.name }} &bull; {{ user.profile.college.name }} &bull; <strong class="text-dark">{{ user.profile.department.name }}</strong>
                </span>
                {% endif %}
            </div>

            <div class="d-flex align-items-center gap-3">
                <span class="m3-chip chip-tonal">
                    <i data-lucide="shield-check" style="width:16px;height:16px;"></i>
                    {{ user.profile.get_role_display }}
                </span>

                <!-- Notifications Bell -->
                <div class="dropdown">
                    <button class="btn btn-m3-outline position-relative py-2 px-3" data-bs-toggle="dropdown" aria-expanded="false">
                        <i data-lucide="bell"></i>
                        {% if notifications %}
                        <span class="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-danger">
                            {{ notifications|length }}
                        </span>
                        {% endif %}
                    </button>
                    <div class="dropdown-menu dropdown-menu-end p-3 shadow-lg border-0" style="width: 360px; border-radius: 20px;">
                        <div class="d-flex justify-content-between align-items-center mb-2 pb-2 border-bottom">
                            <span class="fw-bold">Department Alerts</span>
                            {% if notifications %}
                            <a href="{% url 'mark_notifications_read' %}" class="small text-decoration-none fw-medium">Mark all read</a>
                            {% endif %}
                        </div>
                        {% for n in notifications %}
                        <div class="py-2 border-bottom small">
                            <div class="text-dark fw-medium">{{ n.message }}</div>
                            <div class="text-muted" style="font-size: 0.78rem;">{{ n.created_at|timesince }} ago</div>
                        </div>
                        {% empty %}
                        <div class="text-center py-4 text-muted small">
                            <i data-lucide="check-circle-2" class="mb-2 text-success"></i>
                            <div>All caught up! No new notifications.</div>
                        </div>
                        {% endfor %}
                    </div>
                </div>

                <!-- User Identity & Logout -->
                <div class="d-flex align-items-center gap-2 ps-2 border-start">
                    <div class="text-end d-none d-sm-block">
                        <div class="fw-medium" style="line-height:1.2;">{{ user.get_full_name|default:user.username }}</div>
                        <div class="text-muted small" style="font-size:0.8rem;">{{ user.profile.identifier }}</div>
                    </div>
                    <a href="{% url 'logout' %}" class="btn btn-m3-outline py-2 px-3" title="Sign Out">
                        <i data-lucide="log-out"></i>
                    </a>
                </div>
            </div>
        </div>
    </nav>
    {% endif %}

    <main class="flex-grow-1 py-4 py-md-5">
        <div class="container">
            {% block content %}{% endblock %}
        </div>
    </main>

    <!-- Floating Material 3 Snackbars -->
    {% if messages %}
    <div class="toast-stack" id="toastStack">
        {% for message in messages %}
        <div class="m3-snackbar">
            <i data-lucide="sparkles" class="text-info flex-shrink-0"></i>
            <div class="flex-grow-1">{{ message }}</div>
        </div>
        {% endfor %}
    </div>
    {% endif %}

    <footer class="py-4 border-top bg-white mt-auto">
        <div class="container d-flex flex-wrap justify-content-between align-items-center text-muted small">
            <div><strong>ProTrack Cloud v4.0</strong> &mdash; Dynamic Multi-Tenant Academic Project & Viva Portal</div>
            <div>Powered by Django &bull; Scikit-Learn TF-IDF &bull; Google Material 3</div>
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        lucide.createIcons();
        setTimeout(() => {
            const stack = document.getElementById('toastStack');
            if (stack) stack.style.display = 'none';
        }, 5000);
    </script>
</body>
</html>
"""

# ==============================================================================
# 8. LOGIN & SELF-SERVICE REGISTRATION TEMPLATES
# ==============================================================================
LOGIN_HTML = """
{% extends 'base.html' %}
{% block content %}
<div class="row justify-content-center align-items-center g-5 py-3">
    <div class="col-lg-6">
        <div class="m3-chip chip-tonal mb-3">
            <i data-lucide="globe" style="width:16px;height:16px;"></i>
            Multi-University Dynamic Cloud
        </div>
        <h1 class="display-5 fw-bold mb-3" style="color: #041E49;">Academic Project & Viva Lifecycle, Simplified.</h1>
        <p class="lead text-muted mb-4" style="font-size: 1.15rem;">
            A unified workspace for Universities, Colleges, and Departments. Submit proposals with real-time Scikit-Learn TF-IDF similarity detection, track weekly mentor sign-offs, and grade viva evaluations seamlessly.
        </p>

        <div class="row g-3 mb-4">
            <div class="col-sm-4">
                <div class="m3-card-tonal text-center py-3">
                    <div class="h3 fw-bold text-primary mb-0">{{ total_universities }}</div>
                    <div class="small text-muted">Universities</div>
                </div>
            </div>
            <div class="col-sm-4">
                <div class="m3-card-tonal text-center py-3">
                    <div class="h3 fw-bold text-primary mb-0">{{ total_departments }}</div>
                    <div class="small text-muted">Departments</div>
                </div>
            </div>
            <div class="col-sm-4">
                <div class="m3-card-tonal text-center py-3">
                    <div class="h3 fw-bold text-primary mb-0">{{ total_users }}</div>
                    <div class="small text-muted">Registered Users</div>
                </div>
            </div>
        </div>
    </div>

    <div class="col-lg-5">
        <div class="m3-card">
            <div class="d-flex align-items-center gap-3 mb-4">
                <div class="brand-icon-box"><i data-lucide="graduation-cap"></i></div>
                <div>
                    <h3 class="mb-0 fw-bold">Sign in to ProTrack</h3>
                    <div class="text-muted small">Use your student or faculty account</div>
                </div>
            </div>

            <form method="POST">
                {% csrf_token %}
                <div class="mb-3">
                    <label class="form-label">Username</label>
                    <input type="text" name="username" class="form-control" placeholder="Enter your username" required autofocus>
                </div>
                <div class="mb-4">
                    <label class="form-label">Password</label>
                    <input type="password" name="password" class="form-control" placeholder="Enter your password" required>
                </div>
                <button type="submit" class="btn-m3-primary w-100 mb-3">
                    <i data-lucide="log-in"></i> Sign In to Workspace
                </button>
            </form>

            <hr class="my-4">
            <div class="text-center">
                <p class="text-muted mb-3">First time here from your college or department?</p>
                <a href="{% url 'signup' %}" class="btn-m3-tonal w-100 text-decoration-none">
                    <i data-lucide="user-plus"></i> Create New Account (Student / Faculty)
                </a>
            </div>
        </div>
    </div>
</div>
{% endblock %}
"""

SIGNUP_HTML = """
{% extends 'base.html' %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-xl-9">
        <div class="m3-card">
            <div class="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4 pb-3 border-bottom">
                <div class="d-flex align-items-center gap-3">
                    <div class="brand-icon-box"><i data-lucide="user-plus"></i></div>
                    <div>
                        <h2 class="mb-0 fw-bold">Create Your ProTrack Account</h2>
                        <div class="text-muted">Select your role and connect to your University &rarr; College &rarr; Department</div>
                    </div>
                </div>
                <a href="{% url 'login' %}" class="btn-m3-outline text-decoration-none">
                    <i data-lucide="arrow-left"></i> Back to Sign In
                </a>
            </div>

            <form method="POST" id="signupForm">
                {% csrf_token %}

                <!-- STEP 1: ROLE SELECTION -->
                <h5 class="fw-bold mb-3 d-flex align-items-center gap-2">
                    <i data-lucide="badge-check" class="text-primary"></i> 1. Choose Your Academic Role
                </h5>
                <div class="row g-3 mb-4">
                    <div class="col-md-3 col-sm-6">
                        <label class="m3-card-tonal p-3 w-100 h-100 d-block" style="cursor:pointer;">
                            <input type="radio" name="role" value="STUDENT" class="form-check-input me-2" checked>
                            <strong class="d-block mt-1">Student</strong>
                            <span class="small text-muted">Create/join groups, test abstracts & log tasks</span>
                        </label>
                    </div>
                    <div class="col-md-3 col-sm-6">
                        <label class="m3-card-tonal p-3 w-100 h-100 d-block" style="cursor:pointer;">
                            <input type="radio" name="role" value="GUIDE" class="form-check-input me-2">
                            <strong class="d-block mt-1">Faculty Guide</strong>
                            <span class="small text-muted">Mentor student groups, approve proposals & logs</span>
                        </label>
                    </div>
                    <div class="col-md-3 col-sm-6">
                        <label class="m3-card-tonal p-3 w-100 h-100 d-block" style="cursor:pointer;">
                            <input type="radio" name="role" value="COORDINATOR" class="form-check-input me-2">
                            <strong class="d-block mt-1">Coordinator / HOD</strong>
                            <span class="small text-muted">Manage department, AI archives & analytics</span>
                        </label>
                    </div>
                    <div class="col-md-3 col-sm-6">
                        <label class="m3-card-tonal p-3 w-100 h-100 d-block" style="cursor:pointer;">
                            <input type="radio" name="role" value="EXAMINER" class="form-check-input me-2">
                            <strong class="d-block mt-1">External Examiner</strong>
                            <span class="small text-muted">Evaluate projects & grade final viva rubrics</span>
                        </label>
                    </div>
                </div>

                <!-- STEP 2: DESCENDING INSTITUTIONAL HIERARCHY -->
                <h5 class="fw-bold mb-3 d-flex align-items-center gap-2">
                    <i data-lucide="building-2" class="text-primary"></i> 2. Institution Hierarchy (University &rarr; College &rarr; Department)
                </h5>
                <div class="m3-card-tonal mb-4">
                    <div class="row g-4">
                        <!-- University -->
                        <div class="col-md-4">
                            <div class="d-flex justify-content-between align-items-center mb-1">
                                <label class="form-label mb-0">University</label>
                                <button type="button" class="btn btn-link btn-sm p-0 text-decoration-none" onclick="toggleNewField('uni')">+ Add New</button>
                            </div>
                            <select name="university_id" id="uniSelect" class="form-select mb-2" onchange="filterColleges()">
                                <option value="">-- Select University --</option>
                                {% for u in universities %}
                                <option value="{{ u.id }}">{{ u.name }}</option>
                                {% endfor %}
                            </select>
                            <input type="text" name="new_university" id="uniInput" class="form-control {% if universities %}d-none{% endif %}" placeholder="Or type new University name...">
                        </div>

                        <!-- College -->
                        <div class="col-md-4">
                            <div class="d-flex justify-content-between align-items-center mb-1">
                                <label class="form-label mb-0">College / Institute</label>
                                <button type="button" class="btn btn-link btn-sm p-0 text-decoration-none" onclick="toggleNewField('col')">+ Add New</button>
                            </div>
                            <select name="college_id" id="colSelect" class="form-select mb-2" onchange="filterDepartments()">
                                <option value="">-- Select College --</option>
                                {% for c in colleges %}
                                <option value="{{ c.id }}" data-uni="{{ c.university_id }}">{{ c.name }}</option>
                                {% endfor %}
                            </select>
                            <input type="text" name="new_college" id="colInput" class="form-control {% if colleges %}d-none{% endif %}" placeholder="Or type new College name...">
                        </div>

                        <!-- Department -->
                        <div class="col-md-4">
                            <div class="d-flex justify-content-between align-items-center mb-1">
                                <label class="form-label mb-0">Department</label>
                                <button type="button" class="btn btn-link btn-sm p-0 text-decoration-none" onclick="toggleNewField('dept')">+ Add New</button>
                            </div>
                            <select name="department_id" id="deptSelect" class="form-select mb-2">
                                <option value="">-- Select Department --</option>
                                {% for d in departments %}
                                <option value="{{ d.id }}" data-col="{{ d.college_id }}">{{ d.name }}</option>
                                {% endfor %}
                            </select>
                            <input type="text" name="new_department" id="deptInput" class="form-control {% if departments %}d-none{% endif %}" placeholder="e.g. Computer Science">
                        </div>
                    </div>
                    <div class="small text-muted mt-3">
                        <i data-lucide="info" style="width:15px;height:15px;"></i>
                        If your University, College, or Department isn't listed yet, click <strong>+ Add New</strong> above to register it dynamically. All students and faculty who select the same department are automatically linked.
                    </div>
                </div>

                <!-- STEP 3: PERSONAL CREDENTIALS -->
                <h5 class="fw-bold mb-3 d-flex align-items-center gap-2">
                    <i data-lucide="user-check" class="text-primary"></i> 3. Personal & Login Details
                </h5>
                <div class="row g-3 mb-4">
                    <div class="col-md-6">
                        <label class="form-label">Full Name</label>
                        <input type="text" name="full_name" class="form-control" placeholder="e.g. Prof. Saurabh Pagar or Ahmed Raza" required>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Roll No. / Faculty ID</label>
                        <input type="text" name="identifier" class="form-control" placeholder="e.g. TY-CS-01 or FAC-101" required>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Class / Division</label>
                        <input type="text" name="class_division" class="form-control" value="TY-CS-A">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Choose Username</label>
                        <input type="text" name="username" class="form-control" placeholder="e.g. ahmed_cs" required>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Create Password</label>
                        <input type="password" name="password" class="form-control" placeholder="Minimum 6 characters" required>
                    </div>
                </div>

                <button type="submit" class="btn-m3-primary w-100 py-3">
                    <i data-lucide="sparkles"></i> Complete Registration & Launch Workspace
                </button>
            </form>
        </div>
    </div>
</div>

<script>
function toggleNewField(prefix) {
    const input = document.getElementById(prefix + 'Input');
    input.classList.toggle('d-none');
    if (!input.classList.contains('d-none')) input.focus();
}

function filterColleges() {
    const uniId = document.getElementById('uniSelect').value;
    const colSelect = document.getElementById('colSelect');
    Array.from(colSelect.options).forEach(opt => {
        if (!opt.value) return;
        opt.hidden = uniId && opt.getAttribute('data-uni') !== uniId;
    });
    colSelect.value = '';
    filterDepartments();
}

function filterDepartments() {
    const colId = document.getElementById('colSelect').value;
    const deptSelect = document.getElementById('deptSelect');
    Array.from(deptSelect.options).forEach(opt => {
        if (!opt.value) return;
        opt.hidden = colId && opt.getAttribute('data-col') !== colId;
    });
    deptSelect.value = '';
}
</script>
{% endblock %}
"""

# ==============================================================================
# 9. STUDENT DASHBOARD TEMPLATE (WIZARD + PROPOSAL + LOGBOOK)
# ==============================================================================
STUDENT_DASHBOARD_HTML = """
{% extends 'base.html' %}
{% block content %}

{% if not group %}
<!-- ======================================================================= -->
<!-- STATE A: DYNAMIC GROUP CREATION & TEAMMATE PAIRING WIZARD               -->
<!-- ======================================================================= -->
<div class="m3-card mb-4">
    <div class="d-flex align-items-center gap-3 mb-3">
        <div class="brand-icon-box"><i data-lucide="users"></i></div>
        <div>
            <h2 class="mb-0 fw-bold">Welcome to {{ user.profile.department.name }}!</h2>
            <div class="text-muted">Set up your academic project group or join your teammates using a group code.</div>
        </div>
    </div>

    <div class="row g-4 mt-2">
        <!-- Create New Group Card -->
        <div class="col-lg-7">
            <div class="m3-card-tonal h-100">
                <h4 class="fw-bold mb-3 d-flex align-items-center gap-2">
                    <i data-lucide="plus-circle" class="text-primary"></i> Option 1: Create a New Project Group
                </h4>
                <form method="POST">
                    {% csrf_token %}
                    <input type="hidden" name="action" value="create_group">
                    <div class="mb-3">
                        <label class="form-label">Project Group Name / Number</label>
                        <input type="text" name="group_name" class="form-control" placeholder="e.g. G-01: Team Horizon" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Select Faculty Guide (from {{ user.profile.department.name }})</label>
                        <select name="guide_id" class="form-select">
                            <option value="">-- Choose Registered Faculty Guide (or assign later) --</option>
                            {% for g in dept_guides %}
                            <option value="{{ g.id }}">Prof. {{ g.get_full_name|default:g.username }} ({{ g.profile.identifier }})</option>
                            {% endfor %}
                        </select>
                        {% if not dept_guides %}
                        <div class="small text-muted mt-1">No Faculty Guides have registered in {{ user.profile.department.name }} yet. You can create your group now and assign your guide once they register!</div>
                        {% endif %}
                    </div>
                    {% if dept_students %}
                    <div class="mb-4">
                        <label class="form-label">Add Classmates from {{ user.profile.department.name }} (Optional)</label>
                        <select name="teammate_ids" class="form-select" multiple style="height: 110px;">
                            {% for s in dept_students %}
                            <option value="{{ s.id }}">{{ s.get_full_name|default:s.username }} ({{ s.profile.identifier }})</option>
                            {% endfor %}
                        </select>
                        <div class="small text-muted mt-1">Hold Ctrl/Cmd to select multiple teammates, or share your Join Code after creating.</div>
                    </div>
                    {% endif %}
                    <button type="submit" class="btn-m3-primary w-100">
                        <i data-lucide="rocket"></i> Create Project Group
                    </button>
                </form>
            </div>
        </div>

        <!-- Join Existing Group Card -->
        <div class="col-lg-5">
            <div class="m3-card-tonal h-100 d-flex flex-column justify-content-between">
                <div>
                    <h4 class="fw-bold mb-3 d-flex align-items-center gap-2">
                        <i data-lucide="key-round" class="text-primary"></i> Option 2: Join Existing Group
                    </h4>
                    <p class="text-muted">If your teammate already created a group in <strong>{{ user.profile.department.name }}</strong>, enter the 6-character Group Join Code below:</p>
                    <form method="POST" class="mb-4">
                        {% csrf_token %}
                        <input type="hidden" name="action" value="join_group">
                        <div class="mb-3">
                            <label class="form-label">Group Join Code</label>
                            <input type="text" name="join_code" class="form-control text-uppercase fw-bold" placeholder="e.g. PT-8X2A" required>
                        </div>
                        <button type="submit" class="btn-m3-tonal w-100">
                            <i data-lucide="user-check"></i> Join Teammate's Group
                        </button>
                    </form>
                </div>

                {% if open_groups %}
                <div class="border-top pt-3">
                    <div class="small fw-bold text-muted mb-2">Active Groups in {{ user.profile.department.name }}:</div>
                    {% for og in open_groups|slice:":4" %}
                    <div class="d-flex justify-content-between align-items-center py-1 small">
                        <span><strong>{{ og.name }}</strong> ({{ og.students.count }} members)</span>
                        <span class="m3-chip chip-tonal py-1 px-2">{{ og.join_code }}</span>
                    </div>
                    {% endfor %}
                </div>
                {% endif %}
            </div>
        </div>
    </div>
</div>

{% else %}
<!-- ======================================================================= -->
<!-- STATE B: ACTIVE GROUP WORKSPACE (PROPOSAL, AI SIMILARITY & LOGBOOK)     -->
<!-- ======================================================================= -->
<div class="m3-card mb-4">
    <div class="row align-items-center g-4">
        <div class="col-lg-7">
            <div class="d-flex flex-wrap align-items-center gap-2 mb-2">
                <span class="m3-chip chip-tonal"><i data-lucide="users" style="width:15px;height:15px;"></i> {{ group.name }}</span>
                <span class="m3-chip chip-neutral" title="Share this code with teammates to join">
                    <i data-lucide="hash" style="width:15px;height:15px;"></i> Join Code: <strong>{{ group.join_code }}</strong>
                </span>
                {% if proposal %}
                    {% if proposal.status == 'APPROVED' %}
                    <span class="m3-chip chip-success"><i data-lucide="check-circle" style="width:15px;height:15px;"></i> Proposal Approved</span>
                    {% elif proposal.status == 'CHANGES' %}
                    <span class="m3-chip chip-danger"><i data-lucide="alert-circle" style="width:15px;height:15px;"></i> Changes Requested</span>
                    {% else %}
                    <span class="m3-chip chip-warning"><i data-lucide="clock" style="width:15px;height:15px;"></i> Pending Guide Review</span>
                    {% endif %}
                {% endif %}
            </div>
            <h2 class="fw-bold mb-2">{{ proposal.title|default:"Project Proposal Not Submitted Yet" }}</h2>
            <div class="text-muted d-flex flex-wrap gap-3">
                <span><strong>Team Members:</strong> {% for s in group.students.all %}{{ s.get_full_name|default:s.username }} ({{ s.profile.identifier }}){% if not forloop.last %}, {% endif %}{% endfor %}</span>
            </div>
        </div>

        <div class="col-lg-5">
            <div class="m3-card-tonal p-3">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <div class="small text-muted">Assigned Faculty Guide</div>
                        {% if group.guide %}
                        <div class="fw-bold fs-5">Prof. {{ group.guide.get_full_name|default:group.guide.username }}</div>
                        {% else %}
                        <div class="text-danger fw-medium">No Guide Selected Yet</div>
                        {% endif %}
                    </div>
                    {% if viva %}
                    <div class="text-end">
                        <div class="small text-muted">Final Viva Grade</div>
                        <span class="m3-chip chip-success fs-6">{{ viva.total_score }}/100 &bull; {{ viva.grade_badge }}</span>
                    </div>
                    {% endif %}
                </div>

                {% if not group.guide and dept_guides %}
                <form method="POST" class="mt-3 d-flex gap-2">
                    {% csrf_token %}
                    <input type="hidden" name="action" value="assign_guide">
                    <select name="guide_id" class="form-select form-select-sm" required>
                        <option value="">-- Select Registered Department Guide --</option>
                        {% for g in dept_guides %}
                        <option value="{{ g.id }}">Prof. {{ g.get_full_name|default:g.username }}</option>
                        {% endfor %}
                    </select>
                    <button type="submit" class="btn-m3-primary py-1 px-3">Assign</button>
                </form>
                {% endif %}
            </div>
        </div>
    </div>
</div>

<div class="row g-4">
    <!-- LEFT COLUMN: PROPOSAL SUBMISSION & LIVE TF-IDF SIMILARITY ENGINE -->
    <div class="col-lg-7">
        <div class="m3-card h-100">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h4 class="fw-bold mb-0 d-flex align-items-center gap-2">
                    <i data-lucide="file-text" class="text-primary"></i> Project Proposal & AI Originality Check
                </h4>
                {% if proposal %}
                <span class="m3-chip {% if proposal.similarity_score >= 60 %}chip-danger{% elif proposal.similarity_score >= 30 %}chip-warning{% else %}chip-success{% endif %}">
                    Similarity: {{ proposal.similarity_score }}%
                </span>
                {% endif %}
            </div>

            {% if proposal.guide_remarks %}
            <div class="p-3 mb-4 rounded-4" style="background: var(--m3-warning-bg); color: var(--m3-warning-text);">
                <div class="fw-bold d-flex align-items-center gap-2 mb-1">
                    <i data-lucide="message-square-warning"></i> Faculty Guide Remarks:
                </div>
                <div>{{ proposal.guide_remarks }}</div>
            </div>
            {% endif %}

            <form method="POST" enctype="multipart/form-data">
                {% csrf_token %}
                <input type="hidden" name="action" value="submit_proposal">
                <div class="mb-3">
                    <label class="form-label">Project Title</label>
                    <input type="text" name="title" id="propTitle" class="form-control" value="{{ proposal.title|default:'' }}" placeholder="Enter descriptive academic project title" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">Technical Domain / Area</label>
                    <input type="text" name="domain" class="form-control" value="{{ proposal.domain|default:'' }}" placeholder="e.g. Machine Learning, Cloud Computing, Cybersecurity, FinTech" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">Detailed Project Abstract</label>
                    <textarea name="abstract" id="propAbstract" rows="6" class="form-control" placeholder="Describe problem statement, methodology, architecture, and expected outcomes..." required>{{ proposal.abstract|default:'' }}</textarea>
                </div>

                <!-- Live AI TF-IDF Similarity Result Box -->
                <div id="simResultBox" class="m3-card-tonal p-3 mb-3 d-none">
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <span class="fw-bold d-flex align-items-center gap-2">
                            <i data-lucide="cpu" class="text-primary"></i> Scikit-Learn TF-IDF Similarity Scan
                        </span>
                        <span id="simBadge" class="m3-chip chip-tonal">0%</span>
                    </div>
                    <div class="small text-muted">Closest Match in Department / Archive: <strong id="simMatch" class="text-dark">None</strong></div>
                </div>

                <div class="mb-4">
                    <label class="form-label">Attach Synopsis / Blackbook Report (PDF, DOCX, PNG)</label>
                    <input type="file" name="report_file" class="form-control">
                    {% if proposal.report_file %}
                    <div class="small mt-2">
                        <a href="{{ proposal.report_file.url }}" target="_blank" class="text-primary fw-medium text-decoration-none">
                            <i data-lucide="external-link" style="width:15px;height:15px;"></i> View Currently Uploaded Report File
                        </a>
                    </div>
                    {% endif %}
                </div>

                <div class="d-flex flex-wrap gap-3">
                    <button type="button" onclick="runSimilarityCheck()" id="btnSimCheck" class="btn-m3-tonal">
                        <i data-lucide="sparkles"></i> Test Abstract Similarity
                    </button>
                    <button type="submit" class="btn-m3-primary flex-grow-1">
                        <i data-lucide="send"></i> Save & Submit Proposal to Guide
                    </button>
                </div>
            </form>
        </div>
    </div>

    <!-- RIGHT COLUMN: WEEKLY PROGRESS LOGBOOK -->
    <div class="col-lg-5">
        <div class="m3-card h-100">
            <h4 class="fw-bold mb-4 d-flex align-items-center gap-2">
                <i data-lucide="calendar-check-2" class="text-primary"></i> Weekly Progress Logbook
            </h4>

            <form method="POST" class="m3-card-tonal p-3 mb-4">
                {% csrf_token %}
                <input type="hidden" name="action" value="submit_log">
                <div class="row g-2 mb-2">
                    <div class="col-4">
                        <label class="form-label small">Week #</label>
                        <input type="number" name="week_number" class="form-control" value="{{ next_week }}" min="1" max="52" required>
                    </div>
                    <div class="col-8">
                        <label class="form-label small">Milestone Completed</label>
                        <input type="text" name="tasks_completed" class="form-control" placeholder="e.g. Database schema & UI" required>
                    </div>
                </div>
                <div class="mb-3">
                    <label class="form-label small">Next Week Target Plan</label>
                    <input type="text" name="next_week_plan" class="form-control" placeholder="e.g. API integration & unit tests" required>
                </div>
                <button type="submit" class="btn-m3-primary w-100 py-2">
                    <i data-lucide="plus"></i> Record Weekly Log Entry
                </button>
            </form>

            <div class="d-flex flex-column gap-3" style="max-height: 400px; overflow-y: auto;">
                {% for log in logs %}
                <div class="p-3 border rounded-4 bg-white">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <span class="fw-bold">Week {{ log.week_number }}</span>
                        {% if log.is_verified %}
                        <span class="m3-chip chip-success py-1 px-2"><i data-lucide="check" style="width:14px;height:14px;"></i> Guide Verified</span>
                        {% else %}
                        <span class="m3-chip chip-warning py-1 px-2">Awaiting Sign-Off</span>
                        {% endif %}
                    </div>
                    <div class="small mb-1"><strong>Completed:</strong> {{ log.tasks_completed }}</div>
                    <div class="small text-muted"><strong>Next Plan:</strong> {{ log.next_week_plan }}</div>
                    {% if log.guide_feedback %}
                    <div class="small text-primary mt-2 pt-2 border-top">
                        <strong>Guide Note:</strong> {{ log.guide_feedback }}
                    </div>
                    {% endif %}
                </div>
                {% empty %}
                <div class="text-center py-4 text-muted">
                    <i data-lucide="clipboard-list" class="mb-2"></i>
                    <div>No weekly logs recorded yet. Submit Week 1 above!</div>
                </div>
                {% endfor %}
            </div>
        </div>
    </div>
</div>

<script>
function runSimilarityCheck() {
    const title = document.getElementById('propTitle').value;
    const abstract = document.getElementById('propAbstract').value;
    const btn = document.getElementById('btnSimCheck');
    if (!title || !abstract) {
        alert('Please enter both your Project Title and Abstract first.');
        return;
    }
    btn.disabled = true;
    btn.innerText = 'Scanning Department Corpus...';

    const formData = new FormData();
    formData.append('title', title);
    formData.append('abstract', abstract);
    formData.append('csrfmiddlewaretoken', '{{ csrf_token }}');

    fetch("{% url 'api_check_similarity' %}", {
        method: 'POST',
        body: formData
    })
    .then(r => r.json())
    .then(data => {
        btn.disabled = false;
        btn.innerHTML = '<i data-lucide="sparkles"></i> Test Abstract Similarity';
        lucide.createIcons();

        const box = document.getElementById('simResultBox');
        const badge = document.getElementById('simBadge');
        const match = document.getElementById('simMatch');
        box.classList.remove('d-none');
        badge.innerText = data.score + '% (' + data.risk + ' RISK)';
        match.innerText = data.closest_match;
        badge.className = 'm3-chip ' + (data.score >= 60 ? 'chip-danger' : (data.score >= 30 ? 'chip-warning' : 'chip-success'));
    });
}
</script>
{% endif %}
{% endblock %}
"""

# ==============================================================================
# 10. FACULTY GUIDE DASHBOARD TEMPLATE
# ==============================================================================
GUIDE_DASHBOARD_HTML = """
{% extends 'base.html' %}
{% block content %}
<div class="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
    <div>
        <h2 class="fw-bold mb-1">Faculty Guide Mentoring Console</h2>
        <div class="text-muted">Review proposals, verify weekly student logbooks, and mentor groups in <strong>{{ user.profile.department.name }}</strong></div>
    </div>
    <div class="d-flex gap-2">
        <span class="m3-chip chip-tonal">Mentored Groups: {{ my_groups.count }}</span>
        <span class="m3-chip chip-warning">Pending Proposals: {{ pending_proposals }}</span>
        <span class="m3-chip chip-neutral">Unverified Logs: {{ unverified_logs }}</span>
    </div>
</div>

{% if unassigned_groups %}
<div class="m3-card-tonal mb-4">
    <h5 class="fw-bold mb-3 d-flex align-items-center gap-2">
        <i data-lucide="user-plus" class="text-primary"></i> Unassigned Student Groups in {{ user.profile.department.name }}
    </h5>
    <div class="row g-3">
        {% for ug in unassigned_groups %}
        <div class="col-md-6">
            <div class="bg-white p-3 rounded-4 border d-flex justify-content-between align-items-center">
                <div>
                    <div class="fw-bold">{{ ug.name }} <span class="text-muted small">({{ ug.join_code }})</span></div>
                    <div class="small text-muted">Members: {% for s in ug.students.all %}{{ s.get_full_name|default:s.username }}{% if not forloop.last %}, {% endif %}{% endfor %}</div>
                </div>
                <form method="POST">
                    {% csrf_token %}
                    <input type="hidden" name="action" value="claim_group">
                    <input type="hidden" name="group_id" value="{{ ug.id }}">
                    <button type="submit" class="btn-m3-tonal py-2 px-3">Accept Group</button>
                </form>
            </div>
        </div>
        {% endfor %}
    </div>
</div>
{% endif %}

{% for g in my_groups %}
<div class="m3-card mb-4">
    <div class="d-flex flex-wrap justify-content-between align-items-center gap-3 pb-3 mb-4 border-bottom">
        <div>
            <div class="d-flex align-items-center gap-2 mb-1">
                <span class="m3-chip chip-tonal">{{ g.name }}</span>
                <span class="m3-chip chip-neutral">Code: {{ g.join_code }}</span>
            </div>
            <div class="text-muted small">
                <strong>Students:</strong> {% for s in g.students.all %}{{ s.get_full_name|default:s.username }} ({{ s.profile.identifier }}){% if not forloop.last %}, {% endif %}{% endfor %}
            </div>
        </div>
        {% if g.proposal %}
        <div class="d-flex align-items-center gap-2">
            <span class="m3-chip {% if g.proposal.similarity_score >= 60 %}chip-danger{% elif g.proposal.similarity_score >= 30 %}chip-warning{% else %}chip-success{% endif %}">
                AI Similarity: {{ g.proposal.similarity_score }}%
            </span>
            <span class="m3-chip {% if g.proposal.status == 'APPROVED' %}chip-success{% elif g.proposal.status == 'CHANGES' %}chip-danger{% else %}chip-warning{% endif %}">
                {{ g.proposal.get_status_display }}
            </span>
        </div>
        {% endif %}
    </div>

    <div class="row g-4">
        <!-- Proposal Evaluation -->
        <div class="col-lg-7">
            <h5 class="fw-bold mb-3 d-flex align-items-center gap-2">
                <i data-lucide="file-check" class="text-primary"></i> Project Proposal Review
            </h5>
            {% if g.proposal %}
            <div class="m3-card-tonal p-4">
                <h5 class="fw-bold mb-1">{{ g.proposal.title }}</h5>
                <div class="small text-primary fw-medium mb-3">Domain: {{ g.proposal.domain }} &bull; Closest Match: {{ g.proposal.closest_match_title }}</div>
                <p class="mb-3">{{ g.proposal.abstract }}</p>

                {% if g.proposal.report_file %}
                <div class="mb-3">
                    <a href="{{ g.proposal.report_file.url }}" target="_blank" class="btn-m3-outline py-2 px-3 text-decoration-none">
                        <i data-lucide="download"></i> Open Student Uploaded Synopsis / Report
                    </a>
                </div>
                {% endif %}

                <form method="POST" class="border-top pt-3 mt-3">
                    {% csrf_token %}
                    <input type="hidden" name="action" value="review_proposal">
                    <input type="hidden" name="proposal_id" value="{{ g.proposal.id }}">
                    <div class="mb-3">
                        <label class="form-label small">Mentor Feedback / Remarks for Students</label>
                        <input type="text" name="guide_remarks" class="form-control" value="{{ g.proposal.guide_remarks }}" placeholder="Add feedback or instructions for the team...">
                    </div>
                    <div class="d-flex flex-wrap gap-2">
                        <button type="submit" name="decision" value="APPROVED" class="btn-m3-primary">
                            <i data-lucide="check-circle"></i> Approve Proposal
                        </button>
                        <button type="submit" name="decision" value="CHANGES" class="btn-m3-outline text-danger border-danger">
                            <i data-lucide="refresh-cw"></i> Request Revisions
                        </button>
                    </div>
                </form>
            </div>
            {% else %}
            <div class="m3-card-tonal text-center py-5 text-muted">
                <i data-lucide="file-clock" class="mb-2"></i>
                <div>This group has not submitted their project proposal yet.</div>
            </div>
            {% endif %}
        </div>

        <!-- Weekly Log Sign-off -->
        <div class="col-lg-5">
            <h5 class="fw-bold mb-3 d-flex align-items-center gap-2">
                <i data-lucide="list-checks" class="text-primary"></i> Weekly Logbook Sign-Off
            </h5>
            <div class="d-flex flex-column gap-3" style="max-height: 420px; overflow-y: auto;">
                {% for log in g.logs.all %}
                <div class="p-3 border rounded-4 bg-white">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <span class="fw-bold">Week {{ log.week_number }}</span>
                        {% if log.is_verified %}
                        <span class="m3-chip chip-success py-1 px-2">Verified</span>
                        {% else %}
                        <span class="m3-chip chip-warning py-1 px-2">Pending Sign-Off</span>
                        {% endif %}
                    </div>
                    <div class="small mb-1"><strong>Completed:</strong> {{ log.tasks_completed }}</div>
                    <div class="small text-muted mb-2"><strong>Next Plan:</strong> {{ log.next_week_plan }}</div>

                    {% if not log.is_verified %}
                    <form method="POST" class="d-flex gap-2 mt-2 pt-2 border-top">
                        {% csrf_token %}
                        <input type="hidden" name="action" value="verify_log">
                        <input type="hidden" name="log_id" value="{{ log.id }}">
                        <input type="text" name="guide_feedback" class="form-control form-control-sm" placeholder="Optional mentor note...">
                        <button type="submit" class="btn-m3-primary py-1 px-3">Verify</button>
                    </form>
                    {% endif %}
                </div>
                {% empty %}
                <div class="m3-card-tonal text-center py-5 text-muted">
                    No weekly progress logs submitted yet.
                </div>
                {% endfor %}
            </div>
        </div>
    </div>
</div>
{% empty %}
<div class="m3-card text-center py-5">
    <i data-lucide="users" class="text-primary mb-3" style="width:44px;height:44px;"></i>
    <h4 class="fw-bold">No Mentored Groups Yet</h4>
    <p class="text-muted mb-0">When students in <strong>{{ user.profile.department.name }}</strong> create a group and select you as their Faculty Guide, their proposals and weekly logs will appear right here automatically.</p>
</div>
{% endfor %}
{% endblock %}
"""

# ==============================================================================
# 11. COORDINATOR DASHBOARD TEMPLATE (ANALYTICS + HIERARCHY + ARCHIVES)
# ==============================================================================
COORDINATOR_DASHBOARD_HTML = """
{% extends 'base.html' %}
{% block content %}
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<div class="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
    <div>
        <h2 class="fw-bold mb-1">Department Coordinator Command Center</h2>
        <div class="text-muted">{{ user.profile.university.name }} &bull; {{ user.profile.college.name }} &bull; <strong>{{ user.profile.department.name }}</strong></div>
    </div>
    <div class="d-flex flex-wrap gap-2">
        <a href="{% url 'export_department_csv' %}" class="btn-m3-primary text-decoration-none">
            <i data-lucide="download"></i> Export Master Gradebook (CSV)
        </a>
    </div>
</div>

<!-- KPI Row -->
<div class="row g-3 mb-4">
    <div class="col-md-3 col-6">
        <div class="m3-card p-4">
            <div class="text-muted small mb-1">Active Project Groups</div>
            <div class="display-6 fw-bold text-primary">{{ groups.count }}</div>
        </div>
    </div>
    <div class="col-md-3 col-6">
        <div class="m3-card p-4">
            <div class="text-muted small mb-1">Enrolled Students</div>
            <div class="display-6 fw-bold text-dark">{{ dept_students_count }}</div>
        </div>
    </div>
    <div class="col-md-3 col-6">
        <div class="m3-card p-4">
            <div class="text-muted small mb-1">Approved Proposals</div>
            <div class="display-6 fw-bold text-success">{{ approved_count }}</div>
        </div>
    </div>
    <div class="col-md-3 col-6">
        <div class="m3-card p-4">
            <div class="text-muted small mb-1">AI Archive Corpus</div>
            <div class="display-6 fw-bold text-primary">{{ archives.count }}</div>
        </div>
    </div>
</div>

<div class="row g-4 mb-4">
    <!-- Left: Master Department Group Roster -->
    <div class="col-lg-8">
        <div class="m3-card h-100">
            <h4 class="fw-bold mb-3 d-flex align-items-center gap-2">
                <i data-lucide="layers" class="text-primary"></i> Department Project Groups & Guide Allocation
            </h4>
            <div class="table-responsive">
                <table class="table align-middle">
                    <thead class="text-muted small">
                        <tr>
                            <th>Group & Code</th>
                            <th>Proposal & AI Similarity</th>
                            <th>Faculty Guide</th>
                            <th>Viva Score</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for g in groups %}
                        <tr>
                            <td>
                                <div class="fw-bold">{{ g.name }}</div>
                                <div class="small text-muted">Code: {{ g.join_code }} &bull; {{ g.students.count }} Students</div>
                            </td>
                            <td>
                                {% if g.proposal %}
                                <div class="fw-medium">{{ g.proposal.title|truncatechars:42 }}</div>
                                <span class="m3-chip {% if g.proposal.status == 'APPROVED' %}chip-success{% else %}chip-warning{% endif %} py-0 px-2 small">
                                    {{ g.proposal.get_status_display }} ({{ g.proposal.similarity_score }}%)
                                </span>
                                {% else %}
                                <span class="text-muted small">Not Submitted</span>
                                {% endif %}
                            </td>
                            <td>
                                <form method="POST" class="d-flex gap-1">
                                    {% csrf_token %}
                                    <input type="hidden" name="action" value="assign_guide">
                                    <input type="hidden" name="group_id" value="{{ g.id }}">
                                    <select name="guide_id" class="form-select form-select-sm" onchange="this.form.submit()">
                                        <option value="">-- Unassigned --</option>
                                        {% for prof in dept_guides %}
                                        <option value="{{ prof.id }}" {% if g.guide_id == prof.id %}selected{% endif %}>
                                            Prof. {{ prof.get_full_name|default:prof.username }}
                                        </option>
                                        {% endfor %}
                                    </select>
                                </form>
                            </td>
                            <td>
                                {% if g.viva %}
                                <span class="m3-chip chip-success">{{ g.viva.total_score }}/100</span>
                                {% else %}
                                <span class="m3-chip chip-neutral">Pending</span>
                                {% endif %}
                            </td>
                        </tr>
                        {% empty %}
                        <tr>
                            <td colspan="4" class="text-center py-4 text-muted">No project groups created in {{ user.profile.department.name }} yet.</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- Right: Proposal Analytics Chart & Dynamic College Department Expansion -->
    <div class="col-lg-4">
        <div class="m3-card mb-4">
            <h5 class="fw-bold mb-3 d-flex align-items-center gap-2">
                <i data-lucide="pie-chart" class="text-primary"></i> Proposal Status Breakdown
            </h5>
            <canvas id="deptChart" height="200"></canvas>
        </div>

        <div class="m3-card">
            <h5 class="fw-bold mb-2 d-flex align-items-center gap-2">
                <i data-lucide="git-branch-plus" class="text-primary"></i> Add College Department
            </h5>
            <p class="small text-muted mb-3">New departments added under <strong>{{ user.profile.college.name }}</strong> immediately appear on the Student & Faculty registration screen.</p>
            <form method="POST">
                {% csrf_token %}
                <input type="hidden" name="action" value="add_department">
                <div class="mb-2">
                    <input type="text" name="new_dept_name" class="form-control" placeholder="e.g. Information Technology or AI & DS" required>
                </div>
                <button type="submit" class="btn-m3-tonal w-100">
                    <i data-lucide="plus"></i> Publish Department to Cloud
                </button>
            </form>
        </div>
    </div>
</div>

<!-- Scikit-Learn TF-IDF Past Project Archive Manager -->
<div class="m3-card">
    <div class="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-3">
        <div>
            <h4 class="fw-bold mb-1 d-flex align-items-center gap-2">
                <i data-lucide="database" class="text-primary"></i> Department Past Project Archive (TF-IDF Plagiarism Corpus)
            </h4>
            <div class="text-muted small">Student abstracts in {{ user.profile.department.name }} are mathematically compared against these historical records and peer submissions.</div>
        </div>
        <form method="POST">
            {% csrf_token %}
            <input type="hidden" name="action" value="seed_corpus">
            <button type="submit" class="btn-m3-tonal">
                <i data-lucide="sparkles"></i> Load 5 Benchmark AI Abstracts
            </button>
        </form>
    </div>

    <form method="POST" class="m3-card-tonal p-3 mb-4">
        {% csrf_token %}
        <input type="hidden" name="action" value="add_archive">
        <div class="row g-2">
            <div class="col-md-4">
                <input type="text" name="title" class="form-control" placeholder="Past Project Title" required>
            </div>
            <div class="col-md-2">
                <input type="text" name="year" class="form-control" value="2025" placeholder="Year" required>
            </div>
            <div class="col-md-4">
                <input type="text" name="abstract" class="form-control" placeholder="Paste project abstract summary..." required>
            </div>
            <div class="col-md-2">
                <button type="submit" class="btn-m3-primary w-100 h-100">Add Archive</button>
            </div>
        </div>
    </form>

    <div class="row g-3">
        {% for a in archives %}
        <div class="col-md-6">
            <div class="p-3 border rounded-4 bg-white h-100">
                <div class="fw-bold">{{ a.title }} <span class="m3-chip chip-neutral py-0 px-2 small">{{ a.year }}</span></div>
                <div class="small text-muted mt-1">{{ a.abstract|truncatechars:160 }}</div>
            </div>
        </div>
        {% endfor %}
    </div>
</div>

<script>
new Chart(document.getElementById('deptChart'), {
    type: 'doughnut',
    data: {
        labels: ['Approved', 'Pending Review', 'Changes Requested'],
        datasets: [{
            data: [{{ approved_count }}, {{ pending_count }}, {{ changes_count }}],
            backgroundColor: ['#137333', '#F9AB00', '#C5221F'],
            borderWidth: 0
        }]
    },
    options: { plugins: { legend: { position: 'bottom' } }, cutout: '68%' }
});
</script>
{% endblock %}
"""

# ==============================================================================
# 12. EXTERNAL EXAMINER VIVA RUBRIC TEMPLATE
# ==============================================================================
EXAMINER_VIVA_HTML = """
{% extends 'base.html' %}
{% block content %}
<div class="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
    <div>
        <h2 class="fw-bold mb-1">External Examiner Viva Assessment Portal</h2>
        <div class="text-muted">Live 100-Point Rubric Grading for <strong>{{ user.profile.department.name }}</strong> ({{ user.profile.college.name }})</div>
    </div>
    <span class="m3-chip chip-tonal"><i data-lucide="award"></i> Total Groups: {{ groups.count }}</span>
</div>

{% for g in groups %}
<div class="m3-card mb-4">
    <div class="row g-4">
        <div class="col-lg-6">
            <div class="d-flex align-items-center gap-2 mb-2">
                <span class="m3-chip chip-tonal">{{ g.name }}</span>
                <span class="m3-chip chip-neutral">Guide: {% if g.guide %}Prof. {{ g.guide.get_full_name|default:g.guide.username }}{% else %}Unassigned{% endif %}</span>
                <span class="m3-chip chip-neutral">Verified Logs: {{ g.logs.count }}</span>
            </div>
            <h4 class="fw-bold mb-2">{{ g.proposal.title|default:"Proposal Pending" }}</h4>
            <p class="text-muted mb-3">{{ g.proposal.abstract|default:"No abstract uploaded yet." }}</p>
            <div class="small text-muted mb-3">
                <strong>Examinees:</strong> {% for s in g.students.all %}{{ s.get_full_name|default:s.username }} ({{ s.profile.identifier }}){% if not forloop.last %}, {% endif %}{% endfor %}
            </div>
            {% if g.proposal and g.proposal.report_file %}
            <a href="{{ g.proposal.report_file.url }}" target="_blank" class="btn-m3-tonal text-decoration-none">
                <i data-lucide="file-text"></i> Inspect Uploaded Project Report
            </a>
            {% endif %}
        </div>

        <div class="col-lg-6">
            <form method="POST" class="m3-card-tonal p-4">
                {% csrf_token %}
                <input type="hidden" name="group_id" value="{{ g.id }}">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h5 class="fw-bold mb-0">4-Pillar Viva Rubric</h5>
                    <span class="m3-chip chip-success fs-6" id="totalBadge_{{ g.id }}">
                        Total: {{ g.viva.total_score|default:0 }} / 100
                    </span>
                </div>

                <div class="row g-3 mb-3">
                    <div class="col-sm-6">
                        <label class="form-label small">1. Problem Formulation (0-25)</label>
                        <input type="number" name="problem_clarity" class="form-control rubric-{{ g.id }}" min="0" max="25" value="{{ g.viva.problem_clarity|default:20 }}" oninput="calcViva({{ g.id }})" required>
                    </div>
                    <div class="col-sm-6">
                        <label class="form-label small">2. System Implementation (0-25)</label>
                        <input type="number" name="implementation" class="form-control rubric-{{ g.id }}" min="0" max="25" value="{{ g.viva.implementation|default:20 }}" oninput="calcViva({{ g.id }})" required>
                    </div>
                    <div class="col-sm-6">
                        <label class="form-label small">3. Presentation & Defense (0-25)</label>
                        <input type="number" name="presentation" class="form-control rubric-{{ g.id }}" min="0" max="25" value="{{ g.viva.presentation|default:20 }}" oninput="calcViva({{ g.id }})" required>
                    </div>
                    <div class="col-sm-6">
                        <label class="form-label small">4. Blackbook Documentation (0-25)</label>
                        <input type="number" name="documentation" class="form-control rubric-{{ g.id }}" min="0" max="25" value="{{ g.viva.documentation|default:20 }}" oninput="calcViva({{ g.id }})" required>
                    </div>
                </div>

                <div class="mb-3">
                    <label class="form-label small">Examiner Evaluation Remarks</label>
                    <input type="text" name="examiner_comments" class="form-control" value="{{ g.viva.examiner_comments|default:'' }}" placeholder="Enter official viva remarks...">
                </div>

                <button type="submit" class="btn-m3-primary w-100">
                    <i data-lucide="check-circle-2"></i> Certify & Publish Final Viva Grade
                </button>
            </form>
        </div>
    </div>
</div>
{% empty %}
<div class="m3-card text-center py-5 text-muted">
    No project groups found in {{ user.profile.department.name }} for evaluation yet.
</div>
{% endfor %}

<script>
function calcViva(gid) {
    let sum = 0;
    document.querySelectorAll('.rubric-' + gid).forEach(el => {
        let v = parseInt(el.value || 0, 10);
        if (v > 25) v = 25;
        if (v < 0) v = 0;
        sum += v;
    });
    document.getElementById('totalBadge_' + gid).innerText = 'Total: ' + sum + ' / 100';
}
</script>
{% endblock %}
"""

# ==============================================================================
# 13. OPTIONAL SEED COMMAND (KEPT CLEAN IN CASE EVER NEEDED)
# ==============================================================================
SEED_DATA_PY = """
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'ProTrack v4.0 runs 100% dynamically via self-service registration.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS(
            "ProTrack v4.0 is configured for 100% fresh self-service registration! Visit /signup/ in your browser to create your University, College, Department, and Role accounts dynamically."
        ))
"""

# ==============================================================================
# MASTER BUILD EXECUTION
# ==============================================================================
def build():
    print("=================================================================")
    print("  Building ProTrack v4.0 — Dynamic Google Material 3 Edition")
    print("=================================================================")

    write_file('requirements.txt', REQUIREMENTS_TXT)
    write_file('manage.py', MANAGE_PY)

    # Config package
    write_file('protrack_config/__init__.py', '')
    write_file('protrack_config/settings.py', SETTINGS_PY)
    write_file('protrack_config/urls.py', CONFIG_URLS_PY)
    write_file('protrack_config/wsgi.py', WSGI_PY)

    # Portal package
    write_file('portal/__init__.py', '')
    write_file('portal/models.py', MODELS_PY)
    write_file('portal/similarity.py', SIMILARITY_PY)
    write_file('portal/views.py', VIEWS_PY)
    write_file('portal/urls.py', PORTAL_URLS_PY)
    write_file('portal/admin.py', ADMIN_PY)
    write_file('portal/management/__init__.py', '')
    write_file('portal/management/commands/__init__.py', '')
    write_file('portal/management/commands/seed_data.py', SEED_DATA_PY)

    # Templates
    write_file('templates/base.html', BASE_HTML)
    write_file('templates/login.html', LOGIN_HTML)
    write_file('templates/signup.html', SIGNUP_HTML)
    write_file('templates/student_dashboard.html', STUDENT_DASHBOARD_HTML)
    write_file('templates/guide_dashboard.html', GUIDE_DASHBOARD_HTML)
    write_file('templates/coordinator_dashboard.html', COORDINATOR_DASHBOARD_HTML)
    write_file('templates/examiner_viva.html', EXAMINER_VIVA_HTML)

    # Reset old database & migrations so v4.0 starts 100% fresh
    if os.path.exists('db.sqlite3'):
        os.remove('db.sqlite3')
        print("  [CLEAN] Removed old db.sqlite3 for a 100% fresh start")

    if os.path.exists('portal/migrations'):
        shutil.rmtree('portal/migrations')
    os.makedirs('portal/migrations', exist_ok=True)
    write_file('portal/migrations/__init__.py', '')

    print("\nRunning Django makemigrations & migrate...")
    subprocess.run([sys.executable, 'manage.py', 'makemigrations', 'portal'], check=True)
    subprocess.run([sys.executable, 'manage.py', 'migrate'], check=True)

    print("\n=================================================================")
    print("  ProTrack v4.0 Built Successfully! (100% Fresh & Dynamic)")
    print("=================================================================")

if __name__ == '__main__':
    build()