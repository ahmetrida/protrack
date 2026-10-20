import os
import sys
import subprocess

def write_file(path, content):
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content.strip() + '\n')
    print(f"  [OK] Updated {path}")

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
# 2. GLOBAL CONFIGURATION (protrack_config)
# ==============================================================================
SETTINGS_PY = """
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = 'django-insecure-protrack-v105-royal-violet-enterprise-edition'
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

SESSION_COOKIE_AGE = 1209600  # 2 weeks session persistence
SESSION_SAVE_EVERY_REQUEST = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
"""

CONFIG_URLS_PY = """
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('', include('portal.urls')),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
"""

WSGI_PY = """
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'protrack_config.settings')
application = get_wsgi_application()
"""

# ==============================================================================
# 3. DATABASE MODELS & VALIDATORS (portal/models.py)
# ==============================================================================
MODELS_PY = """
import re
import random
import string
from django.db import models
from django.contrib.auth.models import User

def generate_join_code():
    \"\"\"Generates a unique, exactly 5-character uppercase alphanumeric join code.\"\"\"
    chars = string.ascii_uppercase + string.digits
    for _ in range(100):
        code = ''.join(random.choices(chars, k=5))
        try:
            if not ProjectGroup.objects.filter(join_code=code).exists():
                return code
        except Exception:
            return code
    return ''.join(random.choices(chars, k=5))

def normalize_whatsapp(raw_phone):
    if not raw_phone:
        return ''
    digits = re.sub(r'[^0-9]', '', str(raw_phone))
    if len(digits) == 10:
        return '91' + digits
    return digits

def format_social_url(handle_or_url, base_domain):
    if not handle_or_url:
        return ''
    val = handle_or_url.strip()
    if val.startswith('http://') or val.startswith('https://'):
        return val
    val = val.lstrip('@').strip('/')
    return f"https://{base_domain}/{val}"

class University(models.Model):
    name = models.CharField(max_length=200, unique=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
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
        ('ADMIN', 'Institution Admin'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='STUDENT')
    is_examiner = models.BooleanField(default=False, help_text="Assigned by Admin to Faculty Guides")

    university = models.ForeignKey(University, on_delete=models.SET_NULL, null=True, blank=True)
    college = models.ForeignKey(College, on_delete=models.SET_NULL, null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)

    preferred_guide = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='registered_students'
    )

    identifier = models.CharField(max_length=60, blank=True, help_text="Roll Call, Faculty ID, or Admin ID")
    class_division = models.CharField(max_length=60, blank=True, default="Class-A")

    id_proof_front = models.FileField(upload_to='admin_proofs/', null=True, blank=True)
    id_proof_back = models.FileField(upload_to='admin_proofs/', null=True, blank=True)
    is_verified_admin = models.BooleanField(default=False)

    avatar = models.FileField(upload_to='avatars/', null=True, blank=True)
    bio = models.CharField(max_length=280, blank=True, default='')
    whatsapp_number = models.CharField(max_length=25, blank=True, default='')
    github_handle = models.CharField(max_length=200, blank=True, default='')
    youtube_handle = models.CharField(max_length=200, blank=True, default='')
    instagram_handle = models.CharField(max_length=200, blank=True, default='')
    form_drafts = models.TextField(blank=True, default='{}')

    @property
    def has_avatar(self):
        try:
            return bool(self.avatar and self.avatar.name and self.avatar.url)
        except Exception:
            return False

    @property
    def avatar_url(self):
        try:
            return self.avatar.url if self.has_avatar else ''
        except Exception:
            return ''

    @property
    def initials(self):
        full = self.user.get_full_name().strip()
        if full:
            parts = full.split()
            return (parts[0][0] + (parts[-1][0] if len(parts) > 1 else '')).upper()
        return self.user.username[:2].upper()

    @property
    def clean_whatsapp(self):
        return normalize_whatsapp(self.whatsapp_number)

    @property
    def github_url(self):
        return format_social_url(self.github_handle, 'github.com')

    @property
    def youtube_url(self):
        val = self.youtube_handle.strip()
        if not val:
            return ''
        if val.startswith('http'):
            return val
        val = val.lstrip('@')
        return f"https://youtube.com/@{val}"

    @property
    def instagram_url(self):
        return format_social_url(self.instagram_handle, 'instagram.com')

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

    def save(self, *args, **kwargs):
        if not self.join_code or len(self.join_code) != 5 or ProjectGroup.objects.filter(join_code=self.join_code).exclude(pk=self.pk).exists():
            self.join_code = generate_join_code()
        super().save(*args, **kwargs)

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
    domain = models.CharField(max_length=120, default='Software Engineering')
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
        "title": "Automated Attendance System Using Computer Vision (2024)",
        "abstract": "An automated classroom attendance monitoring application built with OpenCV and deep metric facial encodings to mark student attendance in real time via camera feeds and export CSV sheets."
    },
    {
        "title": "Campus Placement & Recruitment Management Portal (2024)",
        "abstract": "A centralized web platform connecting graduating students with recruiters, featuring resume parsing, GPA eligibility filtering, interview scheduling, and placement analytics."
    },
    {
        "title": "Decentralized Academic Credential Verification Platform (2025)",
        "abstract": "A tamper-proof academic certificate verification portal using cryptographic SHA-256 hashes and smart contracts to eliminate counterfeit diplomas and enable instant employer validation."
    },
    {
        "title": "Smart Hospital Outpatient Queue & E-Prescription System (2025)",
        "abstract": "A clinical web application enabling patients to book appointments online, track live consultation queues, and generate digital prescriptions with automated inventory alerts."
    },
    {
        "title": "Machine Learning Crop Disease Detection Advisory System (2025)",
        "abstract": "An agricultural support portal where users upload plant leaf images to classify diseases using convolutional neural networks and receive localized treatment recommendations."
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
        return {"score": 0.0, "closest_match": "Provide at least 4 words for analysis", "risk": "LOW"}

    corpus_records = []

    archives = PastProjectArchive.objects.filter(department=department) if department else PastProjectArchive.objects.all()
    for a in archives:
        corpus_records.append({
            "title": f"{a.title} ({a.year} Archive)",
            "text": clean_text(f"{a.title} {a.title} {a.abstract}"),
            "raw_title": a.title
        })

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

    for item in FALLBACK_CORPUS:
        corpus_records.append({
            "title": item["title"],
            "text": clean_text(f"{item['title']} {item['title']} {item['abstract']}"),
            "raw_title": item["title"]
        })

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
            "closest_match": best_match if best_score >= 8.0 else "Unique Concept (Low Overlap)",
            "risk": risk
        }
    except Exception:
        return {"score": 0.0, "closest_match": "Unique Concept", "risk": "LOW"}
"""

# ==============================================================================
# 5. VIEWS, ACCESS CONTROL & CONTROLLERS (portal/views.py)
# ==============================================================================
VIEWS_PY = """
import re
import csv
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.views.decorators.cache import never_cache
from django.db.models import Q
from .models import (
    University, College, Department, UserProfile,
    ProjectGroup, ProjectProposal, WeeklyLog,
    VivaEvaluation, PastProjectArchive, Notification,
    generate_join_code
)
from .similarity import check_abstract_similarity, FALLBACK_CORPUS

ALLOWED_PROOF_EXT = ('.jpg', '.jpeg', '.png', '.webp', '.pdf')
ALLOWED_AVATAR_EXT = ('.jpg', '.jpeg', '.png', '.webp')
ALLOWED_REPORT_EXT = ('.pdf', '.docx', '.doc', '.png', '.jpg', '.jpeg')

def notify_users(users, message):
    for u in users:
        if u and not u.is_superuser:
            Notification.objects.create(user=u, message=message)

def validate_file_ext(uploaded_file, allowed_tuple):
    if not uploaded_file:
        return False
    return uploaded_file.name.lower().endswith(allowed_tuple)

def get_authorized_profile_ids(viewer_user):
    \"\"\"
    Enforces strict hierarchical role-based visibility for directories and public profiles.
    Superusers are NEVER included in regular user querysets.
    \"\"\"
    base_qs = UserProfile.objects.filter(user__is_superuser=False)
    if viewer_user.is_superuser:
        return list(base_qs.values_list('id', flat=True))

    viewer_profile = getattr(viewer_user, 'profile', None)
    if not viewer_profile:
        return []

    if viewer_profile.role == 'ADMIN':
        if viewer_profile.college:
            return list(base_qs.filter(college=viewer_profile.college).values_list('id', flat=True))
        elif viewer_profile.university:
            return list(base_qs.filter(university=viewer_profile.university).values_list('id', flat=True))
        return [viewer_profile.id]

    elif viewer_profile.role == 'GUIDE':
        if viewer_profile.department:
            return list(
                base_qs.filter(
                    department=viewer_profile.department,
                    role__in=['STUDENT', 'GUIDE']
                ).values_list('id', flat=True)
            )
        return [viewer_profile.id]

    elif viewer_profile.role == 'STUDENT':
        allowed_user_ids = {viewer_user.id}
        if viewer_profile.preferred_guide_id:
            allowed_user_ids.add(viewer_profile.preferred_guide_id)

        for grp in viewer_user.student_groups.all():
            for member in grp.students.filter(is_superuser=False):
                allowed_user_ids.add(member.id)
            if grp.guide_id:
                allowed_user_ids.add(grp.guide_id)
            if hasattr(grp, 'viva') and grp.viva and grp.viva.examiner_id:
                allowed_user_ids.add(grp.viva.examiner_id)

        if viewer_profile.department:
            dept_examiner_ids = base_qs.filter(
                department=viewer_profile.department,
                is_examiner=True
            ).values_list('user_id', flat=True)
            allowed_user_ids.update(dept_examiner_ids)

        return list(base_qs.filter(user_id__in=allowed_user_ids).values_list('id', flat=True))

    return [viewer_profile.id]

def can_view_profile(viewer_user, target_profile):
    if target_profile.user.is_superuser:
        return viewer_user.is_superuser
    if viewer_user.is_superuser or viewer_user.id == target_profile.user_id:
        return True
    allowed_ids = get_authorized_profile_ids(viewer_user)
    return target_profile.id in allowed_ids

# ==============================================================================
# API ENDPOINTS: HIERARCHY, USERNAME DUPLICATION CHECK, CLASSMATE SEARCH, DRAFTS
# ==============================================================================
def api_hierarchy(request):
    universities = list(University.objects.values('id', 'name'))
    colleges = list(College.objects.values('id', 'university_id', 'name'))
    departments = list(Department.objects.values('id', 'college_id', 'name', 'academic_year'))
    guides = []
    for g in UserProfile.objects.filter(role='GUIDE', user__is_superuser=False).select_related('user'):
        guides.append({
            'id': g.user.id,
            'department_id': g.department_id,
            'name': g.user.get_full_name() or g.user.username,
            'identifier': g.identifier
        })
    return JsonResponse({
        'universities': universities,
        'colleges': colleges,
        'departments': departments,
        'guides': guides,
    })

def api_check_username(request):
    \"\"\"Checks if a username is taken and returns guaranteed non-duplicate suggestions.\"\"\"
    username = request.GET.get('username', '').strip().lower()
    full_name = request.GET.get('full_name', '').strip().lower()
    identifier = request.GET.get('identifier', '').strip().lower()

    exists = User.objects.filter(username__iexact=username).exists() if username else False

    clean_name = re.sub(r'[^a-z0-9\\s]', '', full_name)
    clean_id = re.sub(r'[^a-z0-9]', '', identifier)
    parts = [p for p in clean_name.split() if p]

    candidates = []
    if parts:
        base = ''.join(parts)
        dot = f"{parts[0]}.{parts[-1]}" if len(parts) > 1 else f"{parts[0]}.user"
        id_combo = f"{parts[0]}_{clean_id}" if clean_id else f"{parts[0]}2026"
        candidates.extend([base, dot, id_combo])
        for suffix in range(1, 50):
            candidates.append(f"{parts[0]}.{parts[-1] if len(parts) > 1 else 'user'}{suffix}")
            candidates.append(f"{base}{suffix}")
    else:
        candidates = ['johndoe', 'john.doe', 'jdoe2026', 'john.user1', 'johndoe99']

    existing_lower = set(
        u.lower() for u in User.objects.filter(username__in=candidates).values_list('username', flat=True)
    )
    suggestions = []
    for cand in candidates:
        if len(cand) >= 3 and cand.lower() not in existing_lower and cand.lower() != username and cand not in suggestions:
            if not User.objects.filter(username__iexact=cand).exists():
                suggestions.append(cand)
            if len(suggestions) >= 3:
                break

    return JsonResponse({
        'username': username,
        'exists': exists,
        'suggestions': suggestions,
    })

@login_required
def api_search_classmates(request):
    \"\"\"Interactive classmate search restricted strictly to the student's department.\"\"\"
    if request.user.is_superuser:
        return JsonResponse({'results': []})
    profile = getattr(request.user, 'profile', None)
    if not profile or not profile.department:
        return JsonResponse({'results': []})

    q = request.GET.get('q', '').strip()
    qs = UserProfile.objects.filter(
        department=profile.department,
        role='STUDENT',
        user__is_superuser=False,
        user__student_groups__isnull=True
    ).exclude(user=request.user).select_related('user', 'department')

    if q:
        qs = qs.filter(
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q) |
            Q(user__username__icontains=q) |
            Q(identifier__icontains=q)
        )

    results = []
    for p in qs[:20]:
        results.append({
            'user_id': p.user.id,
            'full_name': p.user.get_full_name() or p.user.username,
            'username': p.user.username,
            'identifier': p.identifier,
            'class_division': p.class_division,
            'department': p.department.name if p.department else '',
            'avatar_url': p.avatar_url,
            'initials': p.initials,
        })
    return JsonResponse({'results': results})

@login_required
def api_sync_drafts(request):
    \"\"\"Synchronizes unfinished form drafts with the authenticated user's account.\"\"\"
    if request.user.is_superuser:
        return JsonResponse({'status': 'isolated'})

    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        try:
            payload = json.loads(request.body.decode('utf-8'))
            current_drafts = json.loads(profile.form_drafts or '{}')
            form_key = payload.get('form_key', '')
            fields = payload.get('fields', {})
            clear = payload.get('clear', False)
            if form_key:
                if clear:
                    current_drafts.pop(form_key, None)
                else:
                    # Never store sensitive secrets
                    safe_fields = {
                        k: v for k, v in fields.items()
                        if 'password' not in k.lower() and 'csrf' not in k.lower() and 'token' not in k.lower()
                    }
                    current_drafts[form_key] = safe_fields
                profile.form_drafts = json.dumps(current_drafts)
                profile.save(update_fields=['form_drafts'])
            return JsonResponse({'status': 'saved'})
        except Exception:
            return JsonResponse({'status': 'error'}, status=400)

    try:
        data = json.loads(profile.form_drafts or '{}')
    except Exception:
        data = {}
    return JsonResponse({'status': 'ok', 'drafts': data})

# ==============================================================================
# AUTHENTICATION & SESSION PERSISTENCE (REGULAR USERS VS SUPERADMIN ISOLATION)
# ==============================================================================
@never_cache
def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('superadmin_dashboard')
        return redirect('dashboard_router')

    if request.method == 'POST':
        u = request.POST.get('username', '').strip()
        p = request.POST.get('password', '').strip()
        user = authenticate(request, username=u, password=p)
        if user:
            if user.is_superuser:
                messages.error(request, "Invalid username or password. Please use your authorized login route.")
                return redirect('login')
            login(request, user)
            request.session['play_success_sound'] = True
            messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
            return redirect('dashboard_router')
        else:
            messages.error(request, "Invalid username or password. Please verify your credentials or create an account.")

    return render(request, 'login.html', {
        'total_universities': University.objects.count(),
        'total_colleges': College.objects.count(),
        'total_departments': Department.objects.count(),
        'total_users': UserProfile.objects.filter(user__is_superuser=False).count(),
    })

@never_cache
def signup_view(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('superadmin_dashboard')
        return redirect('dashboard_router')

    if request.method == 'POST':
        role = request.POST.get('role', 'STUDENT').strip().upper()
        if role not in ('STUDENT', 'GUIDE', 'ADMIN'):
            role = 'STUDENT'

        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        identifier = request.POST.get('identifier', '').strip()
        class_division = request.POST.get('class_division', 'Class-A').strip()
        whatsapp_number = request.POST.get('whatsapp_number', '').strip()

        if len(full_name) < 2:
            messages.error(request, "Full Name is required (minimum 2 characters).")
            return redirect('signup')

        if not email or '@' not in email:
            messages.error(request, "A valid Email Address is required.")
            return redirect('signup')

        if not re.match(r'^[a-zA-Z0-9_.-]{3,30}$', username):
            messages.error(request, "Username must be 3–30 characters using letters, numbers, dots, hyphens, or underscores.")
            return redirect('signup')

        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, f"Username '@{username}' is already taken. Please select an available username.")
            return redirect('signup')

        if len(password) < 6:
            messages.error(request, "Password is required and must be at least 6 characters long.")
            return redirect('signup')

        if not identifier:
            messages.error(request, "Roll Call, Faculty ID, or Admin ID is required.")
            return redirect('signup')

        uni_id = request.POST.get('university_id', '').strip()
        col_id = request.POST.get('college_id', '').strip()
        dept_id = request.POST.get('department_id', '').strip()

        id_front = None
        id_back = None
        preferred_guide_user = None

        if role == 'ADMIN':
            id_front = request.FILES.get('id_proof_front')
            id_back = request.FILES.get('id_proof_back')
            if not id_front or not id_back:
                messages.error(request, "Admin registration requires both Front and Back ID Proof uploads.")
                return redirect('signup')
            if not (validate_file_ext(id_front, ALLOWED_PROOF_EXT) and validate_file_ext(id_back, ALLOWED_PROOF_EXT)):
                messages.error(request, "ID Proofs must be valid image or PDF files (.jpg, .png, .webp, .pdf).")
                return redirect('signup')

            new_uni = request.POST.get('new_university', '').strip()
            new_col = request.POST.get('new_college', '').strip()
            new_dept = request.POST.get('new_department', '').strip()

            if new_uni:
                university, _ = University.objects.get_or_create(name=new_uni)
            elif uni_id.isdigit():
                university = University.objects.filter(id=int(uni_id)).first()
            else:
                university = None

            if not university:
                messages.error(request, "Admin: Please select an existing University or enter a new University name.")
                return redirect('signup')

            if new_col:
                college, _ = College.objects.get_or_create(university=university, name=new_col)
            elif col_id.isdigit():
                college = College.objects.filter(id=int(col_id), university=university).first()
            else:
                college = None

            if not college:
                messages.error(request, "Admin: Please select an existing College or enter a new College name.")
                return redirect('signup')

            if new_dept:
                department, _ = Department.objects.get_or_create(college=college, name=new_dept)
            elif dept_id.isdigit():
                department = Department.objects.filter(id=int(dept_id), college=college).first()
            else:
                department = None

            if not department:
                messages.error(request, "Admin: Please select an existing Department or enter a new Department name.")
                return redirect('signup')

        else:
            if not (uni_id.isdigit() and col_id.isdigit() and dept_id.isdigit()):
                messages.error(request, "Please select your University, College, and Department from the required dropdown menus.")
                return redirect('signup')

            university = University.objects.filter(id=int(uni_id)).first()
            college = College.objects.filter(id=int(col_id), university=university).first()
            department = Department.objects.filter(id=int(dept_id), college=college).first()

            if not (university and college and department):
                messages.error(request, "Invalid institution hierarchy selected. Please choose valid options from the dropdowns.")
                return redirect('signup')

            if role == 'STUDENT':
                guide_id = request.POST.get('preferred_guide_id', '').strip()
                if guide_id.isdigit():
                    preferred_guide_user = User.objects.filter(
                        id=int(guide_id),
                        is_superuser=False,
                        profile__department=department,
                        profile__role='GUIDE'
                    ).first()

        parts = full_name.split(' ', 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ''

        user = User.objects.create_user(
            username=username,
            email=email,
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
            preferred_guide=preferred_guide_user,
            identifier=identifier,
            class_division=class_division if role == 'STUDENT' else '',
            id_proof_front=id_front,
            id_proof_back=id_back,
            is_verified_admin=(role == 'ADMIN'),
            whatsapp_number=whatsapp_number
        )

        dept_admins = User.objects.filter(is_superuser=False, profile__department=department, profile__role='ADMIN').exclude(id=user.id)
        notify_users(dept_admins, f"New {role.title()} registered in {department.name}: {full_name} ({identifier}).")
        if preferred_guide_user:
            notify_users([preferred_guide_user], f"Student {full_name} ({identifier}) selected you as their Project Guide.")

        login(request, user)
        request.session['play_success_sound'] = True
        messages.success(request, f"Profile created! Welcome to {department.name}, {full_name}.")
        return redirect('dashboard_router')

    guides_list = UserProfile.objects.filter(role='GUIDE', user__is_superuser=False).select_related('user', 'department')
    return render(request, 'signup.html', {
        'universities': University.objects.all(),
        'colleges': College.objects.all(),
        'departments': Department.objects.all(),
        'guides_list': guides_list,
    })

def logout_view(request):
    was_super = request.user.is_authenticated and request.user.is_superuser
    logout(request)
    if was_super:
        return redirect('superadmin_login')
    messages.info(request, "You have signed out safely.")
    return redirect('login')

@login_required
@never_cache
def dashboard_router(request):
    if request.user.is_superuser:
        return redirect('superadmin_dashboard')
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if profile.role == 'ADMIN':
        return redirect('admin_dashboard')
    elif profile.role == 'GUIDE':
        return redirect('guide_dashboard')
    return redirect('student_dashboard')

@login_required
def mark_notifications_read(request):
    if request.user.is_superuser:
        return redirect('superadmin_dashboard')
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect(request.META.get('HTTP_REFERER', 'dashboard_router'))

# ==============================================================================
# DEDICATED PRIVATE SUPERADMIN FLOW (/superadmin-access/ & /superadmin-console/)
# ==============================================================================
@never_cache
def superadmin_login_view(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('superadmin_dashboard')
        return redirect('dashboard_router')

    if request.method == 'POST':
        u = request.POST.get('username', '').strip()
        p = request.POST.get('password', '').strip()
        user = authenticate(request, username=u, password=p)
        if user and user.is_superuser:
            # Ensure a superuser never has a regular student/guide/admin UserProfile
            UserProfile.objects.filter(user=user).delete()
            login(request, user)
            request.session['play_success_sound'] = True
            messages.success(request, "Superadmin session authenticated.")
            return redirect('superadmin_dashboard')
        else:
            messages.error(request, "Unauthorized credentials for Superadmin console.")

    return render(request, 'superadmin_login.html')

@login_required(login_url='/superadmin-access/')
@never_cache
def superadmin_dashboard_view(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("403 Forbidden: Restricted access.")

    # Ensure superuser is never represented in regular UserProfile records
    UserProfile.objects.filter(user=request.user).delete()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_superadmin_profile':
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip()
            new_username = request.POST.get('username', '').strip()

            if new_username and new_username != request.user.username:
                if User.objects.filter(username__iexact=new_username).exclude(id=request.user.id).exists():
                    messages.error(request, f"Username '{new_username}' is already in use.")
                    return redirect('superadmin_dashboard')
                request.user.username = new_username

            request.user.first_name = first_name
            request.user.last_name = last_name
            request.user.email = email
            request.user.save()
            request.session['play_success_sound'] = True
            messages.success(request, "Superadmin private profile updated.")

        elif action == 'update_superadmin_password':
            new_pass = request.POST.get('new_password', '').strip()
            if len(new_pass) >= 6:
                request.user.set_password(new_pass)
                request.user.save()
                update_session_auth_hash(request, request.user)
                request.session['play_success_sound'] = True
                messages.success(request, "Superadmin password updated.")
            else:
                messages.error(request, "Password must be at least 6 characters.")

        elif action == 'delete_user':
            uid = request.POST.get('user_id', '')
            if uid.isdigit():
                User.objects.filter(id=int(uid), is_superuser=False).delete()
                request.session['play_success_sound'] = True
                messages.success(request, "Selected user record deleted.")

        elif action == 'delete_group':
            gid = request.POST.get('group_id', '')
            if gid.isdigit():
                ProjectGroup.objects.filter(id=int(gid)).delete()
                request.session['play_success_sound'] = True
                messages.success(request, "Selected project group deleted.")

        return redirect('superadmin_dashboard')

    universities = University.objects.all()
    colleges = College.objects.select_related('university').all()
    departments = Department.objects.select_related('college__university').all()
    profiles = UserProfile.objects.filter(user__is_superuser=False).select_related('user', 'university', 'college', 'department')
    groups = ProjectGroup.objects.select_related('department__college__university', 'guide').prefetch_related('students')

    return render(request, 'superadmin_dashboard.html', {
        'universities': universities,
        'colleges': colleges,
        'departments': departments,
        'profiles': profiles,
        'groups': groups,
        'active_tab': 'superadmin_dashboard',
    })

# ==============================================================================
# PUBLIC PROFILE VIEW & ROLE-SCOPED SETTINGS / DIRECTORY
# ==============================================================================
@login_required
def public_profile_view(request, username):
    target_user = get_object_or_404(User, username=username, is_superuser=False)
    target_profile = get_object_or_404(UserProfile, user=target_user)

    if not can_view_profile(request.user, target_profile):
        messages.error(request, "Access Denied: This profile is outside your authorized institutional or group scope.")
        return redirect('dashboard_router')

    student_group = target_user.student_groups.first() if target_profile.role == 'STUDENT' else None
    guided_groups = ProjectGroup.objects.filter(guide=target_user) if target_profile.role == 'GUIDE' else []

    return render(request, 'public_profile.html', {
        'target_user': target_user,
        'target_profile': target_profile,
        'student_group': student_group,
        'guided_groups': guided_groups,
        'active_tab': 'profile_settings',
        'notifications': [] if request.user.is_superuser else request.user.notifications.filter(is_read=False)[:6],
    })

@login_required
def profile_settings_view(request):
    if request.user.is_superuser:
        return redirect('superadmin_dashboard')

    profile = request.user.profile
    dept = profile.department

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_profile':
            full_name = request.POST.get('full_name', '').strip()
            email = request.POST.get('email', '').strip()
            identifier = request.POST.get('identifier', '').strip()
            class_division = request.POST.get('class_division', '').strip()
            bio = request.POST.get('bio', '').strip()
            whatsapp = request.POST.get('whatsapp_number', '').strip()
            github = request.POST.get('github_handle', '').strip()
            youtube = request.POST.get('youtube_handle', '').strip()
            instagram = request.POST.get('instagram_handle', '').strip()
            avatar_file = request.FILES.get('avatar')

            if not full_name or not identifier:
                messages.error(request, "Full Name and ID/Roll Call are required fields.")
                return redirect('profile_settings')

            parts = full_name.split(' ', 1)
            request.user.first_name = parts[0]
            request.user.last_name = parts[1] if len(parts) > 1 else ''
            if email:
                request.user.email = email
            request.user.save()

            profile.identifier = identifier
            if class_division:
                profile.class_division = class_division
            profile.bio = bio[:280]
            profile.whatsapp_number = whatsapp
            profile.github_handle = github
            profile.youtube_handle = youtube
            profile.instagram_handle = instagram

            if avatar_file:
                if validate_file_ext(avatar_file, ALLOWED_AVATAR_EXT):
                    profile.avatar = avatar_file
                else:
                    messages.error(request, "Profile photo must be a valid image (.jpg, .png, .webp).")
                    return redirect('profile_settings')

            if profile.role == 'STUDENT':
                pref_guide_id = request.POST.get('preferred_guide_id', '')
                if pref_guide_id.isdigit():
                    g_user = User.objects.filter(
                        id=int(pref_guide_id),
                        is_superuser=False,
                        profile__department=dept,
                        profile__role='GUIDE'
                    ).first()
                    if g_user:
                        profile.preferred_guide = g_user

            profile.save()
            request.session['play_success_sound'] = True
            messages.success(request, "Your profile, avatar, and contact handles have been saved!")
            return redirect('profile_settings')

        elif action == 'change_password':
            new_pass = request.POST.get('new_password', '').strip()
            if len(new_pass) < 6:
                messages.error(request, "New password must be at least 6 characters.")
            else:
                request.user.set_password(new_pass)
                request.user.save()
                update_session_auth_hash(request, request.user)
                request.session['play_success_sound'] = True
                messages.success(request, "Your password has been updated securely.")
            return redirect('profile_settings')

        elif action == 'delete_account':
            confirm_text = request.POST.get('confirm_delete', '').strip()
            if confirm_text == 'DELETE':
                u = request.user
                logout(request)
                u.delete()
                messages.info(request, "Your account and associated profile have been permanently deleted.")
                return redirect('login')
            else:
                messages.error(request, "Please type DELETE in uppercase to confirm account deletion.")
                return redirect('profile_settings')

    # Strict Role-Based & Institution-Scoped Contact Directory
    allowed_ids = get_authorized_profile_ids(request.user)
    directory_qs = UserProfile.objects.filter(
        id__in=allowed_ids,
        user__is_superuser=False
    ).select_related('user', 'department', 'college', 'university')

    role_filter = request.GET.get('role_filter', 'ALL').strip()
    search_q = request.GET.get('q', '').strip()

    if role_filter in ('STUDENT', 'GUIDE', 'ADMIN'):
        directory_qs = directory_qs.filter(role=role_filter)
    elif role_filter == 'EXAMINER':
        directory_qs = directory_qs.filter(is_examiner=True)

    if search_q:
        directory_qs = directory_qs.filter(
            Q(user__first_name__icontains=search_q) |
            Q(user__last_name__icontains=search_q) |
            Q(user__username__icontains=search_q) |
            Q(identifier__icontains=search_q)
        )

    dept_guides = User.objects.filter(
        is_superuser=False,
        profile__department=dept,
        profile__role='GUIDE'
    ).select_related('profile') if dept else []

    college_admins = UserProfile.objects.filter(
        college=profile.college,
        role='ADMIN',
        user__is_superuser=False
    ).select_related('user', 'college', 'university') if profile.role == 'ADMIN' and profile.college else []

    return render(request, 'settings_profile.html', {
        'directory_profiles': directory_qs,
        'role_filter': role_filter,
        'search_q': search_q,
        'dept_guides': dept_guides,
        'college_admins': college_admins,
        'active_tab': 'profile_settings',
        'notifications': request.user.notifications.filter(is_read=False)[:6],
    })

# ==============================================================================
# STUDENT WORKSPACE & 5-CHAR GROUP JOIN CODE VALIDATION
# ==============================================================================
@login_required
def student_dashboard(request):
    if request.user.is_superuser:
        return redirect('superadmin_dashboard')

    profile = request.user.profile
    if profile.role != 'STUDENT':
        return redirect('dashboard_router')

    dept = profile.department
    group = request.user.student_groups.first()

    dept_guides = User.objects.filter(
        is_superuser=False,
        profile__department=dept,
        profile__role='GUIDE'
    ).select_related('profile')
    dept_students = User.objects.filter(
        is_superuser=False,
        profile__department=dept,
        profile__role='STUDENT',
        student_groups__isnull=True
    ).exclude(id=request.user.id).select_related('profile')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create_group' and not group:
            group_name = request.POST.get('group_name', '').strip()
            guide_id = request.POST.get('guide_id', '').strip()
            teammate_ids = request.POST.getlist('teammate_ids')

            if not group_name:
                messages.error(request, "Project Group Name is required.")
                return redirect('student_dashboard')

            guide_user = None
            if guide_id.isdigit():
                guide_user = User.objects.filter(
                    id=int(guide_id),
                    is_superuser=False,
                    profile__department=dept,
                    profile__role='GUIDE'
                ).first()
            elif profile.preferred_guide:
                guide_user = profile.preferred_guide

            unique_code = generate_join_code()
            new_group = ProjectGroup.objects.create(
                name=group_name,
                join_code=unique_code,
                department=dept,
                guide=guide_user
            )
            new_group.students.add(request.user)

            for tid in teammate_ids:
                if str(tid).isdigit():
                    tm = User.objects.filter(
                        id=int(tid),
                        is_superuser=False,
                        profile__department=dept,
                        profile__role='STUDENT'
                    ).first()
                    if tm and not tm.student_groups.exists():
                        new_group.students.add(tm)
                        notify_users([tm], f"{request.user.get_full_name()} added you to project group '{new_group.name}'.")

            if guide_user:
                notify_users([guide_user], f"Project group '{new_group.name}' is assigned under your mentorship.")
            request.session['play_success_sound'] = True
            messages.success(request, f"Group '{new_group.name}' created! Share 5-character Join Code {new_group.join_code} with unregistered or eligible classmates.")
            return redirect('student_dashboard')

        elif action == 'join_group' and not group:
            raw_code = request.POST.get('join_code', '').strip().upper()
            if not re.match(r'^[A-Z0-9]{5}$', raw_code):
                messages.error(request, "Invalid Join Code format. Please enter a valid 5-character alphanumeric group code (e.g. A8K2P).")
                return redirect('student_dashboard')

            target_group = ProjectGroup.objects.filter(join_code=raw_code, department=dept).first()
            if not target_group:
                messages.error(request, f"No active group in {dept.name} matches the 5-character code '{raw_code}'.")
            else:
                target_group.students.add(request.user)
                notify_users(target_group.students.exclude(id=request.user.id), f"{request.user.get_full_name()} joined {target_group.name}!")
                request.session['play_success_sound'] = True
                messages.success(request, f"Successfully joined '{target_group.name}'!")
            return redirect('student_dashboard')

        elif action == 'submit_proposal' and group:
            title = request.POST.get('title', '').strip()
            domain = request.POST.get('domain', '').strip()
            abstract = request.POST.get('abstract', '').strip()
            report_file = request.FILES.get('report_file')

            if len(title) < 5 or not domain or len(abstract.split()) < 6:
                messages.error(request, "Project Title, Technical Domain, and a detailed Abstract (at least 6 words) are required.")
                return redirect('student_dashboard')

            if report_file and not validate_file_ext(report_file, ALLOWED_REPORT_EXT):
                messages.error(request, "Report file must be PDF, DOCX, PNG, or JPG.")
                return redirect('student_dashboard')

            sim_res = check_abstract_similarity(title, abstract, department=dept, exclude_group_id=group.id)
            proposal, _ = ProjectProposal.objects.get_or_create(group=group)
            proposal.title = title
            proposal.domain = domain
            proposal.abstract = abstract
            proposal.similarity_score = sim_res['score']
            proposal.closest_match_title = sim_res['closest_match']
            proposal.status = 'PENDING'
            if report_file:
                proposal.report_file = report_file
            proposal.save()

            if group.guide:
                notify_users([group.guide], f"{group.name} submitted proposal '{title}' (Similarity: {sim_res['score']}%).")
            request.session['play_success_sound'] = True
            messages.success(request, f"Proposal submitted to your guide! AI Similarity Score: {sim_res['score']}%.")
            return redirect('student_dashboard')

        elif action == 'submit_log' and group:
            week_num = request.POST.get('week_number', '1')
            tasks = request.POST.get('tasks_completed', '').strip()
            plan = request.POST.get('next_week_plan', '').strip()
            if tasks and plan:
                WeeklyLog.objects.create(
                    group=group,
                    week_number=int(week_num) if str(week_num).isdigit() else 1,
                    tasks_completed=tasks,
                    next_week_plan=plan
                )
                if group.guide:
                    notify_users([group.guide], f"{group.name} submitted Week {week_num} progress log.")
                request.session['play_success_sound'] = True
                messages.success(request, f"Week {week_num} milestone recorded.")
            else:
                messages.error(request, "Tasks Completed and Next Week Target Plan are required.")
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
        'active_tab': 'student_dashboard',
        'notifications': request.user.notifications.filter(is_read=False)[:6],
    })

@login_required
def api_check_similarity(request):
    if request.user.is_superuser:
        return JsonResponse({'error': 'Isolated'}, status=403)
    if request.method == 'POST':
        title = request.POST.get('title', '')
        abstract = request.POST.get('abstract', '')
        dept = request.user.profile.department
        group = request.user.student_groups.first()
        res = check_abstract_similarity(title, abstract, department=dept, exclude_group_id=group.id if group else None)
        return JsonResponse(res)
    return JsonResponse({'error': 'POST required'}, status=400)

# ==============================================================================
# FACULTY GUIDE WORKSPACE (SCOPED TO AUTHORIZED DEPARTMENT)
# ==============================================================================
@login_required
def guide_dashboard(request):
    if request.user.is_superuser:
        return redirect('superadmin_dashboard')

    profile = request.user.profile
    if profile.role != 'GUIDE':
        return redirect('dashboard_router')

    dept = profile.department

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'claim_group':
            gid = request.POST.get('group_id')
            grp = get_object_or_404(ProjectGroup, id=gid, department=dept)
            grp.guide = request.user
            grp.save()
            notify_users(grp.students.all(), f"Guide {request.user.get_full_name()} accepted mentorship of {grp.name}.")
            request.session['play_success_sound'] = True
            messages.success(request, f"You are now guiding '{grp.name}'.")

        elif action == 'review_proposal':
            pid = request.POST.get('proposal_id')
            decision = request.POST.get('decision')
            remarks = request.POST.get('guide_remarks', '').strip()
            prop = get_object_or_404(ProjectProposal, id=pid, group__guide=request.user, group__department=dept)
            prop.status = decision
            prop.guide_remarks = remarks
            prop.save()
            verb = "approved" if decision == 'APPROVED' else "requested changes on"
            notify_users(prop.group.students.all(), f"Guide {request.user.get_full_name()} {verb} your proposal '{prop.title}'.")
            request.session['play_success_sound'] = True
            messages.success(request, f"Saved review for {prop.group.name}.")

        elif action == 'verify_log':
            lid = request.POST.get('log_id')
            feedback = request.POST.get('guide_feedback', '').strip()
            log_item = get_object_or_404(WeeklyLog, id=lid, group__guide=request.user, group__department=dept)
            log_item.is_verified = True
            log_item.guide_feedback = feedback or "Verified & signed off by Project Guide."
            log_item.save()
            notify_users(log_item.group.students.all(), f"Week {log_item.week_number} log verified by {request.user.get_full_name()}.")
            request.session['play_success_sound'] = True
            messages.success(request, f"Verified Week {log_item.week_number} for {log_item.group.name}.")

        return redirect('guide_dashboard')

    my_groups = ProjectGroup.objects.filter(guide=request.user, department=dept).prefetch_related('students__profile', 'logs')
    unassigned_groups = ProjectGroup.objects.filter(department=dept, guide__isnull=True).prefetch_related('students__profile')
    registered_mentees = UserProfile.objects.filter(preferred_guide=request.user, department=dept, user__is_superuser=False).select_related('user')

    pending_proposals = ProjectProposal.objects.filter(group__guide=request.user, group__department=dept, status='PENDING').count()
    unverified_logs = WeeklyLog.objects.filter(group__guide=request.user, group__department=dept, is_verified=False).count()

    return render(request, 'guide_dashboard.html', {
        'my_groups': my_groups,
        'unassigned_groups': unassigned_groups,
        'registered_mentees': registered_mentees,
        'pending_proposals': pending_proposals,
        'unverified_logs': unverified_logs,
        'active_tab': 'guide_dashboard',
        'notifications': request.user.notifications.filter(is_read=False)[:6],
    })

# ==============================================================================
# EXAMINER & HOD ANALYTICS PORTAL (SCOPED TO AUTHORIZED DEPARTMENT)
# ==============================================================================
@login_required
def examiner_dashboard(request):
    if request.user.is_superuser:
        return redirect('superadmin_dashboard')

    profile = request.user.profile
    if not (profile.is_examiner or profile.role == 'ADMIN'):
        messages.error(request, "Examiner portal access requires Examiner assignment by your Institution Admin.")
        return redirect('dashboard_router')

    dept = profile.department

    if request.method == 'POST':
        action = request.POST.get('action', 'grade_viva')

        if action == 'grade_viva':
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

            notify_users(grp.students.all(), f"Final Viva Evaluation certified for {grp.name}: {viva.total_score}/100 ({viva.grade_badge}).")
            request.session['play_success_sound'] = True
            messages.success(request, f"Published Viva grade for {grp.name} ({viva.total_score}/100).")

        elif action == 'add_archive':
            title = request.POST.get('title', '').strip()
            year = request.POST.get('year', '2025').strip()
            domain = request.POST.get('domain', 'Computer Science').strip()
            abstract = request.POST.get('abstract', '').strip()
            if title and abstract:
                PastProjectArchive.objects.create(department=dept, title=title, year=year, domain=domain, abstract=abstract)
                request.session['play_success_sound'] = True
                messages.success(request, f"Added '{title}' to {dept.name} TF-IDF archive corpus.")
            else:
                messages.error(request, "Archive Title and Abstract are required.")

        elif action == 'seed_corpus':
            added = 0
            for item in FALLBACK_CORPUS:
                _, created = PastProjectArchive.objects.get_or_create(
                    department=dept,
                    title=item["title"],
                    defaults={"year": "2025", "domain": "Software Systems", "abstract": item["abstract"]}
                )
                if created:
                    added += 1
            request.session['play_success_sound'] = True
            messages.success(request, f"Loaded {added} benchmark abstracts into {dept.name}'s similarity engine.")

        return redirect('examiner_dashboard')

    groups = ProjectGroup.objects.filter(department=dept).prefetch_related('students__profile', 'logs')
    archives = PastProjectArchive.objects.filter(department=dept)
    dept_students_count = UserProfile.objects.filter(department=dept, role='STUDENT', user__is_superuser=False).count()

    approved_count = ProjectProposal.objects.filter(group__department=dept, status='APPROVED').count()
    pending_count = ProjectProposal.objects.filter(group__department=dept, status='PENDING').count()
    changes_count = ProjectProposal.objects.filter(group__department=dept, status='CHANGES').count()
    evaluated_count = VivaEvaluation.objects.filter(group__department=dept).count()

    return render(request, 'examiner_viva.html', {
        'groups': groups,
        'archives': archives,
        'dept_students_count': dept_students_count,
        'approved_count': approved_count,
        'pending_count': pending_count,
        'changes_count': changes_count,
        'evaluated_count': evaluated_count,
        'active_tab': 'examiner_dashboard',
        'notifications': request.user.notifications.filter(is_read=False)[:6],
    })

# ==============================================================================
# INSTITUTION ADMIN COMMAND CENTER (SCOPED TO AUTHORIZED COLLEGE & UNIVERSITY)
# ==============================================================================
@login_required
def admin_dashboard(request):
    if request.user.is_superuser:
        return redirect('superadmin_dashboard')

    profile = request.user.profile
    if profile.role != 'ADMIN':
        messages.error(request, "Only verified Institution Admins can access the Admin Governance Console.")
        return redirect('dashboard_router')

    admin_uni = profile.university
    admin_col = profile.college

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_university':
            name = request.POST.get('university_name', '').strip()
            if name:
                u, _ = University.objects.get_or_create(name=name, defaults={'created_by': request.user})
                if not profile.university:
                    profile.university = u
                    profile.save()
                request.session['play_success_sound'] = True
                messages.success(request, f"University '{name}' registered.")

        elif action == 'add_college':
            uni_id = request.POST.get('university_id', '')
            col_name = request.POST.get('college_name', '').strip()
            if uni_id.isdigit() and col_name:
                u = get_object_or_404(University, id=int(uni_id))
                if admin_uni and u.id != admin_uni.id:
                    messages.error(request, "You can only add colleges within your authorized University.")
                    return redirect('admin_dashboard')
                c, _ = College.objects.get_or_create(university=u, name=col_name)
                if not profile.college:
                    profile.college = c
                    profile.save()
                request.session['play_success_sound'] = True
                messages.success(request, f"College '{col_name}' added under {u.name}.")

        elif action == 'add_department':
            col_id = request.POST.get('college_id', '')
            dept_name = request.POST.get('department_name', '').strip()
            acad_year = request.POST.get('academic_year', '2026-2027').strip()
            if col_id.isdigit() and dept_name:
                c = get_object_or_404(College, id=int(col_id))
                if admin_col and c.id != admin_col.id:
                    messages.error(request, "You can only add departments within your authorized College.")
                    return redirect('admin_dashboard')
                Department.objects.get_or_create(college=c, name=dept_name, defaults={'academic_year': acad_year})
                request.session['play_success_sound'] = True
                messages.success(request, f"Department '{dept_name}' added under {c.name}!")

        elif action == 'toggle_examiner':
            prof_id = request.POST.get('profile_id', '')
            target_prof = get_object_or_404(UserProfile, id=prof_id, role='GUIDE', user__is_superuser=False)
            if admin_col and target_prof.college_id != admin_col.id:
                messages.error(request, "Unauthorized: You can only manage Faculty Guides within your own College.")
                return redirect('admin_dashboard')
            target_prof.is_examiner = not target_prof.is_examiner
            target_prof.save()
            state_str = "Promoted to External Examiner & HOD Analytics role" if target_prof.is_examiner else "Demoted to standard Faculty Guide role"
            notify_users([target_prof.user], f"Admin {request.user.get_full_name()} updated your role privileges: {state_str}.")
            request.session['play_success_sound'] = True
            messages.success(request, f"{target_prof.user.get_full_name() or target_prof.user.username}: {state_str}.")

        return redirect('admin_dashboard')

    dept_filter = request.GET.get('dept_id', '').strip()
    search_q = request.GET.get('q', '').strip().lower()

    # Enforce College / University boundary
    all_universities = University.objects.filter(id=admin_uni.id) if admin_uni else University.objects.all()
    all_colleges = College.objects.filter(id=admin_col.id).select_related('university') if admin_col else College.objects.select_related('university').all()
    all_departments = Department.objects.filter(college=admin_col).select_related('college__university') if admin_col else Department.objects.select_related('college__university').all()

    guides_qs = UserProfile.objects.filter(role='GUIDE', user__is_superuser=False).select_related('user', 'department', 'college', 'university')
    students_qs = UserProfile.objects.filter(role='STUDENT', user__is_superuser=False).select_related('user', 'department', 'college', 'preferred_guide')

    if admin_col:
        guides_qs = guides_qs.filter(college=admin_col)
        students_qs = students_qs.filter(college=admin_col)
    elif admin_uni:
        guides_qs = guides_qs.filter(university=admin_uni)
        students_qs = students_qs.filter(university=admin_uni)

    if dept_filter.isdigit():
        guides_qs = guides_qs.filter(department_id=int(dept_filter))
        students_qs = students_qs.filter(department_id=int(dept_filter))

    if search_q:
        guides_qs = [g for g in guides_qs if search_q in (g.user.get_full_name() or g.user.username).lower() or search_q in g.identifier.lower()]
        students_qs = [s for s in students_qs if search_q in (s.user.get_full_name() or s.user.username).lower() or search_q in s.identifier.lower()]

    examiners_count = UserProfile.objects.filter(
        college=admin_col,
        is_examiner=True,
        user__is_superuser=False
    ).count() if admin_col else UserProfile.objects.filter(is_examiner=True, user__is_superuser=False).count()

    return render(request, 'admin_dashboard.html', {
        'all_universities': all_universities,
        'all_colleges': all_colleges,
        'all_departments': all_departments,
        'guides_qs': guides_qs,
        'students_qs': students_qs,
        'dept_filter': dept_filter,
        'search_q': search_q,
        'examiners_count': examiners_count,
        'active_tab': 'admin_dashboard',
        'notifications': request.user.notifications.filter(is_read=False)[:6],
    })

@login_required
def export_department_csv(request):
    if request.user.is_superuser:
        groups = ProjectGroup.objects.all()
        dept_label = 'Global_Superadmin'
    else:
        profile = request.user.profile
        if profile.role == 'ADMIN' and profile.college:
            groups = ProjectGroup.objects.filter(department__college=profile.college)
            dept_label = profile.college.name.replace(' ', '_')
        elif profile.department:
            groups = ProjectGroup.objects.filter(department=profile.department)
            dept_label = profile.department.name.replace(' ', '_')
        else:
            return HttpResponseForbidden("Unauthorized export scope.")

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="ProTrack_{dept_label}_Master_Report.csv"'
    writer = csv.writer(response)
    writer.writerow(['Group Name', 'Join Code', 'Department', 'Students', 'Project Guide', 'Proposal Title', 'Status', 'AI Similarity (%)', 'Verified Logs', 'Viva Score (/100)', 'Grade'])

    for g in groups:
        students_str = ", ".join([s.get_full_name() or s.username for s in g.students.filter(is_superuser=False)])
        guide_str = g.guide.get_full_name() if g.guide else "Unassigned"
        prop = getattr(g, 'proposal', None)
        viva = getattr(g, 'viva', None)
        verified_logs = g.logs.filter(is_verified=True).count()
        writer.writerow([
            g.name,
            g.join_code,
            g.department.name,
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
"""

# ==============================================================================
# 6. URL ROUTING & ADMIN REGISTRATION (portal/urls.py & portal/admin.py)
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
    path('examiner/', views.examiner_dashboard, name='examiner_dashboard'),
    path('admin-portal/', views.admin_dashboard, name='admin_dashboard'),
    path('settings/', views.profile_settings_view, name='profile_settings'),
    path('profile/<str:username>/', views.public_profile_view, name='public_profile'),
    path('export-csv/', views.export_department_csv, name='export_department_csv'),
    path('notifications/read/', views.mark_notifications_read, name='mark_notifications_read'),
    # Isolated Superadmin Access Flow
    path('superadmin-access/', views.superadmin_login_view, name='superadmin_login'),
    path('superadmin-console/', views.superadmin_dashboard_view, name='superadmin_dashboard'),
    # APIs
    path('api/check-similarity/', views.api_check_similarity, name='api_check_similarity'),
    path('api/hierarchy/', views.api_hierarchy, name='api_hierarchy'),
    path('api/check-username/', views.api_check_username, name='api_check_username'),
    path('api/search-classmates/', views.api_search_classmates, name='api_search_classmates'),
    path('api/sync-drafts/', views.api_sync_drafts, name='api_sync_drafts'),
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
# 7. BASE TEMPLATE — ACTIVE TABS, AUTO-SAVE ENGINE, REQUIRED LEGEND, AUDIO CHIME
# ==============================================================================
BASE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ProTrack Cloud v1.05 — Academic Project & Viva Governance</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>
        :root {
            --m3-bg: #F6F4FB;
            --m3-surface: #FFFFFF;
            --m3-surface-tonal: #EFEBF9;
            --m3-surface-hover: #E6DFF5;
            --m3-primary: #5E35B1;
            --m3-primary-hover: #4527A0;
            --m3-primary-container: #EDE7F6;
            --m3-on-primary-container: #28115B;
            --m3-accent: #7C4DFF;
            --m3-text: #1B1528;
            --m3-text-muted: #574F6B;
            --m3-border: #DFD8EE;
            --m3-success-bg: #E6F4EA;
            --m3-success-text: #137333;
            --m3-warning-bg: #FEF7E0;
            --m3-warning-text: #B06000;
            --m3-danger-bg: #FCE8E6;
            --m3-danger-text: #C5221F;
            --m3-whatsapp: #25D366;
            --radius-2xl: 32px;
            --radius-xl: 24px;
            --radius-lg: 18px;
            --radius-pill: 9999px;
        }

        body {
            font-family: 'Google Sans', 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--m3-bg);
            color: var(--m3-text);
            font-size: 17px;
            line-height: 1.65;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            -webkit-font-smoothing: antialiased;
        }

        .container-google {
            max-width: 1520px;
            margin: 0 auto;
            padding: 0 24px;
            width: 100%;
        }

        h1, h2, h3, h4, h5, h6 {
            font-family: 'Google Sans', 'Plus Jakarta Sans', sans-serif;
            letter-spacing: -0.02em;
            font-weight: 600;
            color: var(--m3-text);
        }

        @keyframes fadeUp {
            from { opacity: 0; transform: translateY(12px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .animate-in {
            animation: fadeUp 0.35s cubic-bezier(0.2, 0, 0, 1) forwards;
        }

        .m3-navbar {
            background: rgba(255, 255, 255, 0.92);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid var(--m3-border);
            padding: 16px 0;
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
            font-size: 1.5rem;
        }

        .brand-icon-box {
            width: 46px;
            height: 46px;
            border-radius: 14px;
            background: linear-gradient(135deg, #5E35B1, #7C4DFF);
            color: #fff;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 6px 18px rgba(94, 53, 177, 0.25);
        }

        .m3-card {
            background: var(--m3-surface);
            border: 1px solid var(--m3-border);
            border-radius: var(--radius-2xl);
            padding: 36px;
            box-shadow: 0 2px 6px rgba(27, 21, 40, 0.03), 0 12px 32px rgba(94, 53, 177, 0.05);
        }

        .m3-card-tonal {
            background: var(--m3-surface-tonal);
            border: 1px solid rgba(94, 53, 177, 0.12);
            border-radius: var(--radius-xl);
            padding: 28px;
        }

        .form-label {
            font-weight: 600;
            font-size: 0.98rem;
            color: var(--m3-text);
            margin-bottom: 8px;
        }

        .req-star {
            color: #D93025;
            font-weight: 700;
            margin-left: 3px;
        }

        .req-legend {
            font-size: 0.88rem;
            color: var(--m3-text-muted);
            background: var(--m3-surface-tonal);
            padding: 6px 14px;
            border-radius: 999px;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }

        .form-control, .form-select {
            border-radius: var(--radius-lg);
            min-height: 54px;
            padding: 13px 20px;
            font-size: 1.02rem;
            border: 1.5px solid #CEC4E4;
            background-color: #FFFFFF;
            color: var(--m3-text);
            transition: all 0.2s ease;
        }

        textarea.form-control {
            min-height: 130px;
        }

        .form-control:focus, .form-select:focus {
            border-color: var(--m3-primary);
            box-shadow: 0 0 0 4px rgba(94, 53, 177, 0.16);
        }

        /* Active-State Dashboard Navigation Tabs */
        .nav-tab-m3 {
            border-radius: var(--radius-pill);
            min-height: 46px;
            padding: 10px 22px;
            font-size: 0.98rem;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            text-decoration: none;
            transition: all 0.2s ease;
            background-color: #FFFFFF;
            color: var(--m3-primary);
            border: 1.5px solid #C5B9E0;
        }

        .nav-tab-m3:hover {
            background-color: var(--m3-surface-tonal);
            color: var(--m3-primary);
        }

        .nav-tab-m3.active-tab {
            background: linear-gradient(135deg, #5E35B1, #4527A0) !important;
            color: #FFFFFF !important;
            border-color: transparent !important;
            box-shadow: 0 4px 14px rgba(94, 53, 177, 0.28);
        }

        .btn-m3-primary {
            background: linear-gradient(135deg, #5E35B1, #4527A0);
            color: #FFFFFF;
            border: none;
            border-radius: var(--radius-pill);
            min-height: 54px;
            padding: 12px 28px;
            font-size: 1.02rem;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            transition: all 0.2s ease;
            box-shadow: 0 4px 14px rgba(94, 53, 177, 0.24);
        }

        .btn-m3-primary:hover {
            background: linear-gradient(135deg, #512DA8, #311B92);
            color: #FFFFFF;
            transform: translateY(-1px);
        }

        .btn-m3-tonal {
            background-color: var(--m3-primary-container);
            color: var(--m3-on-primary-container);
            border: 1px solid rgba(94, 53, 177, 0.16);
            border-radius: var(--radius-pill);
            min-height: 52px;
            padding: 11px 24px;
            font-size: 0.98rem;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            transition: all 0.2s ease;
        }

        .btn-m3-tonal:hover {
            background-color: #DDD2F3;
            color: var(--m3-on-primary-container);
        }

        .btn-m3-outline {
            background-color: #FFFFFF;
            color: var(--m3-primary);
            border: 1.5px solid #C5B9E0;
            border-radius: var(--radius-pill);
            min-height: 48px;
            padding: 10px 22px;
            font-size: 0.96rem;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            transition: all 0.2s ease;
        }

        .btn-m3-outline:hover {
            background-color: var(--m3-surface-tonal);
            border-color: var(--m3-primary);
            color: var(--m3-primary);
        }

        .btn-whatsapp {
            background-color: #E8FBF0;
            color: #0F6E36;
            border: 1px solid #A8EBC4;
            border-radius: var(--radius-pill);
            padding: 7px 16px;
            font-size: 0.9rem;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            text-decoration: none;
            transition: all 0.2s ease;
        }

        .btn-whatsapp:hover {
            background-color: #25D366;
            color: #FFFFFF;
            border-color: #25D366;
        }

        .m3-chip {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 16px;
            border-radius: var(--radius-pill);
            font-size: 0.9rem;
            font-weight: 600;
            white-space: nowrap;
        }

        .chip-tonal { background: var(--m3-primary-container); color: var(--m3-on-primary-container); }
        .chip-success { background: var(--m3-success-bg); color: var(--m3-success-text); }
        .chip-warning { background: var(--m3-warning-bg); color: var(--m3-warning-text); }
        .chip-danger { background: var(--m3-danger-bg); color: var(--m3-danger-text); }
        .chip-neutral { background: var(--m3-surface-tonal); color: var(--m3-text-muted); }

        .avatar-circle {
            width: 48px;
            height: 48px;
            border-radius: 50%;
            background: var(--m3-primary-container);
            color: var(--m3-on-primary-container);
            font-weight: 700;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            flex-shrink: 0;
            border: 2px solid #FFFFFF;
            box-shadow: 0 2px 8px rgba(94, 53, 177, 0.16);
            text-decoration: none;
        }

        .avatar-circle img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
        }

        .autosave-pill {
            font-size: 0.82rem;
            padding: 5px 12px;
            border-radius: 999px;
            background: var(--m3-surface-tonal);
            color: var(--m3-text-muted);
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-weight: 600;
        }

        .lucide {
            width: 20px;
            height: 20px;
            stroke-width: 2px;
        }

        .toast-stack {
            position: fixed;
            bottom: 28px;
            right: 28px;
            z-index: 1090;
            display: flex;
            flex-direction: column;
            gap: 12px;
            max-width: 440px;
        }

        .m3-snackbar {
            background: #24183E;
            color: #FFFFFF;
            padding: 16px 24px;
            border-radius: 18px;
            box-shadow: 0 12px 32px rgba(27, 21, 40, 0.26);
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 0.98rem;
        }
    </style>
</head>
<body>
    {% if user.is_authenticated and not user.is_superuser %}
    <nav class="m3-navbar">
        <div class="container-google d-flex flex-wrap align-items-center justify-content-between gap-3">
            <div class="d-flex align-items-center gap-3 flex-wrap">
                <a href="{% url 'dashboard_router' %}" class="brand-logo">
                    <span class="brand-icon-box"><i data-lucide="graduation-cap"></i></span>
                    <span>ProTrack</span>
                </a>
                {% if user.profile.department %}
                <span class="m3-chip chip-neutral d-none d-xl-inline-flex">
                    <i data-lucide="building-2" style="width:16px;height:16px;"></i>
                    {{ user.profile.university.name }} &bull; {{ user.profile.college.name }} &bull; <strong class="text-dark">{{ user.profile.department.name }}</strong>
                </span>
                {% endif %}
                <span id="globalAutosaveStatus" class="autosave-pill d-none">
                    <i data-lucide="cloud" style="width:14px;height:14px;"></i> <span id="autosaveText">Saved</span>
                </span>
            </div>

            <div class="d-flex align-items-center gap-2 flex-wrap">
                {% if user.profile.role == 'ADMIN' %}
                <a href="{% url 'admin_dashboard' %}" class="nav-tab-m3 {% if request.resolver_match.url_name == 'admin_dashboard' %}active-tab{% endif %}">
                    <i data-lucide="shield"></i> Admin Console
                </a>
                <a href="{% url 'examiner_dashboard' %}" class="nav-tab-m3 {% if request.resolver_match.url_name == 'examiner_dashboard' %}active-tab{% endif %}">
                    <i data-lucide="bar-chart-3"></i> Examiner & HOD View
                </a>
                {% elif user.profile.role == 'GUIDE' and user.profile.is_examiner %}
                <a href="{% url 'guide_dashboard' %}" class="nav-tab-m3 {% if request.resolver_match.url_name == 'guide_dashboard' %}active-tab{% endif %}">
                    <i data-lucide="users"></i> Guide Console
                </a>
                <a href="{% url 'examiner_dashboard' %}" class="nav-tab-m3 {% if request.resolver_match.url_name == 'examiner_dashboard' %}active-tab{% endif %}">
                    <i data-lucide="award"></i> Examiner & HOD Portal
                </a>
                {% elif user.profile.role == 'GUIDE' %}
                <a href="{% url 'guide_dashboard' %}" class="nav-tab-m3 {% if request.resolver_match.url_name == 'guide_dashboard' %}active-tab{% endif %}">
                    <i data-lucide="users"></i> Guide Console
                </a>
                {% elif user.profile.role == 'STUDENT' %}
                <a href="{% url 'student_dashboard' %}" class="nav-tab-m3 {% if request.resolver_match.url_name == 'student_dashboard' %}active-tab{% endif %}">
                    <i data-lucide="layout-dashboard"></i> Student Workspace
                </a>
                {% endif %}

                <a href="{% url 'profile_settings' %}" class="nav-tab-m3 {% if request.resolver_match.url_name == 'profile_settings' or request.resolver_match.url_name == 'public_profile' %}active-tab{% endif %}">
                    <i data-lucide="settings"></i> <span class="d-none d-md-inline">Profile & Directory</span>
                </a>

                <!-- Notifications Bell -->
                <div class="dropdown">
                    <button class="btn-m3-outline position-relative py-2 px-3" style="min-height:46px;" data-bs-toggle="dropdown" aria-expanded="false">
                        <i data-lucide="bell"></i>
                        {% if notifications %}
                        <span class="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-danger">
                            {{ notifications|length }}
                        </span>
                        {% endif %}
                    </button>
                    <div class="dropdown-menu dropdown-menu-end p-4 shadow-lg border-0" style="width: 380px; border-radius: 24px;">
                        <div class="d-flex justify-content-between align-items-center mb-3 pb-2 border-bottom">
                            <span class="fw-bold fs-5">Workspace Alerts</span>
                            {% if notifications %}
                            <a href="{% url 'mark_notifications_read' %}" class="small text-decoration-none fw-bold" style="color:var(--m3-primary);">Mark all read</a>
                            {% endif %}
                        </div>
                        {% for n in notifications %}
                        <div class="py-2 border-bottom">
                            <div class="text-dark fw-medium">{{ n.message }}</div>
                            <div class="text-muted small">{{ n.created_at|timesince }} ago</div>
                        </div>
                        {% empty %}
                        <div class="text-center py-4 text-muted">
                            <i data-lucide="check-circle-2" class="mb-2 text-success" style="width:30px;height:30px;"></i>
                            <div>All caught up! Zero unread alerts.</div>
                        </div>
                        {% endfor %}
                    </div>
                </div>

                <!-- User Avatar & Sign Out -->
                <div class="d-flex align-items-center gap-2 ps-2 border-start">
                    <a href="{% url 'profile_settings' %}" class="avatar-circle" title="View & Edit Profile">
                        {% if user.profile.has_avatar %}
                        <img src="{{ user.profile.avatar_url }}" alt="{{ user.get_full_name|default:user.username }}" onerror="this.style.display='none';this.parentElement.innerText='{{ user.profile.initials }}';">
                        {% else %}
                        {{ user.profile.initials }}
                        {% endif %}
                    </a>
                    <div class="text-end d-none d-lg-block me-1">
                        <a href="{% url 'public_profile' user.username %}" class="fw-bold text-dark text-decoration-none d-block" style="line-height:1.2;">{{ user.get_full_name|default:user.username }}</a>
                        <div class="text-muted small">{{ user.profile.identifier }}</div>
                    </div>
                    <a href="{% url 'logout' %}" class="btn-m3-outline py-2 px-3" style="min-height:46px;" title="Sign Out">
                        <i data-lucide="log-out"></i>
                    </a>
                </div>
            </div>
        </div>
    </nav>
    {% elif user.is_authenticated and user.is_superuser %}
    <nav class="m3-navbar" style="background: #1B1528; color: #FFFFFF;">
        <div class="container-google d-flex flex-wrap align-items-center justify-content-between gap-3">
            <div class="d-flex align-items-center gap-3">
                <span class="brand-icon-box"><i data-lucide="terminal"></i></span>
                <div>
                    <div class="fw-bold fs-5 text-white">ProTrack Isolated Superadmin Console</div>
                    <div class="small text-white-50">Private System-Wide Multi-Institution Governance</div>
                </div>
            </div>
            <div class="d-flex align-items-center gap-2">
                <a href="{% url 'superadmin_dashboard' %}" class="nav-tab-m3 active-tab">
                    <i data-lucide="database"></i> Master Console
                </a>
                <a href="/django-admin/" class="btn-m3-outline py-2 px-3 text-decoration-none">
                    <i data-lucide="sliders"></i> Raw DB Admin
                </a>
                <a href="{% url 'logout' %}" class="btn btn-danger rounded-pill px-4 fw-bold">
                    <i data-lucide="log-out"></i> Sign Out
                </a>
            </div>
        </div>
    </nav>
    {% endif %}

    <main class="flex-grow-1 py-4 py-md-5">
        <div class="container-google animate-in">
            {% block content %}{% endblock %}
        </div>
    </main>

    {% if messages %}
    <div class="toast-stack" id="toastStack">
        {% for message in messages %}
        <div class="m3-snackbar" data-tags="{{ message.tags }}">
            <i data-lucide="sparkles" class="text-warning flex-shrink-0"></i>
            <div class="flex-grow-1">{{ message }}</div>
        </div>
        {% endfor %}
    </div>
    {% endif %}

    <footer class="py-4 border-top bg-white mt-auto">
        <div class="container-google d-flex flex-wrap justify-content-between align-items-center text-muted">
            <div><strong>ProTrack Cloud v1.05 by Mohammad Mustafa</strong></div>
            <div>Google Material 3 &bull; Scikit-Learn TF-IDF &bull; Lucide Vector UI</div>
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        lucide.createIcons();

        // Celebratory Audio Chime using the uploaded Success.mp3 file
        function playSuccessChime() {
           try {
               const audio = new Audio('/media/Success.mp3');
               audio.play().catch(e => console.log("Audio blocked by browser auto-play policy."));
            } catch (e) {}
        }

        document.addEventListener('DOMContentLoaded', () => {
            // 1. Trigger Success Sound if a success message is present
            const successToast = document.querySelector('.m3-snackbar[data-tags*="success"]');
            if (successToast) {
                playSuccessChime();
            }

            setTimeout(() => {
                const stack = document.getElementById('toastStack');
                if (stack) stack.style.display = 'none';
            }, 5500);

            // 2. Automatically append red asterisk (*) to required fields & inject legend
            document.querySelectorAll('form').forEach(form => {
                const reqInputs = form.querySelectorAll('input[required], select[required], textarea[required]');
                if (reqInputs.length > 0 && !form.querySelector('.req-legend') && !form.classList.contains('no-legend')) {
                    const legend = document.createElement('div');
                    legend.className = 'mb-3';
                    legend.innerHTML = '<span class="req-legend"><span class="req-star">*</span> Indicates a required field</span>';
                    form.insertBefore(legend, form.firstElementChild);
                }
                reqInputs.forEach(input => {
                    if (input.type === 'hidden') return;
                    let label = form.querySelector(`label[for="${input.id}"]`);
                    if (!label && input.parentElement) {
                        label = input.parentElement.querySelector('label.form-label');
                    }
                    if (label && !label.querySelector('.req-star')) {
                        const star = document.createElement('span');
                        star.className = 'req-star';
                        star.innerText = ' *';
                        label.appendChild(star);
                    }
                });
            });

            // 3. Automatic Form Saving & Persistence Engine (Local + Account Sync)
            const statusPill = document.getElementById('globalAutosaveStatus');
            const statusText = document.getElementById('autosaveText');
            const isAuthRegular = {{ user.is_authenticated|yesno:"true,false" }} && !{{ user.is_superuser|yesno:"true,false" }};
            const userKeyPrefix = "protrack_v105_draft_{{ user.username|default:'guest' }}_";

            function setSaveStatus(state) {
                if (!statusPill || !statusText) return;
                statusPill.classList.remove('d-none');
                if (state === 'saving') {
                    statusText.innerText = 'Saving...';
                } else if (state === 'saved') {
                    statusText.innerText = 'Saved';
                } else {
                    statusText.innerText = 'Unable to save (Offline draft kept)';
                }
            }

            let syncTimeout = null;
            function syncDraftToServer(formKey, fieldsObj, clearFlag) {
                if (!isAuthRegular) return;
                clearTimeout(syncTimeout);
                syncTimeout = setTimeout(() => {
                    fetch("{% url 'api_sync_drafts' %}", {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': '{{ csrf_token }}'
                        },
                        body: JSON.stringify({
                            form_key: formKey,
                            fields: fieldsObj,
                            clear: !!clearFlag
                        })
                    }).then(r => {
                        if (r.ok) setSaveStatus('saved');
                        else setSaveStatus('error');
                    }).catch(() => setSaveStatus('error'));
                }, 500);
            }

            document.querySelectorAll('form[data-autosave]').forEach(form => {
                const formKey = form.getAttribute('data-autosave');
                const storageKey = userKeyPrefix + formKey;

                // Restore from localStorage if field is currently empty
                try {
                    const savedRaw = localStorage.getItem(storageKey);
                    if (savedRaw) {
                        const savedData = JSON.parse(savedRaw);
                        Object.keys(savedData).forEach(name => {
                            const el = form.elements[name];
                            if (el && el.type !== 'password' && el.type !== 'file' && el.type !== 'hidden') {
                                if (!el.value || el.getAttribute('data-allow-draft-override') === 'true') {
                                    el.value = savedData[name];
                                }
                            }
                        });
                    }
                } catch (e) {}

                form.addEventListener('input', (ev) => {
                    const target = ev.target;
                    if (!target.name || target.type === 'password' || target.type === 'file' || target.type === 'hidden') return;
                    setSaveStatus('saving');
                    let current = {};
                    try {
                        current = JSON.parse(localStorage.getItem(storageKey) || '{}');
                    } catch (e) {}
                    current[target.name] = target.value;
                    localStorage.setItem(storageKey, JSON.stringify(current));
                    if (!isAuthRegular) {
                        setTimeout(() => setSaveStatus('saved'), 250);
                    } else {
                        syncDraftToServer(formKey, current, false);
                    }
                });

                form.addEventListener('submit', () => {
                    localStorage.removeItem(storageKey);
                    syncDraftToServer(formKey, {}, true);
                });
            });
        });
    </script>
</body>
</html>
"""

# ==============================================================================
# 8. LOGIN & ROLE-TAILORED SIGNUP TEMPLATES (login.html & signup.html)
# ==============================================================================
LOGIN_HTML = """
{% extends 'base.html' %}
{% block content %}
<div class="row justify-content-center align-items-center g-5 py-4">
    <div class="col-xl-6 col-lg-6">
        <div class="m3-chip chip-tonal mb-4">
            <i data-lucide="sparkles" style="width:18px;height:18px;"></i>
            ProTrack Cloud v1.05 Enterprise
        </div>
        <h1 class="display-4 fw-bold mb-4" style="color: #28115B; line-height: 1.15;">
            Academic Projects & Viva Governance, Reimagined.
        </h1>
        <p class="lead text-muted mb-5" style="font-size: 1.2rem;">
            A unified, role-verified workspace where Admins govern Universities, Colleges, and Departments, Faculty Guides mentor teams, Examiners grade live rubrics, and Students verify originality with Scikit-Learn TF-IDF AI.
        </p>

        <div class="row g-3">
            <div class="col-sm-3 col-6">
                <div class="m3-card-tonal text-center py-4 px-2">
                    <div class="h2 fw-bold mb-0" style="color:var(--m3-primary);">{{ total_universities }}</div>
                    <div class="small text-muted fw-medium">Universities</div>
                </div>
            </div>
            <div class="col-sm-3 col-6">
                <div class="m3-card-tonal text-center py-4 px-2">
                    <div class="h2 fw-bold mb-0" style="color:var(--m3-primary);">{{ total_colleges }}</div>
                    <div class="small text-muted fw-medium">Colleges</div>
                </div>
            </div>
            <div class="col-sm-3 col-6">
                <div class="m3-card-tonal text-center py-4 px-2">
                    <div class="h2 fw-bold mb-0" style="color:var(--m3-primary);">{{ total_departments }}</div>
                    <div class="small text-muted fw-medium">Departments</div>
                </div>
            </div>
            <div class="col-sm-3 col-6">
                <div class="m3-card-tonal text-center py-4 px-2">
                    <div class="h2 fw-bold mb-0" style="color:var(--m3-primary);">{{ total_users }}</div>
                    <div class="small text-muted fw-medium">Verified Users</div>
                </div>
            </div>
        </div>
    </div>

    <div class="col-xl-5 col-lg-6">
        <div class="m3-card">
            <div class="d-flex align-items-center gap-3 mb-4">
                <div class="brand-icon-box"><i data-lucide="graduation-cap"></i></div>
                <div>
                    <h2 class="mb-0 fw-bold">Sign in</h2>
                    <div class="text-muted">Continue to your ProTrack Workspace</div>
                </div>
            </div>

            <form method="POST" data-autosave="login_form">
                {% csrf_token %}
                <div class="mb-4">
                    <label class="form-label" for="loginUsername">Username</label>
                    <input type="text" name="username" id="loginUsername" class="form-control" placeholder="e.g. johndoe" required autofocus>
                </div>
                <div class="mb-4">
                    <label class="form-label" for="loginPassword">Password</label>
                    <input type="password" name="password" id="loginPassword" class="form-control" placeholder="Enter your password" required>
                </div>
                <button type="submit" class="btn-m3-primary w-100 mb-3">
                    <i data-lucide="log-in"></i> Sign In to Workspace
                </button>
            </form>

            <hr class="my-4">
            <div class="text-center">
                <p class="text-muted mb-3">New Student, Faculty Guide, or Institution Admin?</p>
                <a href="{% url 'signup' %}" class="btn-m3-tonal w-100 text-decoration-none">
                    <i data-lucide="user-plus"></i> Create Role-Verified Account
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
<style>
    .role-tab-btn {
        cursor: pointer;
        border: 2px solid var(--m3-border);
        border-radius: 24px;
        padding: 24px;
        background: #FFFFFF;
        transition: all 0.22s ease;
    }
    .role-tab-btn.active {
        border-color: var(--m3-primary);
        background: var(--m3-primary-container);
        box-shadow: 0 8px 24px rgba(94, 53, 177, 0.15);
    }
    .suggestion-pill {
        cursor: pointer;
        background: var(--m3-primary-container);
        color: var(--m3-on-primary-container);
        padding: 6px 16px;
        border-radius: 999px;
        font-size: 0.9rem;
        font-weight: 600;
        border: 1px solid rgba(94, 53, 177, 0.2);
        transition: all 0.15s ease;
    }
    .suggestion-pill:hover {
        background: var(--m3-primary);
        color: #FFFFFF;
    }
</style>

<div class="row justify-content-center">
    <div class="col-xl-10">
        <div class="m3-card">
            <div class="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4 pb-3 border-bottom">
                <div class="d-flex align-items-center gap-3">
                    <div class="brand-icon-box"><i data-lucide="user-plus"></i></div>
                    <div>
                        <h2 class="mb-0 fw-bold">Create Your ProTrack Account</h2>
                        <div class="text-muted">Role-tailored onboarding with live duplicate checks & draft auto-saving</div>
                    </div>
                </div>
                <div class="d-flex align-items-center gap-2">
                    <span id="signupDraftBadge" class="autosave-pill"><i data-lucide="check-circle-2" style="width:14px;height:14px;"></i> Draft Auto-Save Active</span>
                    <a href="{% url 'login' %}" class="btn-m3-outline text-decoration-none">
                        <i data-lucide="arrow-left"></i> Back to Sign In
                    </a>
                </div>
            </div>

            <form method="POST" enctype="multipart/form-data" id="signupForm" data-autosave="signup_form">
                {% csrf_token %}
                <input type="hidden" name="role" id="selectedRole" value="STUDENT">

                <!-- 1. ROLE SELECTOR CARDS -->
                <h4 class="fw-bold mb-3 d-flex align-items-center gap-2">
                    <i data-lucide="layers" style="color:var(--m3-primary);"></i> 1. Select Your Role
                </h4>
                <div class="row g-3 mb-5">
                    <div class="col-md-4">
                        <div class="role-tab-btn active h-100" id="tab_STUDENT" onclick="selectRole('STUDENT')">
                            <div class="d-flex align-items-center justify-content-between mb-2">
                                <span class="m3-chip chip-tonal py-1 px-3">Student</span>
                                <i data-lucide="graduation-cap" style="color:var(--m3-primary);"></i>
                            </div>
                            <h5 class="fw-bold mb-1">Student</h5>
                            <div class="small text-muted">Select your Admin-registered University, College, Department & Project Guide.</div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="role-tab-btn h-100" id="tab_GUIDE" onclick="selectRole('GUIDE')">
                            <div class="d-flex align-items-center justify-content-between mb-2">
                                <span class="m3-chip chip-tonal py-1 px-3">Faculty Guide</span>
                                <i data-lucide="book-open-check" style="color:var(--m3-primary);"></i>
                            </div>
                            <h5 class="fw-bold mb-1">Faculty Guide</h5>
                            <div class="small text-muted">Join your Department to mentor students. Can be promoted to Examiner by Admin.</div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="role-tab-btn h-100" id="tab_ADMIN" onclick="selectRole('ADMIN')">
                            <div class="d-flex align-items-center justify-content-between mb-2">
                                <span class="m3-chip chip-tonal py-1 px-3">Verified Admin</span>
                                <i data-lucide="shield-check" style="color:var(--m3-primary);"></i>
                            </div>
                            <h5 class="fw-bold mb-1">Institution Admin</h5>
                            <div class="small text-muted">Register Universities, Colleges & Departments. Requires Front & Back ID Proof.</div>
                        </div>
                    </div>
                </div>

                <!-- 2. PERSONAL & ACCOUNT CREDENTIALS -->
                <h4 class="fw-bold mb-3 d-flex align-items-center gap-2">
                    <i data-lucide="user-check" style="color:var(--m3-primary);"></i> 2. Personal & Account Details
                </h4>
                <div class="row g-4 mb-4">
                    <div class="col-md-6">
                        <label class="form-label" for="fullNameInput">Full Name</label>
                        <input type="text" name="full_name" id="fullNameInput" class="form-control" placeholder="e.g. John Doe" oninput="scheduleUsernameCheck()" required>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label" for="emailInput">Email Address</label>
                        <input type="email" name="email" id="emailInput" class="form-control" placeholder="e.g. johndoe@example.com" required>
                    </div>

                    <div class="col-md-4">
                        <label class="form-label" id="idFieldLabel" for="idFieldInput">Roll Call Number <span class="req-star">*</span></label>
                        <input type="text" name="identifier" id="idFieldInput" class="form-control" placeholder="e.g. CS-2026-01" oninput="scheduleUsernameCheck()" required>
                    </div>

                    <div class="col-md-4" id="studentClassWrap">
                        <label class="form-label" for="classDivInput">Class / Division</label>
                        <input type="text" name="class_division" id="classDivInput" class="form-control" placeholder="e.g. TY-BSc-CS" value="TY-CS-A" required>
                    </div>

                    <div class="col-md-4">
                        <label class="form-label" for="waInput">WhatsApp Number (Optional)</label>
                        <input type="text" name="whatsapp_number" id="waInput" class="form-control" placeholder="e.g. +1 555 234 5678">
                    </div>

                    <div class="col-md-6">
                        <label class="form-label" for="usernameInput">Username</label>
                        <input type="text" name="username" id="usernameInput" class="form-control" placeholder="e.g. johndoe" oninput="scheduleUsernameCheck()" required>
                        <div id="usernameDupError" class="small text-danger fw-bold mt-1 d-none">
                            This username is already taken. Please choose one of the available suggestions below.
                        </div>
                        <div class="mt-2 d-flex flex-wrap align-items-center gap-2" id="suggestionBar">
                            <span class="small text-muted">Available suggestions:</span>
                        </div>
                    </div>

                    <div class="col-md-6">
                        <label class="form-label" for="passwordInput">Password (Min. 6 characters)</label>
                        <input type="password" name="password" id="passwordInput" class="form-control" placeholder="Create a strong password" minlength="6" required>
                    </div>
                </div>

                <!-- 3. INSTITUTION HIERARCHY -->
                <h4 class="fw-bold mb-3 mt-5 d-flex align-items-center gap-2">
                    <i data-lucide="building-2" style="color:var(--m3-primary);"></i> 3. Institution Hierarchy (University &rarr; College &rarr; Department)
                </h4>

                {% if not departments %}
                <div class="p-4 rounded-4 mb-4" id="noInstAlert" style="background: var(--m3-warning-bg); color: var(--m3-warning-text);">
                    <div class="fw-bold d-flex align-items-center gap-2">
                        <i data-lucide="alert-triangle"></i> No Universities or Departments Registered Yet
                    </div>
                    <div class="small mt-1">If you are the Institution Admin setting up ProTrack for the first time, select <strong>Institution Admin</strong> in Step 1 above to create your University, College, and Department.</div>
                </div>
                {% endif %}

                <div class="m3-card-tonal mb-4">
                    <div class="row g-4">
                        <div class="col-md-4">
                            <label class="form-label" for="uniSelect">University <span class="req-star">*</span></label>
                            <select name="university_id" id="uniSelect" class="form-select" onchange="filterColleges()" required>
                                <option value="">-- Select University --</option>
                                {% for u in universities %}
                                <option value="{{ u.id }}">{{ u.name }}</option>
                                {% endfor %}
                            </select>
                            <div class="mt-2 d-none" id="adminNewUniWrap">
                                <input type="text" name="new_university" id="newUniInput" class="form-control" placeholder="Or register new University name..." oninput="syncAdminRequired()">
                            </div>
                        </div>

                        <div class="col-md-4">
                            <label class="form-label" for="colSelect">College / Institute <span class="req-star">*</span></label>
                            <select name="college_id" id="colSelect" class="form-select" onchange="filterDepartments()" required>
                                <option value="">-- Select College --</option>
                                {% for c in colleges %}
                                <option value="{{ c.id }}" data-uni="{{ c.university_id }}">{{ c.name }}</option>
                                {% endfor %}
                            </select>
                            <div class="mt-2 d-none" id="adminNewColWrap">
                                <input type="text" name="new_college" id="newColInput" class="form-control" placeholder="Or register new College name..." oninput="syncAdminRequired()">
                            </div>
                        </div>

                        <div class="col-md-4">
                            <label class="form-label" for="deptSelect">Department <span class="req-star">*</span></label>
                            <select name="department_id" id="deptSelect" class="form-select" onchange="filterGuides()" required>
                                <option value="">-- Select Department --</option>
                                {% for d in departments %}
                                <option value="{{ d.id }}" data-col="{{ d.college_id }}">{{ d.name }}</option>
                                {% endfor %}
                            </select>
                            <div class="mt-2 d-none" id="adminNewDeptWrap">
                                <input type="text" name="new_department" id="newDeptInput" class="form-control" placeholder="Or register new Department name..." oninput="syncAdminRequired()">
                            </div>
                        </div>

                        <div class="col-md-12" id="studentGuideWrap">
                            <label class="form-label" for="guideSelect">Select Project Guide (Optional — Filtered by Department)</label>
                            <select name="preferred_guide_id" id="guideSelect" class="form-select">
                                <option value="">-- Select Your Faculty Project Guide (or assign later) --</option>
                                {% for g in guides_list %}
                                <option value="{{ g.user.id }}" data-dept="{{ g.department_id }}">
                                    {{ g.user.get_full_name|default:g.user.username }} (ID: {{ g.identifier }} &bull; {{ g.department.name }})
                                </option>
                                {% endfor %}
                            </select>
                        </div>
                    </div>
                </div>

                <!-- 4. ADMIN-ONLY: MANDATORY FRONT & BACK ID PROOF VERIFICATION -->
                <div class="m3-card-tonal mb-4 d-none" id="adminProofSection">
                    <h5 class="fw-bold mb-2 d-flex align-items-center gap-2" style="color:var(--m3-primary);">
                        <i data-lucide="shield-alert"></i> 4. Mandatory Admin Identity Verification (Front & Back ID Proof)
                    </h5>
                    <p class="text-muted small mb-3">
                        To verify your authenticity as an authorized Institution Admin, please upload both the Front and Back of your official institution ID card.
                    </p>
                    <div class="row g-4">
                        <div class="col-md-6">
                            <label class="form-label" for="proofFront">Official Admin ID Proof — Front Side <span class="req-star">*</span></label>
                            <input type="file" name="id_proof_front" id="proofFront" class="form-control" accept=".jpg,.jpeg,.png,.webp,.pdf">
                        </div>
                        <div class="col-md-6">
                            <label class="form-label" for="proofBack">Official Admin ID Proof — Back Side <span class="req-star">*</span></label>
                            <input type="file" name="id_proof_back" id="proofBack" class="form-control" accept=".jpg,.jpeg,.png,.webp,.pdf">
                        </div>
                    </div>
                </div>

                <button type="submit" id="signupSubmitBtn" class="btn-m3-primary w-100 py-3 mt-2 fs-5">
                    <i data-lucide="sparkles"></i> Complete Role-Verified Registration
                </button>
            </form>
        </div>
    </div>
</div>

<script>
function selectRole(role) {
    document.getElementById('selectedRole').value = role;
    ['STUDENT', 'GUIDE', 'ADMIN'].forEach(r => {
        document.getElementById('tab_' + r).classList.toggle('active', r === role);
    });

    const idLabel = document.getElementById('idFieldLabel');
    const idInput = document.getElementById('idFieldInput');
    const studentClassWrap = document.getElementById('studentClassWrap');
    const classDivInput = document.getElementById('classDivInput');
    const studentGuideWrap = document.getElementById('studentGuideWrap');
    const adminProofSection = document.getElementById('adminProofSection');
    const proofFront = document.getElementById('proofFront');
    const proofBack = document.getElementById('proofBack');
    const adminNewUniWrap = document.getElementById('adminNewUniWrap');
    const adminNewColWrap = document.getElementById('adminNewColWrap');
    const adminNewDeptWrap = document.getElementById('adminNewDeptWrap');

    if (role === 'STUDENT') {
        idLabel.innerHTML = 'Roll Call Number <span class="req-star">*</span>';
        idInput.placeholder = 'e.g. CS-2026-01';
        studentClassWrap.classList.remove('d-none');
        classDivInput.required = true;
        studentGuideWrap.classList.remove('d-none');
        adminProofSection.classList.add('d-none');
        proofFront.required = false;
        proofBack.required = false;
        adminNewUniWrap.classList.add('d-none');
        adminNewColWrap.classList.add('d-none');
        adminNewDeptWrap.classList.add('d-none');
    } else if (role === 'GUIDE') {
        idLabel.innerHTML = 'Faculty / Department ID <span class="req-star">*</span>';
        idInput.placeholder = 'e.g. FAC-101';
        studentClassWrap.classList.add('d-none');
        classDivInput.required = false;
        studentGuideWrap.classList.add('d-none');
        adminProofSection.classList.add('d-none');
        proofFront.required = false;
        proofBack.required = false;
        adminNewUniWrap.classList.add('d-none');
        adminNewColWrap.classList.add('d-none');
        adminNewDeptWrap.classList.add('d-none');
    } else if (role === 'ADMIN') {
        idLabel.innerHTML = 'Official Admin ID <span class="req-star">*</span>';
        idInput.placeholder = 'e.g. ADM-001';
        studentClassWrap.classList.add('d-none');
        classDivInput.required = false;
        studentGuideWrap.classList.add('d-none');
        adminProofSection.classList.remove('d-none');
        proofFront.required = true;
        proofBack.required = true;
        adminNewUniWrap.classList.remove('d-none');
        adminNewColWrap.classList.remove('d-none');
        adminNewDeptWrap.classList.remove('d-none');
    }
    syncAdminRequired();
    scheduleUsernameCheck();
}

function syncAdminRequired() {
    const role = document.getElementById('selectedRole').value;
    const uniSelect = document.getElementById('uniSelect');
    const colSelect = document.getElementById('colSelect');
    const deptSelect = document.getElementById('deptSelect');
    const newUni = document.getElementById('newUniInput').value.trim();
    const newCol = document.getElementById('newColInput').value.trim();
    const newDept = document.getElementById('newDeptInput').value.trim();

    if (role === 'ADMIN') {
        uniSelect.required = !newUni;
        colSelect.required = !newCol;
        deptSelect.required = !newDept;
    } else {
        uniSelect.required = true;
        colSelect.required = true;
        deptSelect.required = true;
    }
}

let usernameTimer = null;
function scheduleUsernameCheck() {
    clearTimeout(usernameTimer);
    usernameTimer = setTimeout(checkUsernameAndSuggestions, 220);
}

function checkUsernameAndSuggestions() {
    const u = document.getElementById('usernameInput').value.trim();
    const full = document.getElementById('fullNameInput').value.trim();
    const ident = document.getElementById('idFieldInput').value.trim();
    const errBox = document.getElementById('usernameDupError');
    const submitBtn = document.getElementById('signupSubmitBtn');
    const bar = document.getElementById('suggestionBar');

    const url = `{% url 'api_check_username' %}?username=${encodeURIComponent(u)}&full_name=${encodeURIComponent(full)}&identifier=${encodeURIComponent(ident)}`;
    fetch(url)
        .then(r => r.json())
        .then(data => {
            if (data.exists) {
                errBox.classList.remove('d-none');
                document.getElementById('usernameInput').classList.add('border-danger');
                submitBtn.disabled = true;
            } else {
                errBox.classList.add('d-none');
                document.getElementById('usernameInput').classList.remove('border-danger');
                submitBtn.disabled = false;
            }
            let html = '<span class="small text-muted">Available suggestions:</span>';
            (data.suggestions || []).forEach(s => {
                html += `<span class="suggestion-pill" onclick="pickUsername('${s}')">@${s}</span>`;
            });
            bar.innerHTML = html;
        })
        .catch(() => {});
}

function pickUsername(val) {
    const input = document.getElementById('usernameInput');
    input.value = val;
    input.dispatchEvent(new Event('input', { bubbles: true }));
    checkUsernameAndSuggestions();
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
    filterGuides();
}

function filterGuides() {
    const deptId = document.getElementById('deptSelect').value;
    const guideSelect = document.getElementById('guideSelect');
    if (!guideSelect) return;
    Array.from(guideSelect.options).forEach(opt => {
        if (!opt.value) return;
        opt.hidden = deptId && opt.getAttribute('data-dept') !== deptId;
    });
    guideSelect.value = '';
}

document.addEventListener('DOMContentLoaded', () => {
    checkUsernameAndSuggestions();
});
</script>
{% endblock %}
"""

# ==============================================================================
# 9. STUDENT DASHBOARD TEMPLATE (INTERACTIVE CLASSMATE SEARCH & 5-CHAR JOIN CODE)
# ==============================================================================
STUDENT_DASHBOARD_HTML = """
{% extends 'base.html' %}
{% block content %}

{% if not group %}
<div class="m3-card mb-4">
    <div class="d-flex align-items-center gap-3 mb-4">
        <div class="brand-icon-box"><i data-lucide="users"></i></div>
        <div>
            <h2 class="mb-0 fw-bold">Initialize Your Project Group</h2>
            <div class="text-muted">{{ user.profile.university.name }} &bull; {{ user.profile.college.name }} &bull; <strong>{{ user.profile.department.name }}</strong></div>
        </div>
    </div>

    <div class="row g-4">
        <!-- Option 1: Create Group with Interactive Classmate Search -->
        <div class="col-lg-7">
            <div class="m3-card-tonal h-100">
                <h4 class="fw-bold mb-3 d-flex align-items-center gap-2">
                    <i data-lucide="plus-circle" style="color:var(--m3-primary);"></i> Option 1: Create New Project Group
                </h4>
                <form method="POST" data-autosave="student_create_group">
                    {% csrf_token %}
                    <input type="hidden" name="action" value="create_group">
                    <div class="mb-4">
                        <label class="form-label" for="grpNameInput">Project Group Name</label>
                        <input type="text" name="group_name" id="grpNameInput" class="form-control" placeholder="e.g. Group-01: Cloud Pioneers" required>
                    </div>
                    <div class="mb-4">
                        <label class="form-label" for="grpGuideSelect">Assigned Project Guide ({{ user.profile.department.name }})</label>
                        <select name="guide_id" id="grpGuideSelect" class="form-select">
                            <option value="">-- Select Faculty Guide --</option>
                            {% for g in dept_guides %}
                            <option value="{{ g.id }}" {% if user.profile.preferred_guide_id == g.id %}selected{% endif %}>
                                {{ g.get_full_name|default:g.username }} (ID: {{ g.profile.identifier }})
                            </option>
                            {% endfor %}
                        </select>
                    </div>

                    <!-- Interactive Classmate Search & Selection -->
                    <div class="mb-4">
                        <label class="form-label" for="classmateSearchInput">
                            Add Classmates from {{ user.profile.department.name }} (Optional)
                        </label>
                        <div class="position-relative">
                            <input type="text" id="classmateSearchInput" class="form-control" placeholder="Type a classmate's first name or Roll Call to search {{ user.profile.department.name }}..." autocomplete="off" oninput="searchClassmatesLive(this.value)">
                            <div id="classmateDropdown" class="list-group shadow-lg mt-1 d-none" style="position:absolute; width:100%; z-index:1050; border-radius:18px; max-height:260px; overflow-y:auto;"></div>
                        </div>

                        <div id="selectedTeammatesBox" class="d-flex flex-wrap gap-2 mt-3"></div>
                        <div id="selectedTeammatesInputs"></div>

                        <div class="small text-muted mt-2 d-flex align-items-center gap-2">
                            <i data-lucide="info" style="width:16px;height:16px;flex-shrink:0;"></i>
                            <span>Can't find your teammate yet? You can continue without selecting them—unregistered classmates can join anytime using your group's unique <strong>5-character Join Code</strong> generated right after creation.</span>
                        </div>
                    </div>

                    <button type="submit" class="btn-m3-primary w-100">
                        <i data-lucide="rocket"></i> Create Group & Generate 5-Character Join Code
                    </button>
                </form>
            </div>
        </div>

        <!-- Option 2: Join Existing Group by 5-Character Code -->
        <div class="col-lg-5">
            <div class="m3-card-tonal h-100 d-flex flex-column justify-content-between">
                <div>
                    <h4 class="fw-bold mb-3 d-flex align-items-center gap-2">
                        <i data-lucide="key-round" style="color:var(--m3-primary);"></i> Option 2: Join Teammate's Group
                    </h4>
                    <p class="text-muted mb-4">
                        Have an existing <strong>5-character alphanumeric Group Join Code</strong> from a classmate in <strong>{{ user.profile.department.name }}</strong>? Enter it below:
                    </p>
                    <form method="POST" data-autosave="student_join_group">
                        {% csrf_token %}
                        <input type="hidden" name="action" value="join_group">
                        <div class="mb-4">
                            <label class="form-label" for="joinCodeInput">5-Character Group Join Code</label>
                            <input type="text" name="join_code" id="joinCodeInput" class="form-control text-uppercase fw-bold fs-4 text-center" style="letter-spacing: 0.2em;" maxlength="5" minlength="5" pattern="[A-Za-z0-9]{5}" placeholder="A8K2P" required>
                        </div>
                        <button type="submit" class="btn-m3-tonal w-100">
                            <i data-lucide="user-check"></i> Validate Code & Join Group
                        </button>
                    </form>
                </div>

                <div class="border-top pt-3 mt-4 small text-muted">
                    <i data-lucide="shield-check" style="width:15px;height:15px;"></i>
                    Join codes are strictly validated on the backend and restricted to eligible students in <strong>{{ user.profile.department.name }}</strong>.
                </div>
            </div>
        </div>
    </div>
</div>

<script>
const selectedTeammates = new Map();

function searchClassmatesLive(query) {
    const box = document.getElementById('classmateDropdown');
    const q = query.trim();
    if (!q) {
        box.classList.add('d-none');
        box.innerHTML = '';
        return;
    }
    fetch(`{% url 'api_search_classmates' %}?q=${encodeURIComponent(q)}`)
        .then(r => r.json())
        .then(data => {
            const list = (data.results || []).filter(item => !selectedTeammates.has(item.user_id));
            box.classList.remove('d-none');
            if (list.length === 0) {
                box.innerHTML = `<div class="list-group-item p-3 text-muted small">No matching unassigned student found in {{ user.profile.department.name }}. You can proceed and share your 5-character Group Join Code after creating the group!</div>`;
                return;
            }
            box.innerHTML = list.map(item => `
                <button type="button" class="list-group-item list-group-item-action p-3 d-flex align-items-center justify-content-between" onclick="addTeammate(${item.user_id}, '${item.full_name.replace(/'/g, "\\'")}', '${item.identifier.replace(/'/g, "\\'")}')">
                    <div>
                        <div class="fw-bold text-dark">${item.full_name}</div>
                        <div class="small text-muted">Roll Call: ${item.identifier} &bull; ${item.class_division}</div>
                    </div>
                    <span class="m3-chip chip-tonal py-1 px-3">+ Select</span>
                </button>
            `).join('');
        });
}

function addTeammate(uid, fullName, ident) {
    selectedTeammates.set(uid, { fullName, ident });
    document.getElementById('classmateSearchInput').value = '';
    document.getElementById('classmateDropdown').classList.add('d-none');
    renderSelectedTeammates();
}

function removeTeammate(uid) {
    selectedTeammates.delete(uid);
    renderSelectedTeammates();
}

function renderSelectedTeammates() {
    const chipBox = document.getElementById('selectedTeammatesBox');
    const inputBox = document.getElementById('selectedTeammatesInputs');
    let chipsHtml = '';
    let inputsHtml = '';
    selectedTeammates.forEach((info, uid) => {
        chipsHtml += `
            <span class="m3-chip chip-tonal py-2 px-3">
                ${info.fullName} (${info.ident})
                <button type="button" class="btn-close ms-2" style="font-size:0.65rem;" onclick="removeTeammate(${uid})"></button>
            </span>
        `;
        inputsHtml += `<input type="hidden" name="teammate_ids" value="${uid}">`;
    });
    chipBox.innerHTML = chipsHtml;
    inputBox.innerHTML = inputsHtml;
}
</script>

{% else %}
<!-- ACTIVE STUDENT GROUP WORKSPACE -->
<div class="m3-card mb-4">
    <div class="row align-items-center g-4">
        <div class="col-lg-7">
            <div class="d-flex flex-wrap align-items-center gap-2 mb-3">
                <span class="m3-chip chip-tonal"><i data-lucide="users" style="width:16px;height:16px;"></i> {{ group.name }}</span>
                <span class="m3-chip chip-neutral" style="letter-spacing:0.06em;">
                    <i data-lucide="key-round" style="width:16px;height:16px;"></i> 5-Char Join Code: <strong class="text-dark">{{ group.join_code }}</strong>
                </span>
                {% if proposal %}
                    {% if proposal.status == 'APPROVED' %}
                    <span class="m3-chip chip-success"><i data-lucide="check-circle" style="width:16px;height:16px;"></i> Approved</span>
                    {% elif proposal.status == 'CHANGES' %}
                    <span class="m3-chip chip-danger"><i data-lucide="alert-circle" style="width:16px;height:16px;"></i> Revisions Requested</span>
                    {% else %}
                    <span class="m3-chip chip-warning"><i data-lucide="clock" style="width:16px;height:16px;"></i> Pending Review</span>
                    {% endif %}
                {% endif %}
            </div>
            <h2 class="fw-bold mb-2">{{ proposal.title|default:"Project Proposal Not Submitted Yet" }}</h2>
            <div class="d-flex flex-wrap align-items-center gap-2 mt-3">
                <span class="text-muted fw-medium me-1">Team Members:</span>
                {% for s in group.students.all %}
                <span class="m3-chip chip-neutral py-1 px-3">
                    <a href="{% url 'public_profile' s.username %}" class="text-dark text-decoration-none fw-bold">{{ s.get_full_name|default:s.username }}</a>
                    <span class="text-muted">({{ s.profile.identifier }})</span>
                    {% if s.email %}
                    <a href="mailto:{{ s.email }}" class="text-primary ms-1" title="Email {{ s.email }}"><i data-lucide="mail" style="width:15px;height:15px;"></i></a>
                    {% endif %}
                    {% if s.profile.clean_whatsapp %}
                    <a href="https://wa.me/{{ s.profile.clean_whatsapp }}?text=Hi%20{{ s.get_full_name|urlencode }},%20connecting%20from%20ProTrack" target="_blank" class="text-success ms-1" title="WhatsApp Chat"><i data-lucide="message-circle" style="width:15px;height:15px;"></i></a>
                    {% endif %}
                </span>
                {% endfor %}
            </div>
        </div>

        <div class="col-lg-5">
            <div class="m3-card-tonal p-4">
                <div class="d-flex justify-content-between align-items-center flex-wrap gap-2">
                    <div class="d-flex align-items-center gap-3">
                        {% if group.guide %}
                        <a href="{% url 'public_profile' group.guide.username %}" class="avatar-circle">
                            {% if group.guide.profile.has_avatar %}
                            <img src="{{ group.guide.profile.avatar_url }}" alt="Guide">
                            {% else %}
                            {{ group.guide.profile.initials }}
                            {% endif %}
                        </a>
                        <div>
                            <div class="small text-muted">Assigned Project Guide</div>
                            <a href="{% url 'public_profile' group.guide.username %}" class="fw-bold fs-5 text-dark text-decoration-none">{{ group.guide.get_full_name|default:group.guide.username }}</a>
                            <div class="d-flex flex-wrap gap-2 mt-2">
                                {% if group.guide.email %}
                                <a href="mailto:{{ group.guide.email }}" class="btn-m3-outline py-1 px-3 text-decoration-none" style="min-height:34px;font-size:0.85rem;">
                                    <i data-lucide="mail" style="width:14px;height:14px;"></i> Email
                                </a>
                                {% endif %}
                                {% if group.guide.profile.clean_whatsapp %}
                                <a href="https://wa.me/{{ group.guide.profile.clean_whatsapp }}?text=Hello%20{{ group.guide.get_full_name|urlencode }},%20we%20are%20from%20{{ group.name|urlencode }}" target="_blank" class="btn-whatsapp py-1 px-3">
                                    <i data-lucide="message-circle" style="width:14px;height:14px;"></i> WhatsApp
                                </a>
                                {% endif %}
                            </div>
                        </div>
                        {% else %}
                        <div>
                            <div class="small text-muted">Project Guide</div>
                            <div class="text-danger fw-bold">Unassigned</div>
                        </div>
                        {% endif %}
                    </div>
                    {% if viva %}
                    <div class="text-end">
                        <div class="small text-muted">Final Viva Grade</div>
                        <span class="m3-chip chip-success fs-5">{{ viva.total_score }}/100 &bull; {{ viva.grade_badge }}</span>
                    </div>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>
</div>

<div class="row g-4">
    <!-- Proposal & TF-IDF Originality Scanner -->
    <div class="col-lg-7">
        <div class="m3-card h-100">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h3 class="fw-bold mb-0 d-flex align-items-center gap-2">
                    <i data-lucide="file-text" style="color:var(--m3-primary);"></i> Proposal & AI Similarity Engine
                </h3>
                {% if proposal %}
                <span class="m3-chip {% if proposal.similarity_score >= 60 %}chip-danger{% elif proposal.similarity_score >= 30 %}chip-warning{% else %}chip-success{% endif %}">
                    Similarity: {{ proposal.similarity_score }}%
                </span>
                {% endif %}
            </div>

            {% if proposal.guide_remarks %}
            <div class="p-4 mb-4 rounded-4" style="background: var(--m3-warning-bg); color: var(--m3-warning-text);">
                <div class="fw-bold d-flex align-items-center gap-2 mb-1">
                    <i data-lucide="message-square"></i> Guide Feedback:
                </div>
                <div>{{ proposal.guide_remarks }}</div>
            </div>
            {% endif %}

            <form method="POST" enctype="multipart/form-data" data-autosave="student_proposal_form">
                {% csrf_token %}
                <input type="hidden" name="action" value="submit_proposal">
                <div class="mb-4">
                    <label class="form-label" for="propTitle">Project Title</label>
                    <input type="text" name="title" id="propTitle" class="form-control" value="{{ proposal.title|default:'' }}" placeholder="e.g. Cloud-Native Academic Governance Platform" required>
                </div>
                <div class="mb-4">
                    <label class="form-label" for="propDomain">Technical Domain</label>
                    <input type="text" name="domain" id="propDomain" class="form-control" value="{{ proposal.domain|default:'' }}" placeholder="e.g. Artificial Intelligence, Distributed Systems, Cybersecurity" required>
                </div>
                <div class="mb-4">
                    <label class="form-label" for="propAbstract">Detailed Abstract</label>
                    <textarea name="abstract" id="propAbstract" rows="6" class="form-control" placeholder="Outline the problem statement, system architecture, algorithms, and expected deliverables..." required>{{ proposal.abstract|default:'' }}</textarea>
                </div>

                <div id="simResultBox" class="m3-card-tonal p-4 mb-4 d-none">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <span class="fw-bold d-flex align-items-center gap-2">
                            <i data-lucide="cpu" style="color:var(--m3-primary);"></i> Scikit-Learn TF-IDF Similarity Result
                        </span>
                        <span id="simBadge" class="m3-chip chip-tonal">0%</span>
                    </div>
                    <div class="small text-muted">Closest Corpus Match: <strong id="simMatch" class="text-dark">None</strong></div>
                </div>

                <div class="mb-4">
                    <label class="form-label" for="propFile">Upload Synopsis / Blackbook Documentation (Optional — PDF, DOCX, PNG)</label>
                    <input type="file" name="report_file" id="propFile" class="form-control" accept=".pdf,.docx,.doc,.png,.jpg,.jpeg">
                    {% if proposal.report_file %}
                    <div class="mt-2">
                        <a href="{{ proposal.report_file.url }}" target="_blank" class="btn-m3-outline py-2 px-3 text-decoration-none">
                            <i data-lucide="external-link"></i> View Uploaded Document
                        </a>
                    </div>
                    {% endif %}
                </div>

                <div class="d-flex flex-wrap gap-3">
                    <button type="button" onclick="runSimilarityCheck()" id="btnSimCheck" class="btn-m3-tonal">
                        <i data-lucide="sparkles"></i> Scan Abstract Originality
                    </button>
                    <button type="submit" class="btn-m3-primary flex-grow-1">
                        <i data-lucide="send"></i> Submit Proposal to Guide
                    </button>
                </div>
            </form>
        </div>
    </div>

    <!-- Weekly Progress Logbook -->
    <div class="col-lg-5">
        <div class="m3-card h-100">
            <h3 class="fw-bold mb-4 d-flex align-items-center gap-2">
                <i data-lucide="calendar-check" style="color:var(--m3-primary);"></i> Weekly Logbook
            </h3>

            <form method="POST" class="m3-card-tonal p-4 mb-4" data-autosave="student_weekly_log_form">
                {% csrf_token %}
                <input type="hidden" name="action" value="submit_log">
                <div class="row g-3 mb-3">
                    <div class="col-4">
                        <label class="form-label" for="logWeek">Week #</label>
                        <input type="number" name="week_number" id="logWeek" class="form-control" value="{{ next_week }}" min="1" max="52" required>
                    </div>
                    <div class="col-8">
                        <label class="form-label" for="logTasks">Tasks Completed</label>
                        <input type="text" name="tasks_completed" id="logTasks" class="form-control" placeholder="e.g. ER diagram & API routes" required>
                    </div>
                </div>
                <div class="mb-3">
                    <label class="form-label" for="logPlan">Next Week Target Plan</label>
                    <input type="text" name="next_week_plan" id="logPlan" class="form-control" placeholder="e.g. Frontend views & testing" required>
                </div>
                <button type="submit" class="btn-m3-primary w-100">
                    <i data-lucide="plus"></i> Add Weekly Log Entry
                </button>
            </form>

            <div class="d-flex flex-column gap-3" style="max-height: 440px; overflow-y: auto;">
                {% for log in logs %}
                <div class="p-4 border rounded-4 bg-white">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <span class="fw-bold fs-5">Week {{ log.week_number }}</span>
                        {% if log.is_verified %}
                        <span class="m3-chip chip-success py-1 px-3"><i data-lucide="check" style="width:15px;height:15px;"></i> Verified</span>
                        {% else %}
                        <span class="m3-chip chip-warning py-1 px-3">Pending Sign-Off</span>
                        {% endif %}
                    </div>
                    <div class="mb-1"><strong>Completed:</strong> {{ log.tasks_completed }}</div>
                    <div class="text-muted"><strong>Next Plan:</strong> {{ log.next_week_plan }}</div>
                    {% if log.guide_feedback %}
                    <div class="mt-2 pt-2 border-top" style="color:var(--m3-primary);">
                        <strong>Guide Remark:</strong> {{ log.guide_feedback }}
                    </div>
                    {% endif %}
                </div>
                {% empty %}
                <div class="text-center py-5 text-muted">
                    <i data-lucide="clipboard-list" class="mb-2" style="width:36px;height:36px;"></i>
                    <div>No weekly progress logs recorded yet.</div>
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
    btn.innerText = 'Analyzing Corpus...';

    const formData = new FormData();
    formData.append('title', title);
    formData.append('abstract', abstract);
    formData.append('csrfmiddlewaretoken', '{{ csrf_token }}');

    fetch("{% url 'api_check_similarity' %}", { method: 'POST', body: formData })
    .then(r => r.json())
    .then(data => {
        btn.disabled = false;
        btn.innerHTML = '<i data-lucide="sparkles"></i> Scan Abstract Originality';
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
# 10. FACULTY GUIDE DASHBOARD TEMPLATE (guide_dashboard.html)
# ==============================================================================
GUIDE_DASHBOARD_HTML = """
{% extends 'base.html' %}
{% block content %}
<div class="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
    <div>
        <h1 class="fw-bold mb-1">Faculty Guide Mentoring Console</h1>
        <div class="text-muted">Review proposals, verify weekly logs, and connect with mentees in <strong>{{ user.profile.department.name }}</strong></div>
    </div>
    <div class="d-flex flex-wrap gap-2">
        <span class="m3-chip chip-tonal">Mentored Groups: {{ my_groups.count }}</span>
        <span class="m3-chip chip-warning">Pending Proposals: {{ pending_proposals }}</span>
        <span class="m3-chip chip-neutral">Unverified Logs: {{ unverified_logs }}</span>
    </div>
</div>

{% if unassigned_groups %}
<div class="m3-card-tonal mb-4">
    <h4 class="fw-bold mb-3 d-flex align-items-center gap-2">
        <i data-lucide="user-plus" style="color:var(--m3-primary);"></i> Unassigned Student Groups in {{ user.profile.department.name }}
    </h4>
    <div class="row g-3">
        {% for ug in unassigned_groups %}
        <div class="col-md-6">
            <div class="bg-white p-4 rounded-4 border d-flex justify-content-between align-items-center">
                <div>
                    <div class="fw-bold fs-5">{{ ug.name }} <span class="text-muted small">(Code: {{ ug.join_code }})</span></div>
                    <div class="small text-muted">Students: {% for s in ug.students.all %}<a href="{% url 'public_profile' s.username %}" class="text-dark fw-medium">{{ s.get_full_name|default:s.username }}</a>{% if not forloop.last %}, {% endif %}{% endfor %}</div>
                </div>
                <form method="POST" class="no-legend">
                    {% csrf_token %}
                    <input type="hidden" name="action" value="claim_group">
                    <input type="hidden" name="group_id" value="{{ ug.id }}">
                    <button type="submit" class="btn-m3-tonal">Accept Group</button>
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
            <div class="d-flex align-items-center gap-2 mb-2">
                <span class="m3-chip chip-tonal">{{ g.name }}</span>
                <span class="m3-chip chip-neutral">5-Char Code: {{ g.join_code }}</span>
            </div>
            <div class="d-flex flex-wrap gap-2 align-items-center">
                <strong class="me-1">Students:</strong>
                {% for s in g.students.all %}
                <span class="m3-chip chip-neutral py-1 px-3">
                    <a href="{% url 'public_profile' s.username %}" class="text-dark text-decoration-none fw-bold">{{ s.get_full_name|default:s.username }}</a> ({{ s.profile.identifier }})
                    {% if s.email %}
                    <a href="mailto:{{ s.email }}" class="text-primary ms-1" title="Email Student"><i data-lucide="mail" style="width:15px;height:15px;"></i></a>
                    {% endif %}
                    {% if s.profile.clean_whatsapp %}
                    <a href="https://wa.me/{{ s.profile.clean_whatsapp }}?text=Hello%20{{ s.get_full_name|urlencode }},%20regarding%20your%20project%20in%20ProTrack" target="_blank" class="text-success ms-1" title="WhatsApp Student"><i data-lucide="message-circle" style="width:16px;height:16px;"></i></a>
                    {% endif %}
                </span>
                {% endfor %}
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
        <div class="col-lg-7">
            <h4 class="fw-bold mb-3 d-flex align-items-center gap-2">
                <i data-lucide="file-check" style="color:var(--m3-primary);"></i> Proposal Evaluation
            </h4>
            {% if g.proposal %}
            <div class="m3-card-tonal p-4">
                <h4 class="fw-bold mb-1">{{ g.proposal.title }}</h4>
                <div class="small fw-bold mb-3" style="color:var(--m3-primary);">
                    Domain: {{ g.proposal.domain }} &bull; Closest Match: {{ g.proposal.closest_match_title }}
                </div>
                <p class="mb-4">{{ g.proposal.abstract }}</p>

                {% if g.proposal.report_file %}
                <div class="mb-4">
                    <a href="{{ g.proposal.report_file.url }}" target="_blank" class="btn-m3-outline text-decoration-none">
                        <i data-lucide="download"></i> Inspect Uploaded Synopsis / Report
                    </a>
                </div>
                {% endif %}

                <form method="POST" class="border-top pt-4" data-autosave="guide_review_{{ g.proposal.id }}">
                    {% csrf_token %}
                    <input type="hidden" name="action" value="review_proposal">
                    <input type="hidden" name="proposal_id" value="{{ g.proposal.id }}">
                    <div class="mb-3">
                        <label class="form-label">Guide Review Remarks</label>
                        <input type="text" name="guide_remarks" class="form-control" value="{{ g.proposal.guide_remarks }}" placeholder="Provide constructive instructions or approval notes...">
                    </div>
                    <div class="d-flex flex-wrap gap-3">
                        <button type="submit" name="decision" value="APPROVED" class="btn-m3-primary">
                            <i data-lucide="check-circle"></i> Approve Proposal
                        </button>
                        <button type="submit" name="decision" value="CHANGES" class="btn-m3-outline text-danger border-danger">
                            <i data-lucide="refresh-cw"></i> Request Changes
                        </button>
                    </div>
                </form>
            </div>
            {% else %}
            <div class="m3-card-tonal text-center py-5 text-muted">
                <i data-lucide="file-clock" class="mb-2" style="width:36px;height:36px;"></i>
                <div>This group has not submitted their proposal yet.</div>
            </div>
            {% endif %}
        </div>

        <div class="col-lg-5">
            <h4 class="fw-bold mb-3 d-flex align-items-center gap-2">
                <i data-lucide="list-checks" style="color:var(--m3-primary);"></i> Weekly Logbook Sign-Off
            </h4>
            <div class="d-flex flex-column gap-3" style="max-height: 460px; overflow-y: auto;">
                {% for log in g.logs.all %}
                <div class="p-4 border rounded-4 bg-white">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <span class="fw-bold fs-5">Week {{ log.week_number }}</span>
                        {% if log.is_verified %}
                        <span class="m3-chip chip-success py-1 px-3">Verified</span>
                        {% else %}
                        <span class="m3-chip chip-warning py-1 px-3">Needs Sign-Off</span>
                        {% endif %}
                    </div>
                    <div class="mb-1"><strong>Completed:</strong> {{ log.tasks_completed }}</div>
                    <div class="text-muted mb-2"><strong>Next Plan:</strong> {{ log.next_week_plan }}</div>

                    {% if not log.is_verified %}
                    <form method="POST" class="d-flex gap-2 mt-3 pt-3 border-top no-legend">
                        {% csrf_token %}
                        <input type="hidden" name="action" value="verify_log">
                        <input type="hidden" name="log_id" value="{{ log.id }}">
                        <input type="text" name="guide_feedback" class="form-control" placeholder="Add mentor comment...">
                        <button type="submit" class="btn-m3-primary px-4">Verify</button>
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
    <i data-lucide="users" style="width:48px;height:48px;color:var(--m3-primary);" class="mb-3"></i>
    <h3 class="fw-bold">No Active Groups Under Your Mentorship Yet</h3>
    <p class="text-muted mb-0">Students who selected you during registration ({{ registered_mentees.count }} students) will appear here as soon as they initialize their project group.</p>
</div>
{% endfor %}
{% endblock %}
"""

# ==============================================================================
# 11. EXAMINER & HOD PORTAL TEMPLATE (examiner_viva.html)
# ==============================================================================
EXAMINER_VIVA_HTML = """
{% extends 'base.html' %}
{% block content %}
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<div class="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
    <div>
        <div class="m3-chip chip-tonal mb-2"><i data-lucide="award" style="width:16px;height:16px;"></i> Examiner & HOD Analytics Workspace</div>
        <h1 class="fw-bold mb-1">Department Assessment & Viva Grading Center</h1>
        <div class="text-muted">{{ user.profile.university.name }} &bull; {{ user.profile.college.name }} &bull; <strong>{{ user.profile.department.name }}</strong></div>
    </div>
    <div class="d-flex flex-wrap gap-2">
        <a href="{% url 'export_department_csv' %}" class="btn-m3-primary text-decoration-none">
            <i data-lucide="download"></i> Export Master Gradebook (CSV)
        </a>
    </div>
</div>

<!-- HOD Analytics KPIs -->
<div class="row g-4 mb-4">
    <div class="col-md-3 col-6">
        <div class="m3-card p-4">
            <div class="text-muted small mb-1">Department Groups</div>
            <div class="display-5 fw-bold" style="color:var(--m3-primary);">{{ groups.count }}</div>
        </div>
    </div>
    <div class="col-md-3 col-6">
        <div class="m3-card p-4">
            <div class="text-muted small mb-1">Enrolled Students</div>
            <div class="display-5 fw-bold text-dark">{{ dept_students_count }}</div>
        </div>
    </div>
    <div class="col-md-3 col-6">
        <div class="m3-card p-4">
            <div class="text-muted small mb-1">Approved Proposals</div>
            <div class="display-5 fw-bold text-success">{{ approved_count }}</div>
        </div>
    </div>
    <div class="col-md-3 col-6">
        <div class="m3-card p-4">
            <div class="text-muted small mb-1">Vivas Graded</div>
            <div class="display-5 fw-bold" style="color:var(--m3-primary);">{{ evaluated_count }}</div>
        </div>
    </div>
</div>

<!-- HOD Analytics Chart + TF-IDF Corpus Manager -->
<div class="row g-4 mb-5">
    <div class="col-lg-4">
        <div class="m3-card h-100">
            <h4 class="fw-bold mb-3 d-flex align-items-center gap-2">
                <i data-lucide="pie-chart" style="color:var(--m3-primary);"></i> Proposal Status Distribution
            </h4>
            <canvas id="examinerChart" height="220"></canvas>
        </div>
    </div>
    <div class="col-lg-8">
        <div class="m3-card h-100">
            <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
                <div>
                    <h4 class="fw-bold mb-1 d-flex align-items-center gap-2">
                        <i data-lucide="database" style="color:var(--m3-primary);"></i> Department TF-IDF Archive Corpus ({{ archives.count }} Records)
                    </h4>
                    <div class="text-muted small">Manage benchmark past projects used to detect abstract similarity in {{ user.profile.department.name }}.</div>
                </div>
                <form method="POST" class="no-legend">
                    {% csrf_token %}
                    <input type="hidden" name="action" value="seed_corpus">
                    <button type="submit" class="btn-m3-tonal py-2 px-3">
                        <i data-lucide="sparkles"></i> Load 5 Benchmark Abstracts
                    </button>
                </form>
            </div>

            <form method="POST" class="m3-card-tonal p-3 mb-3" data-autosave="examiner_add_archive">
                {% csrf_token %}
                <input type="hidden" name="action" value="add_archive">
                <div class="row g-2">
                    <div class="col-md-4">
                        <label class="form-label small">Archive Title</label>
                        <input type="text" name="title" class="form-control" placeholder="Past Project Title" required>
                    </div>
                    <div class="col-md-2">
                        <label class="form-label small">Year</label>
                        <input type="text" name="year" class="form-control" value="2025" required>
                    </div>
                    <div class="col-md-4">
                        <label class="form-label small">Abstract Summary</label>
                        <input type="text" name="abstract" class="form-control" placeholder="Paste project abstract summary..." required>
                    </div>
                    <div class="col-md-2 d-flex align-items-end">
                        <button type="submit" class="btn-m3-primary w-100">Add</button>
                    </div>
                </div>
            </form>

            <div class="row g-2" style="max-height: 180px; overflow-y: auto;">
                {% for a in archives %}
                <div class="col-md-6">
                    <div class="p-3 border rounded-4 bg-white small">
                        <div class="fw-bold">{{ a.title }} ({{ a.year }})</div>
                        <div class="text-muted">{{ a.abstract|truncatechars:100 }}</div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
    </div>
</div>

<!-- 100-Point 4-Pillar Viva Rubric Evaluation Cards -->
<h3 class="fw-bold mb-4 d-flex align-items-center gap-2">
    <i data-lucide="clipboard-check" style="color:var(--m3-primary);"></i> Live 100-Point Viva Voce Evaluation Rubrics
</h3>

{% for g in groups %}
<div class="m3-card mb-4">
    <div class="row g-4">
        <div class="col-lg-6">
            <div class="d-flex flex-wrap align-items-center gap-2 mb-3">
                <span class="m3-chip chip-tonal">{{ g.name }}</span>
                <span class="m3-chip chip-neutral">5-Char Code: {{ g.join_code }}</span>
                <span class="m3-chip chip-neutral">Guide: {% if g.guide %}<a href="{% url 'public_profile' g.guide.username %}" class="text-dark text-decoration-none">{{ g.guide.get_full_name|default:g.guide.username }}</a>{% else %}Unassigned{% endif %}</span>
                {% if g.proposal %}
                <span class="m3-chip {% if g.proposal.similarity_score >= 60 %}chip-danger{% elif g.proposal.similarity_score >= 30 %}chip-warning{% else %}chip-success{% endif %}">
                    Similarity: {{ g.proposal.similarity_score }}%
                </span>
                {% endif %}
            </div>
            <h3 class="fw-bold mb-2">{{ g.proposal.title|default:"Proposal Pending Submission" }}</h3>
            <p class="text-muted mb-3">{{ g.proposal.abstract|default:"No abstract submitted yet." }}</p>
            <div class="mb-3">
                <strong>Examinees:</strong>
                {% for s in g.students.all %}
                <a href="{% url 'public_profile' s.username %}" class="m3-chip chip-neutral py-1 px-3 me-1 mb-1 text-decoration-none text-dark">{{ s.get_full_name|default:s.username }} ({{ s.profile.identifier }})</a>
                {% endfor %}
            </div>
            {% if g.proposal and g.proposal.report_file %}
            <a href="{{ g.proposal.report_file.url }}" target="_blank" class="btn-m3-tonal text-decoration-none">
                <i data-lucide="file-text"></i> Open Submitted Project Report
            </a>
            {% endif %}
        </div>

        <div class="col-lg-6">
            <form method="POST" class="m3-card-tonal p-4" data-autosave="viva_rubric_{{ g.id }}">
                {% csrf_token %}
                <input type="hidden" name="action" value="grade_viva">
                <input type="hidden" name="group_id" value="{{ g.id }}">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h4 class="fw-bold mb-0">4-Pillar Viva Rubric</h4>
                    <span class="m3-chip chip-success fs-5" id="totalBadge_{{ g.id }}">
                        Total: {{ g.viva.total_score|default:80 }} / 100
                    </span>
                </div>

                <div class="row g-3 mb-3">
                    <div class="col-sm-6">
                        <label class="form-label">1. Problem Clarity (0–25)</label>
                        <input type="number" name="problem_clarity" class="form-control rubric-{{ g.id }}" min="0" max="25" value="{{ g.viva.problem_clarity|default:20 }}" oninput="calcViva({{ g.id }})" required>
                    </div>
                    <div class="col-sm-6">
                        <label class="form-label">2. Implementation (0–25)</label>
                        <input type="number" name="implementation" class="form-control rubric-{{ g.id }}" min="0" max="25" value="{{ g.viva.implementation|default:20 }}" oninput="calcViva({{ g.id }})" required>
                    </div>
                    <div class="col-sm-6">
                        <label class="form-label">3. Presentation & Defense (0–25)</label>
                        <input type="number" name="presentation" class="form-control rubric-{{ g.id }}" min="0" max="25" value="{{ g.viva.presentation|default:20 }}" oninput="calcViva({{ g.id }})" required>
                    </div>
                    <div class="col-sm-6">
                        <label class="form-label">4. Documentation (0–25)</label>
                        <input type="number" name="documentation" class="form-control rubric-{{ g.id }}" min="0" max="25" value="{{ g.viva.documentation|default:20 }}" oninput="calcViva({{ g.id }})" required>
                    </div>
                </div>

                <div class="mb-3">
                    <label class="form-label">Examiner Evaluation Remarks</label>
                    <input type="text" name="examiner_comments" class="form-control" value="{{ g.viva.examiner_comments|default:'' }}" placeholder="Enter official examiner remarks...">
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
    No project groups registered in {{ user.profile.department.name }} yet.
</div>
{% endfor %}

<script>
new Chart(document.getElementById('examinerChart'), {
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
# 12. REORDERED ADMIN DASHBOARD TEMPLATE (admin_dashboard.html)
#     Order: 1. Faculty Guides & Examiner Role Assignment
#            2. Enrolled Students Dataset
#            3. Descending Hierarchy Engine (Very Last)
#     (Verified Admin ID Proofs moved to Profile Settings)
# ==============================================================================
ADMIN_DASHBOARD_HTML = """
{% extends 'base.html' %}
{% block content %}
<div class="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
    <div>
        <div class="m3-chip chip-tonal mb-2">
            <i data-lucide="shield-check" style="width:16px;height:16px;"></i>
            Verified Institution Admin &bull; ID: {{ user.profile.identifier }}
        </div>
        <h1 class="fw-bold mb-1">Institution Governance & Role Command Center</h1>
        <div class="text-muted">Authorized Scope: <strong>{{ user.profile.college.name }}</strong> ({{ user.profile.university.name }})</div>
    </div>
    <div class="d-flex flex-wrap gap-2">
        <a href="{% url 'profile_settings' %}#admin-id-proofs" class="btn-m3-outline text-decoration-none">
            <i data-lucide="file-badge"></i> View Admin ID Proofs in Settings
        </a>
        <a href="{% url 'export_department_csv' %}" class="btn-m3-primary text-decoration-none">
            <i data-lucide="download"></i> Export Master CSV
        </a>
    </div>
</div>

<!-- GLOBAL DATASET FILTER BAR -->
<div class="m3-card-tonal p-4 mb-4">
    <form method="GET" class="row g-3 align-items-end no-legend">
        <div class="col-md-5">
            <label class="form-label">Filter Datasets by Authorized Department</label>
            <select name="dept_id" class="form-select" onchange="this.form.submit()">
                <option value="">All Departments in {{ user.profile.college.name }} ({{ all_departments.count }})</option>
                {% for d in all_departments %}
                <option value="{{ d.id }}" {% if dept_filter == d.id|stringformat:"s" %}selected{% endif %}>
                    {{ d.college.name }} &rarr; {{ d.name }}
                </option>
                {% endfor %}
            </select>
        </div>
        <div class="col-md-5">
            <label class="form-label">Search by Name or ID</label>
            <input type="text" name="q" class="form-control" value="{{ search_q }}" placeholder="e.g. John Doe, FAC-101, CS-2026-01...">
        </div>
        <div class="col-md-2">
            <button type="submit" class="btn-m3-primary w-100">
                <i data-lucide="search"></i> Filter
            </button>
        </div>
    </form>
</div>

<!-- SECTION 1 (HIGHEST PRIORITY): FACULTY GUIDES & EXAMINER ROLE ASSIGNMENT -->
<div class="m3-card mb-5">
    <div class="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
        <div>
            <h3 class="fw-bold mb-1 d-flex align-items-center gap-2">
                <i data-lucide="award" style="color:var(--m3-primary);"></i> 1. Faculty Guides & Examiner Role Assignment
            </h3>
            <div class="text-muted">Promote any registered Faculty Guide in {{ user.profile.college.name }} to External Examiner or demote them in one click.</div>
        </div>
        <span class="m3-chip chip-tonal">Active Examiners: {{ examiners_count }}</span>
    </div>

    <div class="table-responsive">
        <table class="table align-middle">
            <thead class="text-muted">
                <tr>
                    <th>Faculty Guide</th>
                    <th>Faculty ID</th>
                    <th>Department</th>
                    <th>Direct Contact</th>
                    <th>Current Role Status</th>
                    <th class="text-end">Examiner Governance</th>
                </tr>
            </thead>
            <tbody>
                {% for g in guides_qs %}
                <tr>
                    <td>
                        <div class="d-flex align-items-center gap-3">
                            <a href="{% url 'public_profile' g.user.username %}" class="avatar-circle">
                                {% if g.has_avatar %}
                                <img src="{{ g.avatar_url }}" alt="{{ g.user.get_full_name|default:g.user.username }}">
                                {% else %}
                                {{ g.initials }}
                                {% endif %}
                            </a>
                            <div>
                                <a href="{% url 'public_profile' g.user.username %}" class="fw-bold text-dark text-decoration-none">{{ g.user.get_full_name|default:g.user.username }}</a>
                                <div class="small text-muted">
                                    <a href="{% url 'public_profile' g.user.username %}" class="text-muted text-decoration-none">@{{ g.user.username }}</a>
                                    {% if g.user.email %} &bull; <a href="mailto:{{ g.user.email }}" class="text-primary text-decoration-none">{{ g.user.email }}</a>{% endif %}
                                </div>
                            </div>
                        </div>
                    </td>
                    <td><span class="m3-chip chip-neutral">{{ g.identifier }}</span></td>
                    <td>
                        <div class="fw-medium">{{ g.department.name }}</div>
                        <div class="small text-muted">{{ g.college.name }}</div>
                    </td>
                    <td>
                        <div class="d-flex flex-wrap gap-1">
                            {% if g.clean_whatsapp %}
                            <a href="https://wa.me/{{ g.clean_whatsapp }}" target="_blank" class="btn-whatsapp py-1 px-3">
                                <i data-lucide="message-circle" style="width:15px;height:15px;"></i> WhatsApp
                            </a>
                            {% endif %}
                            {% if g.whatsapp_number %}
                            <a href="tel:{{ g.whatsapp_number }}" class="btn-m3-outline py-1 px-2 text-decoration-none" style="min-height:34px;" title="Call {{ g.whatsapp_number }}">
                                <i data-lucide="phone" style="width:15px;height:15px;"></i>
                            </a>
                            {% endif %}
                        </div>
                    </td>
                    <td>
                        {% if g.is_examiner %}
                        <span class="m3-chip chip-success"><i data-lucide="check-circle" style="width:15px;height:15px;"></i> Guide + External Examiner</span>
                        {% else %}
                        <span class="m3-chip chip-tonal">Faculty Guide</span>
                        {% endif %}
                    </td>
                    <td class="text-end">
                        <form method="POST" class="d-inline no-legend">
                            {% csrf_token %}
                            <input type="hidden" name="action" value="toggle_examiner">
                            <input type="hidden" name="profile_id" value="{{ g.id }}">
                            {% if g.is_examiner %}
                            <button type="submit" class="btn-m3-outline text-danger border-danger py-2 px-3" style="min-height:44px;">
                                <i data-lucide="arrow-down-circle"></i> Demote from Examiner
                            </button>
                            {% else %}
                            <button type="submit" class="btn-m3-primary py-2 px-3" style="min-height:44px;">
                                <i data-lucide="arrow-up-circle"></i> Promote to Examiner
                            </button>
                            {% endif %}
                        </form>
                    </td>
                </tr>
                {% empty %}
                <tr>
                    <td colspan="6" class="text-center py-4 text-muted">No Faculty Guides registered matching this filter yet.</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>

<!-- SECTION 2 (PROMINENT): ENROLLED STUDENTS DATASET -->
<div class="m3-card mb-5">
    <div class="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-3">
        <div>
            <h3 class="fw-bold mb-1 d-flex align-items-center gap-2">
                <i data-lucide="graduation-cap" style="color:var(--m3-primary);"></i> 2. Enrolled Students Dataset
            </h3>
            <div class="text-muted">All students registered under {{ user.profile.college.name }} and its departments.</div>
        </div>
        <span class="m3-chip chip-neutral">Total Students: {{ students_qs|length }}</span>
    </div>
    <div class="table-responsive">
        <table class="table align-middle">
            <thead class="text-muted">
                <tr>
                    <th>Student</th>
                    <th>Roll Call & Class</th>
                    <th>Department</th>
                    <th>Selected Guide</th>
                    <th>Contact Actions</th>
                </tr>
            </thead>
            <tbody>
                {% for s in students_qs %}
                <tr>
                    <td>
                        <div class="d-flex align-items-center gap-3">
                            <a href="{% url 'public_profile' s.user.username %}" class="avatar-circle">
                                {% if s.has_avatar %}
                                <img src="{{ s.avatar_url }}" alt="{{ s.user.get_full_name|default:s.user.username }}">
                                {% else %}
                                {{ s.initials }}
                                {% endif %}
                            </a>
                            <div>
                                <a href="{% url 'public_profile' s.user.username %}" class="fw-bold text-dark text-decoration-none">{{ s.user.get_full_name|default:s.user.username }}</a>
                                <div class="small text-muted">
                                    <a href="{% url 'public_profile' s.user.username %}" class="text-muted text-decoration-none">@{{ s.user.username }}</a>
                                    {% if s.user.email %} &bull; <a href="mailto:{{ s.user.email }}" class="text-primary text-decoration-none">{{ s.user.email }}</a>{% endif %}
                                </div>
                            </div>
                        </div>
                    </td>
                    <td>
                        <span class="m3-chip chip-neutral py-1 px-2">{{ s.identifier }}</span>
                        <span class="small text-muted ms-1">{{ s.class_division }}</span>
                    </td>
                    <td>
                        <div class="fw-medium">{{ s.department.name }}</div>
                        <div class="small text-muted">{{ s.college.name }}</div>
                    </td>
                    <td>
                        {% if s.preferred_guide %}
                        <a href="{% url 'public_profile' s.preferred_guide.username %}" class="fw-medium text-dark text-decoration-none">{{ s.preferred_guide.get_full_name|default:s.preferred_guide.username }}</a>
                        {% else %}
                        <span class="text-muted small">Unassigned</span>
                        {% endif %}
                    </td>
                    <td>
                        <div class="d-flex flex-wrap gap-1">
                            {% if s.clean_whatsapp %}
                            <a href="https://wa.me/{{ s.clean_whatsapp }}" target="_blank" class="btn-whatsapp py-1 px-2">
                                <i data-lucide="message-circle" style="width:15px;height:15px;"></i> WhatsApp
                            </a>
                            {% endif %}
                            {% if s.whatsapp_number %}
                            <a href="tel:{{ s.whatsapp_number }}" class="btn-m3-outline py-1 px-2 text-decoration-none" style="min-height:34px;" title="Call {{ s.whatsapp_number }}">
                                <i data-lucide="phone" style="width:15px;height:15px;"></i>
                            </a>
                            {% endif %}
                        </div>
                    </td>
                </tr>
                {% empty %}
                <tr>
                    <td colspan="5" class="text-center py-4 text-muted">No students registered matching this filter yet.</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>

<!-- SECTION 3 (VERY LAST POSITION): DESCENDING HIERARCHY ENGINE -->
<div class="m3-card">
    <h3 class="fw-bold mb-2 d-flex align-items-center gap-2">
        <i data-lucide="git-branch-plus" style="color:var(--m3-primary);"></i> 3. Descending Hierarchy Engine (University &rarr; College &rarr; Department)
    </h3>
    <p class="text-muted mb-4">Add new departments or institutional units under your authorized scope. Updates immediately cascade to Student and Faculty Guide registration dropdowns.</p>

    <div class="row g-4">
        <div class="col-lg-4">
            <div class="m3-card-tonal h-100">
                <h5 class="fw-bold mb-3">Step A: Register University</h5>
                <form method="POST" data-autosave="admin_add_uni">
                    {% csrf_token %}
                    <input type="hidden" name="action" value="add_university">
                    <div class="mb-3">
                        <label class="form-label">University Name</label>
                        <input type="text" name="university_name" class="form-control" placeholder="e.g. Savitribai Phule Pune University" required>
                    </div>
                    <button type="submit" class="btn-m3-primary w-100">
                        <i data-lucide="plus"></i> Add University
                    </button>
                </form>
            </div>
        </div>

        <div class="col-lg-4">
            <div class="m3-card-tonal h-100">
                <h5 class="fw-bold mb-3">Step B: Add College under University</h5>
                <form method="POST" data-autosave="admin_add_col">
                    {% csrf_token %}
                    <input type="hidden" name="action" value="add_college">
                    <div class="mb-3">
                        <label class="form-label">Select Parent University</label>
                        <select name="university_id" class="form-select" required>
                            {% for u in all_universities %}
                            <option value="{{ u.id }}">{{ u.name }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">College / Institute Name</label>
                        <input type="text" name="college_name" class="form-control" placeholder="e.g. MSG Arts, Science & Commerce College" required>
                    </div>
                    <button type="submit" class="btn-m3-primary w-100">
                        <i data-lucide="plus"></i> Add College
                    </button>
                </form>
            </div>
        </div>

        <div class="col-lg-4">
            <div class="m3-card-tonal h-100">
                <h5 class="fw-bold mb-3">Step C: Add Department under College</h5>
                <form method="POST" data-autosave="admin_add_dept">
                    {% csrf_token %}
                    <input type="hidden" name="action" value="add_department">
                    <div class="mb-3">
                        <label class="form-label">Select Parent College</label>
                        <select name="college_id" class="form-select" required>
                            {% for c in all_colleges %}
                            <option value="{{ c.id }}">{{ c.name }} ({{ c.university.name }})</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Department Name</label>
                        <input type="text" name="department_name" class="form-control" placeholder="e.g. Department of Computer Science" required>
                    </div>
                    <button type="submit" class="btn-m3-primary w-100">
                        <i data-lucide="plus"></i> Publish Department
                    </button>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}
"""

# ==============================================================================
# 13. PROFILE SETTINGS & ROLE-SCOPED DIRECTORY (settings_profile.html)
#     Includes Verified Admin ID Proofs inside Admin's Profile Settings
# ==============================================================================
SETTINGS_PROFILE_HTML = """
{% extends 'base.html' %}
{% block content %}
<div class="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
    <div>
        <h1 class="fw-bold mb-1">Profile Settings & Authorized Contact Directory</h1>
        <div class="text-muted">Manage your avatar photo, credentials, clickable contact handles, and browse contacts within your authorized scope</div>
    </div>
    <div class="d-flex gap-2">
        <a href="{% url 'public_profile' user.username %}" class="btn-m3-tonal text-decoration-none">
            <i data-lucide="external-link"></i> View My Public Profile
        </a>
        <a href="{% url 'dashboard_router' %}" class="btn-m3-outline text-decoration-none">
            <i data-lucide="arrow-left"></i> Back to Dashboard
        </a>
    </div>
</div>

<div class="row g-4 mb-5">
    <!-- Left Column: Edit Profile, Avatar, WhatsApp & Social Handles -->
    <div class="col-lg-7">
        <div class="m3-card h-100">
            <div class="d-flex align-items-center gap-4 mb-4 pb-4 border-bottom">
                <a href="{% url 'public_profile' user.username %}" class="avatar-circle" style="width: 92px; height: 92px; font-size: 2rem;">
                    {% if user.profile.has_avatar %}
                    <img src="{{ user.profile.avatar_url }}" alt="{{ user.get_full_name|default:user.username }}" onerror="this.style.display='none';this.parentElement.innerText='{{ user.profile.initials }}';">
                    {% else %}
                    {{ user.profile.initials }}
                    {% endif %}
                </a>
                <div>
                    <h3 class="fw-bold mb-1">{{ user.get_full_name|default:user.username }}</h3>
                    <div class="d-flex flex-wrap gap-2 align-items-center">
                        <span class="m3-chip chip-tonal py-1 px-3">{{ user.profile.get_role_display }}</span>
                        {% if user.profile.is_examiner %}
                        <span class="m3-chip chip-success py-1 px-3">Assigned Examiner</span>
                        {% endif %}
                        <span class="m3-chip chip-neutral py-1 px-3">ID: {{ user.profile.identifier }}</span>
                    </div>
                </div>
            </div>

            <form method="POST" enctype="multipart/form-data" data-autosave="profile_settings_form">
                {% csrf_token %}
                <input type="hidden" name="action" value="update_profile">
                <div class="row g-3 mb-4">
                    <div class="col-md-6">
                        <label class="form-label" for="profFullName">Full Name</label>
                        <input type="text" name="full_name" id="profFullName" class="form-control" value="{{ user.get_full_name }}" placeholder="e.g. John Doe" required>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label" for="profEmail">Email Address</label>
                        <input type="email" name="email" id="profEmail" class="form-control" value="{{ user.email }}" placeholder="e.g. johndoe@example.com" required>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label" for="profId">Roll Call / Faculty / Admin ID</label>
                        <input type="text" name="identifier" id="profId" class="form-control" value="{{ user.profile.identifier }}" required>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label" for="profAvatar">Upload Profile Avatar Photo (JPG, PNG, WEBP)</label>
                        <input type="file" name="avatar" id="profAvatar" class="form-control" accept=".jpg,.jpeg,.png,.webp">
                    </div>
                    {% if user.profile.role == 'STUDENT' %}
                    <div class="col-md-6">
                        <label class="form-label" for="profClass">Class / Division</label>
                        <input type="text" name="class_division" id="profClass" class="form-control" value="{{ user.profile.class_division }}">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label" for="profGuide">Preferred Project Guide</label>
                        <select name="preferred_guide_id" id="profGuide" class="form-select">
                            <option value="">-- Select Guide --</option>
                            {% for g in dept_guides %}
                            <option value="{{ g.id }}" {% if user.profile.preferred_guide_id == g.id %}selected{% endif %}>
                                {{ g.get_full_name|default:g.username }} ({{ g.profile.identifier }})
                            </option>
                            {% endfor %}
                        </select>
                    </div>
                    {% endif %}
                    <div class="col-12">
                        <label class="form-label" for="profBio">Short Bio / Academic Headline</label>
                        <input type="text" name="bio" id="profBio" class="form-control" value="{{ user.profile.bio }}" placeholder="e.g. Final Year Computer Science Researcher | Distributed Cloud Systems">
                    </div>
                </div>

                <h4 class="fw-bold mb-3 d-flex align-items-center gap-2">
                    <i data-lucide="share-2" style="color:var(--m3-primary);"></i> Clickable Contact & Social Links
                </h4>
                <div class="row g-3 mb-4">
                    <div class="col-md-6">
                        <label class="form-label" for="profWa">Phone / WhatsApp Number</label>
                        <input type="text" name="whatsapp_number" id="profWa" class="form-control" value="{{ user.profile.whatsapp_number }}" placeholder="e.g. +91 98765 43210">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label" for="profGh">GitHub Handle or URL</label>
                        <input type="text" name="github_handle" id="profGh" class="form-control" value="{{ user.profile.github_handle }}" placeholder="e.g. johndoe">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label" for="profYt">YouTube Channel Handle or URL</label>
                        <input type="text" name="youtube_handle" id="profYt" class="form-control" value="{{ user.profile.youtube_handle }}" placeholder="e.g. @johndoe">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label" for="profIg">Instagram Handle or URL</label>
                        <input type="text" name="instagram_handle" id="profIg" class="form-control" value="{{ user.profile.instagram_handle }}" placeholder="e.g. @johndoe">
                    </div>
                </div>

                <button type="submit" class="btn-m3-primary w-100">
                    <i data-lucide="save"></i> Save Profile & Avatar
                </button>
            </form>
        </div>
    </div>

    <!-- Right Column: Live Contact Card + Admin ID Proofs (Admin Only) + Password + Delete -->
    <div class="col-lg-5">
        <div class="m3-card mb-4">
            <h4 class="fw-bold mb-3 d-flex align-items-center gap-2">
                <i data-lucide="contact" style="color:var(--m3-primary);"></i> Your Live Public Profile Card
            </h4>
            <div class="m3-card-tonal p-4">
                <div class="d-flex align-items-center gap-3 mb-3">
                    <a href="{% url 'public_profile' user.username %}" class="avatar-circle" style="width:64px;height:64px;font-size:1.4rem;">
                        {% if user.profile.has_avatar %}
                        <img src="{{ user.profile.avatar_url }}" alt="{{ user.get_full_name|default:user.username }}">
                        {% else %}
                        {{ user.profile.initials }}
                        {% endif %}
                    </a>
                    <div>
                        <a href="{% url 'public_profile' user.username %}" class="fw-bold fs-5 text-dark text-decoration-none">{{ user.get_full_name|default:user.username }}</a>
                        <div class="small text-muted">{{ user.profile.get_role_display }} &bull; {{ user.profile.department.name }}</div>
                    </div>
                </div>
                {% if user.profile.bio %}
                <p class="small mb-3">{{ user.profile.bio }}</p>
                {% endif %}
                <div class="d-flex flex-wrap gap-2">
                    {% if user.email %}
                    <a href="mailto:{{ user.email }}" class="btn-m3-outline py-1 px-3 text-decoration-none" style="min-height:38px;">
                        <i data-lucide="mail" style="width:16px;height:16px;"></i> {{ user.email }}
                    </a>
                    {% endif %}
                    {% if user.profile.whatsapp_number %}
                    <a href="tel:{{ user.profile.whatsapp_number }}" class="btn-m3-outline py-1 px-3 text-decoration-none" style="min-height:38px;">
                        <i data-lucide="phone" style="width:16px;height:16px;"></i> Call
                    </a>
                    {% endif %}
                    {% if user.profile.clean_whatsapp %}
                    <a href="https://wa.me/{{ user.profile.clean_whatsapp }}?text=Hi%20{{ user.get_full_name|urlencode }},%20connecting%20via%20ProTrack" target="_blank" class="btn-whatsapp">
                        <i data-lucide="message-circle" style="width:16px;height:16px;"></i> WhatsApp
                    </a>
                    {% endif %}
                    {% if user.profile.github_url %}
                    <a href="{{ user.profile.github_url }}" target="_blank" class="btn-m3-outline py-1 px-3 text-decoration-none" style="min-height:38px;">
                        <i data-lucide="github" style="width:16px;height:16px;"></i> GitHub
                    </a>
                    {% endif %}
                    {% if user.profile.youtube_url %}
                    <a href="{{ user.profile.youtube_url }}" target="_blank" class="btn-m3-outline py-1 px-3 text-decoration-none" style="min-height:38px;">
                        <i data-lucide="youtube" style="width:16px;height:16px;"></i> YouTube
                    </a>
                    {% endif %}
                    {% if user.profile.instagram_url %}
                    <a href="{{ user.profile.instagram_url }}" target="_blank" class="btn-m3-outline py-1 px-3 text-decoration-none" style="min-height:38px;">
                        <i data-lucide="instagram" style="width:16px;height:16px;"></i> Instagram
                    </a>
                    {% endif %}
                </div>
            </div>
        </div>

        {% if user.profile.role == 'ADMIN' %}
        <!-- VERIFIED ADMIN ID PROOFS (MOVED TO ADMIN PROFILE SETTINGS) -->
        <div class="m3-card mb-4" id="admin-id-proofs">
            <h4 class="fw-bold mb-2 d-flex align-items-center gap-2">
                <i data-lucide="shield-check" style="color:var(--m3-primary);"></i> Verified Admin ID Proofs
            </h4>
            <p class="small text-muted mb-3">Official Front & Back identity verification records for {{ user.profile.college.name }} administrators.</p>
            <div class="d-flex flex-column gap-3">
                {% for adm in college_admins %}
                <div class="p-3 border rounded-4 bg-white">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <div class="fw-bold">{{ adm.user.get_full_name|default:adm.user.username }}</div>
                        <span class="m3-chip chip-success py-1 px-2 small">ID: {{ adm.identifier }}</span>
                    </div>
                    <div class="small text-muted mb-2">{{ adm.university.name }} &bull; {{ adm.college.name }}</div>
                    <div class="d-flex gap-2">
                        {% if adm.id_proof_front %}
                        <a href="{{ adm.id_proof_front.url }}" target="_blank" class="btn-m3-outline py-1 px-3 small text-decoration-none" style="min-height:36px;">
                            <i data-lucide="eye" style="width:15px;height:15px;"></i> Front ID
                        </a>
                        {% endif %}
                        {% if adm.id_proof_back %}
                        <a href="{{ adm.id_proof_back.url }}" target="_blank" class="btn-m3-outline py-1 px-3 small text-decoration-none" style="min-height:36px;">
                            <i data-lucide="eye" style="width:15px;height:15px;"></i> Back ID
                        </a>
                        {% endif %}
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        <div class="m3-card mb-4">
            <h4 class="fw-bold mb-3 d-flex align-items-center gap-2">
                <i data-lucide="lock" style="color:var(--m3-primary);"></i> Update Password
            </h4>
            <form method="POST">
                {% csrf_token %}
                <input type="hidden" name="action" value="change_password">
                <div class="mb-3">
                    <label class="form-label" for="newPassInput">New Password</label>
                    <input type="password" name="new_password" id="newPassInput" class="form-control" placeholder="Enter new password (min 6 chars)" minlength="6" required>
                </div>
                <button type="submit" class="btn-m3-tonal w-100">Update Password</button>
            </form>
        </div>

        <div class="m3-card border-danger">
            <h5 class="fw-bold text-danger mb-2 d-flex align-items-center gap-2">
                <i data-lucide="trash-2"></i> Delete Account
            </h5>
            <p class="small text-muted mb-3">Type <strong>DELETE</strong> below to permanently remove your account.</p>
            <form method="POST" class="d-flex gap-2">
                {% csrf_token %}
                <input type="hidden" name="action" value="delete_account">
                <input type="text" name="confirm_delete" class="form-control" placeholder="Type DELETE" required>
                <button type="submit" class="btn btn-danger rounded-pill px-4 fw-bold">Delete</button>
            </form>
        </div>
    </div>
</div>

<!-- ROLE-FILTERED DEPARTMENT CONTACT & WHATSAPP DIRECTORY -->
<div class="m3-card">
    <div class="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
        <div>
            <h3 class="fw-bold mb-1 d-flex align-items-center gap-2">
                <i data-lucide="users" style="color:var(--m3-primary);"></i> Department Contact & WhatsApp Directory
            </h3>
            <div class="text-muted">
                {% if user.profile.role == 'ADMIN' %}
                Showing verified members across <strong>{{ user.profile.college.name }}</strong> (Students, Faculty Guides, Examiners & Admins).
                {% elif user.profile.role == 'GUIDE' %}
                Showing students and faculty colleagues within <strong>{{ user.profile.department.name }}</strong>.
                {% else %}
                Showing your assigned Project Group members, Faculty Guide, and Department Examiner.
                {% endif %}
            </div>
        </div>
        <form method="GET" class="d-flex flex-wrap gap-2 no-legend">
            <select name="role_filter" class="form-select" style="width:auto;" onchange="this.form.submit()">
                <option value="ALL" {% if role_filter == 'ALL' %}selected{% endif %}>All Permitted Contacts</option>
                <option value="GUIDE" {% if role_filter == 'GUIDE' %}selected{% endif %}>Faculty Guides</option>
                <option value="EXAMINER" {% if role_filter == 'EXAMINER' %}selected{% endif %}>Examiners</option>
                <option value="STUDENT" {% if role_filter == 'STUDENT' %}selected{% endif %}>Students</option>
                {% if user.profile.role == 'ADMIN' %}
                <option value="ADMIN" {% if role_filter == 'ADMIN' %}selected{% endif %}>College Admins</option>
                {% endif %}
            </select>
            <input type="text" name="q" class="form-control" style="width:240px;" value="{{ search_q }}" placeholder="Search name or ID...">
            <button type="submit" class="btn-m3-tonal px-4">Search</button>
        </form>
    </div>

    <div class="row g-4">
        {% for p in directory_profiles %}
        <div class="col-xl-4 col-md-6">
            <div class="m3-card-tonal h-100 d-flex flex-column justify-content-between p-4">
                <div>
                    <div class="d-flex align-items-center gap-3 mb-3">
                        <a href="{% url 'public_profile' p.user.username %}" class="avatar-circle" style="width:60px;height:60px;font-size:1.3rem;">
                            {% if p.has_avatar %}
                            <img src="{{ p.avatar_url }}" alt="{{ p.user.get_full_name|default:p.user.username }}" onerror="this.style.display='none';this.parentElement.innerText='{{ p.initials }}';">
                            {% else %}
                            {{ p.initials }}
                            {% endif %}
                        </a>
                        <div>
                            <a href="{% url 'public_profile' p.user.username %}" class="fw-bold fs-5 text-dark text-decoration-none">{{ p.user.get_full_name|default:p.user.username }}</a>
                            <div class="d-flex flex-wrap gap-1 mt-1">
                                <span class="m3-chip chip-tonal py-0 px-2 small">{{ p.get_role_display }}</span>
                                {% if p.is_examiner %}
                                <span class="m3-chip chip-success py-0 px-2 small">Examiner</span>
                                {% endif %}
                                <span class="m3-chip chip-neutral py-0 px-2 small">{{ p.identifier }}</span>
                            </div>
                        </div>
                    </div>
                    {% if p.bio %}
                    <p class="small text-muted mb-2">{{ p.bio }}</p>
                    {% endif %}
                    <div class="small text-muted mb-3">
                        <i data-lucide="building-2" style="width:14px;height:14px;"></i> {{ p.department.name }} &bull; {{ p.college.name }}
                        {% if p.user.email %}
                        <div class="mt-1">
                            <a href="mailto:{{ p.user.email }}" class="text-primary text-decoration-none">
                                <i data-lucide="mail" style="width:14px;height:14px;"></i> {{ p.user.email }}
                            </a>
                        </div>
                        {% endif %}
                    </div>
                </div>

                <div class="d-flex flex-wrap align-items-center gap-2 pt-3 border-top">
                    <a href="{% url 'public_profile' p.user.username %}" class="btn-m3-outline py-1 px-3 text-decoration-none" style="min-height:36px;font-size:0.88rem;">
                        <i data-lucide="user" style="width:15px;height:15px;"></i> Profile
                    </a>
                    {% if p.clean_whatsapp %}
                    <a href="https://wa.me/{{ p.clean_whatsapp }}?text=Hello%20{{ p.user.get_full_name|urlencode }},%20connecting%20from%20ProTrack" target="_blank" class="btn-whatsapp">
                        <i data-lucide="message-circle" style="width:15px;height:15px;"></i> WhatsApp
                    </a>
                    {% endif %}
                    {% if p.whatsapp_number %}
                    <a href="tel:{{ p.whatsapp_number }}" class="btn-m3-outline py-1 px-2 text-decoration-none" style="min-height:36px;" title="Call {{ p.whatsapp_number }}">
                        <i data-lucide="phone" style="width:15px;height:15px;"></i>
                    </a>
                    {% endif %}
                    {% if p.github_url %}
                    <a href="{{ p.github_url }}" target="_blank" class="btn-m3-outline py-1 px-2 text-decoration-none" style="min-height:36px;" title="GitHub">
                        <i data-lucide="github" style="width:15px;height:15px;"></i>
                    </a>
                    {% endif %}
                    {% if p.youtube_url %}
                    <a href="{{ p.youtube_url }}" target="_blank" class="btn-m3-outline py-1 px-2 text-decoration-none" style="min-height:36px;" title="YouTube">
                        <i data-lucide="youtube" style="width:15px;height:15px;"></i>
                    </a>
                    {% endif %}
                    {% if p.instagram_url %}
                    <a href="{{ p.instagram_url }}" target="_blank" class="btn-m3-outline py-1 px-2 text-decoration-none" style="min-height:36px;" title="Instagram">
                        <i data-lucide="instagram" style="width:15px;height:15px;"></i>
                    </a>
                    {% endif %}
                </div>
            </div>
        </div>
        {% empty %}
        <div class="col-12 text-center py-5 text-muted">
            <i data-lucide="contact-2" class="mb-2" style="width:36px;height:36px;"></i>
            <div>No relevant contacts found within your current role scope.</div>
        </div>
        {% endfor %}
    </div>
</div>
{% endblock %}
"""

# ==============================================================================
# 14. PUBLIC PROFILE VIEW TEMPLATE (public_profile.html)
# ==============================================================================
PUBLIC_PROFILE_HTML = """
{% extends 'base.html' %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-xl-9">
        <div class="m3-card">
            <div class="d-flex flex-wrap justify-content-between align-items-start gap-4 pb-4 mb-4 border-bottom">
                <div class="d-flex flex-wrap align-items-center gap-4">
                    <div class="avatar-circle" style="width: 108px; height: 108px; font-size: 2.4rem;">
                        {% if target_profile.has_avatar %}
                        <img src="{{ target_profile.avatar_url }}" alt="{{ target_user.get_full_name|default:target_user.username }}" onerror="this.style.display='none';this.parentElement.innerText='{{ target_profile.initials }}';">
                        {% else %}
                        {{ target_profile.initials }}
                        {% endif %}
                    </div>
                    <div>
                        <div class="d-flex flex-wrap align-items-center gap-2 mb-2">
                            <span class="m3-chip chip-tonal">{{ target_profile.get_role_display }}</span>
                            {% if target_profile.is_examiner %}
                            <span class="m3-chip chip-success"><i data-lucide="award" style="width:15px;height:15px;"></i> External Examiner</span>
                            {% endif %}
                            <span class="m3-chip chip-neutral">ID: {{ target_profile.identifier }}</span>
                        </div>
                        <h2 class="fw-bold mb-1">{{ target_user.get_full_name|default:target_user.username }}</h2>
                        <div class="text-muted">@{{ target_user.username }} &bull; {{ target_profile.department.name }} ({{ target_profile.college.name }})</div>
                        {% if target_profile.bio %}
                        <p class="mt-2 mb-0">{{ target_profile.bio }}</p>
                        {% endif %}
                    </div>
                </div>

                <div class="d-flex gap-2">
                    {% if user.id == target_user.id %}
                    <a href="{% url 'profile_settings' %}" class="btn-m3-primary text-decoration-none">
                        <i data-lucide="edit-3"></i> Edit My Profile
                    </a>
                    {% else %}
                    <a href="{% url 'profile_settings' %}" class="btn-m3-outline text-decoration-none">
                        <i data-lucide="arrow-left"></i> Back to Directory
                    </a>
                    {% endif %}
                </div>
            </div>

            <!-- Clickable Contact & Social Bar -->
            <h5 class="fw-bold mb-3 d-flex align-items-center gap-2">
                <i data-lucide="link" style="color:var(--m3-primary);"></i> Direct Contact & Portfolio Links
            </h5>
            <div class="d-flex flex-wrap gap-3 mb-4">
                {% if target_user.email %}
                <a href="mailto:{{ target_user.email }}" class="btn-m3-tonal text-decoration-none">
                    <i data-lucide="mail"></i> {{ target_user.email }}
                </a>
                {% endif %}
                {% if target_profile.whatsapp_number %}
                <a href="tel:{{ target_profile.whatsapp_number }}" class="btn-m3-outline text-decoration-none">
                    <i data-lucide="phone"></i> Call {{ target_profile.whatsapp_number }}
                </a>
                {% endif %}
                {% if target_profile.clean_whatsapp %}
                <a href="https://wa.me/{{ target_profile.clean_whatsapp }}?text=Hello%20{{ target_user.get_full_name|urlencode }},%20connecting%20from%20ProTrack" target="_blank" class="btn-whatsapp px-4 py-2 fs-6">
                    <i data-lucide="message-circle"></i> Start WhatsApp Chat
                </a>
                {% endif %}
                {% if target_profile.github_url %}
                <a href="{{ target_profile.github_url }}" target="_blank" class="btn-m3-outline text-decoration-none">
                    <i data-lucide="github"></i> GitHub Profile
                </a>
                {% endif %}
                {% if target_profile.youtube_url %}
                <a href="{{ target_profile.youtube_url }}" target="_blank" class="btn-m3-outline text-decoration-none">
                    <i data-lucide="youtube"></i> YouTube Channel
                </a>
                {% endif %}
                {% if target_profile.instagram_url %}
                <a href="{{ target_profile.instagram_url }}" target="_blank" class="btn-m3-outline text-decoration-none">
                    <i data-lucide="instagram"></i> Instagram
                </a>
                {% endif %}
            </div>

            <!-- Academic Context -->
            <div class="m3-card-tonal p-4">
                <h5 class="fw-bold mb-3">Institutional & Academic Affiliation</h5>
                <div class="row g-3">
                    <div class="col-md-4">
                        <div class="small text-muted">University</div>
                        <div class="fw-bold">{{ target_profile.university.name|default:"—" }}</div>
                    </div>
                    <div class="col-md-4">
                        <div class="small text-muted">College / Institute</div>
                        <div class="fw-bold">{{ target_profile.college.name|default:"—" }}</div>
                    </div>
                    <div class="col-md-4">
                        <div class="small text-muted">Department</div>
                        <div class="fw-bold">{{ target_profile.department.name|default:"—" }}</div>
                    </div>
                    {% if student_group %}
                    <div class="col-12 border-top pt-3 mt-3">
                        <div class="small text-muted">Active Student Project Group</div>
                        <div class="fw-bold">{{ student_group.name }} &bull; Proposal: {{ student_group.proposal.title|default:"In Progress" }}</div>
                    </div>
                    {% endif %}
                    {% if guided_groups %}
                    <div class="col-12 border-top pt-3 mt-3">
                        <div class="small text-muted mb-2">Mentored Project Groups ({{ guided_groups.count }})</div>
                        <div class="d-flex flex-wrap gap-2">
                            {% for gg in guided_groups %}
                            <span class="m3-chip chip-tonal">{{ gg.name }}</span>
                            {% endfor %}
                        </div>
                    </div>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
"""

# ==============================================================================
# 15. ISOLATED SUPERADMIN LOGIN & MASTER CONSOLE TEMPLATES
# ==============================================================================
SUPERADMIN_LOGIN_HTML = """
{% extends 'base.html' %}
{% block content %}
<div class="row justify-content-center py-5">
    <div class="col-lg-5">
        <div class="m3-card" style="border-top: 6px solid #5E35B1;">
            <div class="d-flex align-items-center gap-3 mb-4">
                <div class="brand-icon-box"><i data-lucide="terminal"></i></div>
                <div>
                    <h3 class="mb-0 fw-bold">Superadmin Access</h3>
                    <div class="text-muted small">Dedicated Private Governance Authentication</div>
                </div>
            </div>

            <form method="POST">
                {% csrf_token %}
                <div class="mb-4">
                    <label class="form-label" for="saUsername">Authorized Superadmin Username</label>
                    <input type="text" name="username" id="saUsername" class="form-control" required autofocus>
                </div>
                <div class="mb-4">
                    <label class="form-label" for="saPassword">Superadmin Password</label>
                    <input type="password" name="password" id="saPassword" class="form-control" required>
                </div>
                <button type="submit" class="btn-m3-primary w-100">
                    <i data-lucide="shield"></i> Authenticate Superadmin Session
                </button>
            </form>
        </div>
    </div>
</div>
{% endblock %}
"""

SUPERADMIN_DASHBOARD_HTML = """
{% extends 'base.html' %}
{% block content %}
<div class="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
    <div>
        <span class="m3-chip chip-tonal mb-2"><i data-lucide="lock" style="width:15px;height:15px;"></i> Strictly Isolated Root Session</span>
        <h1 class="fw-bold mb-1">Superadmin Global Infrastructure & Data Console</h1>
        <div class="text-muted">Full cross-university oversight. Invisible to all regular administrators, faculty guides, examiners, and students.</div>
    </div>
    <div class="d-flex gap-2">
        <a href="{% url 'export_department_csv' %}" class="btn-m3-primary text-decoration-none">
            <i data-lucide="download"></i> Export Global Master CSV
        </a>
    </div>
</div>

<!-- Global KPIs -->
<div class="row g-4 mb-5">
    <div class="col-md-3 col-6">
        <div class="m3-card p-4">
            <div class="text-muted small">Universities</div>
            <div class="display-5 fw-bold" style="color:var(--m3-primary);">{{ universities.count }}</div>
        </div>
    </div>
    <div class="col-md-3 col-6">
        <div class="m3-card p-4">
            <div class="text-muted small">Colleges</div>
            <div class="display-5 fw-bold" style="color:var(--m3-primary);">{{ colleges.count }}</div>
        </div>
    </div>
    <div class="col-md-3 col-6">
        <div class="m3-card p-4">
            <div class="text-muted small">Departments</div>
            <div class="display-5 fw-bold" style="color:var(--m3-primary);">{{ departments.count }}</div>
        </div>
    </div>
    <div class="col-md-3 col-6">
        <div class="m3-card p-4">
            <div class="text-muted small">Registered Role Users</div>
            <div class="display-5 fw-bold text-success">{{ profiles.count }}</div>
        </div>
    </div>
</div>

<!-- Private Superadmin Profile & Credentials Settings -->
<div class="row g-4 mb-5">
    <div class="col-lg-6">
        <div class="m3-card h-100">
            <h4 class="fw-bold mb-3 d-flex align-items-center gap-2">
                <i data-lucide="user-cog" style="color:var(--m3-primary);"></i> Private Superadmin Profile Settings
            </h4>
            <form method="POST">
                {% csrf_token %}
                <input type="hidden" name="action" value="update_superadmin_profile">
                <div class="row g-3 mb-3">
                    <div class="col-md-6">
                        <label class="form-label">Superadmin Username</label>
                        <input type="text" name="username" class="form-control" value="{{ user.username }}" required>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Superadmin Email</label>
                        <input type="email" name="email" class="form-control" value="{{ user.email }}" required>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">First Name</label>
                        <input type="text" name="first_name" class="form-control" value="{{ user.first_name }}">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Last Name</label>
                        <input type="text" name="last_name" class="form-control" value="{{ user.last_name }}">
                    </div>
                </div>
                <button type="submit" class="btn-m3-primary w-100">Save Private Superadmin Profile</button>
            </form>
        </div>
    </div>

    <div class="col-lg-6">
        <div class="m3-card h-100">
            <h4 class="fw-bold mb-3 d-flex align-items-center gap-2">
                <i data-lucide="key" style="color:var(--m3-primary);"></i> Rotate Superadmin Password
            </h4>
            <p class="text-muted small mb-3">Your Superadmin credentials are isolated from regular user accounts and cannot be viewed or modified by ordinary administrators.</p>
            <form method="POST">
                {% csrf_token %}
                <input type="hidden" name="action" value="update_superadmin_password">
                <div class="mb-4">
                    <label class="form-label">New Superadmin Password</label>
                    <input type="password" name="new_password" class="form-control" minlength="6" placeholder="Minimum 6 characters" required>
                </div>
                <button type="submit" class="btn-m3-tonal w-100">Update Superadmin Password</button>
            </form>
        </div>
    </div>
</div>

<!-- Master Global Users Table -->
<div class="m3-card mb-5">
    <h3 class="fw-bold mb-3">Global User Directory (All Universities, Colleges & Roles)</h3>
    <div class="table-responsive">
        <table class="table align-middle">
            <thead class="text-muted">
                <tr>
                    <th>User</th>
                    <th>Role</th>
                    <th>ID</th>
                    <th>University &rarr; College &rarr; Department</th>
                    <th class="text-end">Action</th>
                </tr>
            </thead>
            <tbody>
                {% for p in profiles %}
                <tr>
                    <td>
                        <div class="d-flex align-items-center gap-3">
                            <a href="{% url 'public_profile' p.user.username %}" class="avatar-circle">
                                {% if p.has_avatar %}<img src="{{ p.avatar_url }}" alt="Avatar">{% else %}{{ p.initials }}{% endif %}
                            </a>
                            <div>
                                <a href="{% url 'public_profile' p.user.username %}" class="fw-bold text-dark text-decoration-none">{{ p.user.get_full_name|default:p.user.username }}</a>
                                <div class="small text-muted">@{{ p.user.username }} &bull; {{ p.user.email }}</div>
                            </div>
                        </div>
                    </td>
                    <td>
                        <span class="m3-chip chip-tonal py-1 px-2">{{ p.get_role_display }}</span>
                        {% if p.is_examiner %}<span class="m3-chip chip-success py-1 px-2">Examiner</span>{% endif %}
                    </td>
                    <td>{{ p.identifier }}</td>
                    <td>{{ p.university.name }} &bull; {{ p.college.name }} &bull; <strong>{{ p.department.name }}</strong></td>
                    <td class="text-end">
                        <form method="POST" class="d-inline no-legend">
                            {% csrf_token %}
                            <input type="hidden" name="action" value="delete_user">
                            <input type="hidden" name="user_id" value="{{ p.user.id }}">
                            <button type="submit" class="btn btn-sm btn-outline-danger rounded-pill px-3">Remove</button>
                        </form>
                    </td>
                </tr>
                {% empty %}
                <tr><td colspan="5" class="text-center py-4 text-muted">No regular users registered yet.</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}
"""

# ==============================================================================
# 16. SEED COMMAND (portal/management/commands/seed_data.py)
# ==============================================================================
SEED_DATA_PY = """
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'ProTrack Cloud v1.05 operates dynamically while preserving existing records.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS(
            "ProTrack Cloud v1.05 is active! Existing database records are preserved."
        ))
"""

# ==============================================================================
# SAFE NON-DESTRUCTIVE BUILDER EXECUTION
# ==============================================================================
def build():
    print("=================================================================")
    print("  Upgrading to ProTrack Cloud v1.05 (Preserving Existing Data)")
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
    os.makedirs('portal/migrations', exist_ok=True)
    if not os.path.exists('portal/migrations/__init__.py'):
        write_file('portal/migrations/__init__.py', '')

    # Templates
    write_file('templates/base.html', BASE_HTML)
    write_file('templates/login.html', LOGIN_HTML)
    write_file('templates/signup.html', SIGNUP_HTML)
    write_file('templates/student_dashboard.html', STUDENT_DASHBOARD_HTML)
    write_file('templates/guide_dashboard.html', GUIDE_DASHBOARD_HTML)
    write_file('templates/examiner_viva.html', EXAMINER_VIVA_HTML)
    write_file('templates/admin_dashboard.html', ADMIN_DASHBOARD_HTML)
    write_file('templates/settings_profile.html', SETTINGS_PROFILE_HTML)
    write_file('templates/public_profile.html', PUBLIC_PROFILE_HTML)
    write_file('templates/superadmin_login.html', SUPERADMIN_LOGIN_HTML)
    write_file('templates/superadmin_dashboard.html', SUPERADMIN_DASHBOARD_HTML)

    print("\nRunning non-destructive Django makemigrations & migrate...")
    subprocess.run([sys.executable, 'manage.py', 'makemigrations', 'portal'], check=True)
    subprocess.run([sys.executable, 'manage.py', 'migrate'], check=True)

    # Clean up any accidental UserProfile attached to Superusers & normalize 5-char join codes
    cleanup_code = (
        "import django, os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'protrack_config.settings'); django.setup(); "
        "from portal.models import UserProfile, ProjectGroup, generate_join_code; "
        "UserProfile.objects.filter(user__is_superuser=True).delete(); "
        "[setattr(g, 'join_code', generate_join_code()) or g.save() for g in ProjectGroup.objects.all() if len(g.join_code) != 5]"
    )
    subprocess.run([sys.executable, '-c', cleanup_code], check=True)

    print("\n=================================================================")
    print("  ProTrack Cloud v1.05 Built Successfully! (Data Preserved)")
    print("=================================================================")

if __name__ == '__main__':
    build()