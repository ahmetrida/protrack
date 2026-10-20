import os
import subprocess
import sys

print("✨ Building ProTrack v3.0 (Masterpiece Edition)...")

folders = [
    "protrack_config",
    "portal",
    "portal/migrations",
    "portal/management",
    "portal/management/commands",
    "templates",
    "media/reports",
]
for folder in folders:
    os.makedirs(folder, exist_ok=True)

files = {}

# --- requirements.txt ---
files["requirements.txt"] = """Django>=5.0,<5.2
scikit-learn>=1.4.0
pandas>=2.2.0
Pillow>=10.2.0
gunicorn>=21.2.0
whitenoise>=6.6.0
"""

# --- manage.py ---
files["manage.py"] = """#!/usr/bin/env python
import os
import sys

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'protrack_config.settings')
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
"""

for init_path in [
    "protrack_config/__init__.py",
    "portal/__init__.py",
    "portal/migrations/__init__.py",
    "portal/management/__init__.py",
    "portal/management/commands/__init__.py",
]:
    files[init_path] = ""

# --- protrack_config/settings.py ---
files["protrack_config/settings.py"] = """import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = 'django-insecure-protrack-v3-masterpiece-2026'
DEBUG = True
ALLOWED_HOSTS = ['*']

CSRF_TRUSTED_ORIGINS = [
    'https://*.app.github.dev',
    'https://*.github.dev',
    'https://*.pythonanywhere.com',
    'https://*.onrender.com',
]

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
    'whitenoise.middleware.WhiteNoiseMiddleware',
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
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
"""

# --- protrack_config/wsgi.py ---
files["protrack_config/wsgi.py"] = """import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'protrack_config.settings')
application = get_wsgi_application()
"""

# --- protrack_config/urls.py ---
files["protrack_config/urls.py"] = """from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('portal.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
"""

# --- portal/models.py ---
files["portal/models.py"] = """from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('STUDENT', 'Student'),
        ('GUIDE', 'Faculty Guide'),
        ('COORDINATOR', 'Project Coordinator'),
        ('EXAMINER', 'External Examiner'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='STUDENT')
    department = models.CharField(max_length=100, default='Department of Computer Science')
    roll_or_emp_id = models.CharField(max_length=30, blank=True, null=True)

    def __str__(self):
        return f"{self.user.first_name or self.user.username} ({self.get_role_display()})"

class PastProjectArchive(models.Model):
    title = models.CharField(max_length=255)
    abstract = models.TextField()
    batch_year = models.CharField(max_length=10, default='2024-25')
    domain = models.CharField(max_length=100, default='Web / AI')

    def __str__(self):
        return f"{self.title} ({self.batch_year})"

class ProjectGroup(models.Model):
    STAGE_CHOICES = (
        ('TOPIC_PENDING', 'Topic Approval Pending'),
        ('IN_PROGRESS', 'Development In Progress'),
        ('READY_FOR_VIVA', 'Submitted & Ready for Viva'),
        ('EVALUATED', 'Viva Evaluated'),
    )
    group_name = models.CharField(max_length=100, unique=True)
    members = models.ManyToManyField(User, related_name='student_groups', blank=True)
    guide = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='guided_groups')
    current_stage = models.CharField(max_length=30, choices=STAGE_CHOICES, default='TOPIC_PENDING')
    github_repo_link = models.URLField(blank=True, null=True)
    final_report_pdf = models.FileField(upload_to='reports/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.group_name

class ProjectProposal(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Changes Requested'),
    )
    group = models.OneToOneField(ProjectGroup, on_delete=models.CASCADE, related_name='proposal')
    proposed_title = models.CharField(max_length=255)
    abstract_text = models.TextField()
    tech_stack = models.CharField(max_length=255)
    similarity_score = models.FloatField(default=0.0)
    closest_match_title = models.CharField(max_length=255, blank=True, null=True)
    closest_match_source = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    reviewer_remarks = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now=True)

class WeeklyLog(models.Model):
    APPROVAL_CHOICES = (
        ('PENDING', 'Pending Review'),
        ('APPROVED', 'Signed Off'),
        ('CHANGES_NEEDED', 'Needs Revision'),
    )
    group = models.ForeignKey(ProjectGroup, on_delete=models.CASCADE, related_name='weekly_logs')
    week_number = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(16)])
    tasks_completed = models.TextField()
    commit_or_doc_link = models.URLField(blank=True, null=True)
    guide_remarks = models.TextField(blank=True, null=True)
    approval_status = models.CharField(max_length=20, choices=APPROVAL_CHOICES, default='PENDING')
    logged_date = models.DateField(auto_now=True)

    class Meta:
        ordering = ['week_number']

class VivaEvaluation(models.Model):
    group = models.OneToOneField(ProjectGroup, on_delete=models.CASCADE, related_name='viva_evaluation')
    examiner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='evaluations_done')
    problem_definition_marks = models.PositiveIntegerField(default=0)
    implementation_marks = models.PositiveIntegerField(default=0)
    presentation_marks = models.PositiveIntegerField(default=0)
    qa_defense_marks = models.PositiveIntegerField(default=0)
    documentation_marks = models.PositiveIntegerField(default=0)
    total_marks = models.PositiveIntegerField(default=0)
    grade = models.CharField(max_length=5, blank=True)
    examiner_comments = models.TextField(blank=True, null=True)
    evaluated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.total_marks = (
            int(self.problem_definition_marks) +
            int(self.implementation_marks) +
            int(self.presentation_marks) +
            int(self.qa_defense_marks) +
            int(self.documentation_marks)
        )
        if self.total_marks >= 85: self.grade = 'O'
        elif self.total_marks >= 75: self.grade = 'A+'
        elif self.total_marks >= 65: self.grade = 'A'
        elif self.total_marks >= 55: self.grade = 'B+'
        elif self.total_marks >= 40: self.grade = 'B'
        else: self.grade = 'F'
        super().save(*args, **kwargs)

class Notification(models.Model):
    LEVEL_CHOICES = (
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('info', 'Info'),
        ('error', 'Error'),
    )
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=255)
    level = models.CharField(max_length=15, choices=LEVEL_CHOICES, default='info')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
"""

# --- portal/admin.py ---
files["portal/admin.py"] = """from django.contrib import admin
from .models import UserProfile, PastProjectArchive, ProjectGroup, ProjectProposal, WeeklyLog, VivaEvaluation, Notification

admin.site.register(UserProfile)
admin.site.register(PastProjectArchive)
admin.site.register(ProjectGroup)
admin.site.register(ProjectProposal)
admin.site.register(WeeklyLog)
admin.site.register(VivaEvaluation)
admin.site.register(Notification)
"""

# --- portal/similarity.py ---
files["portal/similarity.py"] = """import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .models import PastProjectArchive, ProjectProposal

DOMAIN_STOPWORDS = {
    'project', 'system', 'application', 'using', 'based', 'portal', 'web',
    'develop', 'proposed', 'aims', 'manage', 'management', 'user', 'users',
    'allow', 'allows', 'data', 'module', 'modules', 'platform', 'software'
}

def clean_and_normalize(text):
    text = (text or '').lower()
    text = re.sub(r'[^a-z0-9\\s]', ' ', text)
    tokens = [w for w in text.split() if len(w) > 2 and w not in DOMAIN_STOPWORDS]
    return " ".join(tokens)

def calculate_abstract_similarity(new_title, new_abstract, exclude_group_id=None):
    corpus_docs = []
    corpus_titles = []
    corpus_meta = []

    for item in PastProjectArchive.objects.all():
        combined = clean_and_normalize(f"{item.title} {item.title} {item.abstract}")
        corpus_docs.append(combined)
        corpus_titles.append(clean_and_normalize(item.title))
        corpus_meta.append((item.title, f"Archive ({item.batch_year})"))

    proposals = ProjectProposal.objects.all()
    if exclude_group_id:
        proposals = proposals.exclude(group_id=exclude_group_id)

    for prop in proposals:
        combined = clean_and_normalize(f"{prop.proposed_title} {prop.proposed_title} {prop.abstract_text}")
        corpus_docs.append(combined)
        corpus_titles.append(clean_and_normalize(prop.proposed_title))
        corpus_meta.append((prop.proposed_title, f"Active Batch ({prop.group.group_name})"))

    if not corpus_docs:
        return 0.0, "No archive records", "N/A", []

    query_doc = clean_and_normalize(f"{new_title} {new_title} {new_abstract}")
    query_title = clean_and_normalize(new_title)

    if not query_doc.strip():
        return 0.0, "Insufficient text", "N/A", []

    all_docs = corpus_docs + [query_doc]

    word_vec = TfidfVectorizer(stop_words='english', ngram_range=(1, 2), sublinear_tf=True)
    word_mat = word_vec.fit_transform(all_docs)
    word_sims = cosine_similarity(word_mat[-1], word_mat[:-1]).flatten()

    char_vec = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), sublinear_tf=True)
    char_mat = char_vec.fit_transform(all_docs)
    char_sims = cosine_similarity(char_mat[-1], char_mat[:-1]).flatten()

    q_words = set(query_doc.split())
    q_title_words = set(query_title.split())

    final_scores = []
    for idx in range(len(corpus_docs)):
        doc_words = set(corpus_docs[idx].split())
        title_words = set(corpus_titles[idx].split())

        jaccard_doc = len(q_words & doc_words) / max(len(q_words | doc_words), 1)
        jaccard_title = len(q_title_words & title_words) / max(len(q_title_words | title_words), 1)

        raw_score = (0.45 * word_sims[idx]) + (0.30 * char_sims[idx]) + (0.15 * jaccard_title) + (0.10 * jaccard_doc)
        calibrated = min(round(raw_score * 135, 1), 99.4)
        final_scores.append(calibrated)

    best_idx = int(max(range(len(final_scores)), key=lambda i: final_scores[i]))
    best_score = final_scores[best_idx]
    matched_title, matched_source = corpus_meta[best_idx]
    matched_keywords = sorted(list(q_words & set(corpus_docs[best_idx].split())))[:6]

    return best_score, matched_title, matched_source, matched_keywords
"""

# --- portal/views.py ---
files["portal/views.py"] = """import csv
import os
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import (
    UserProfile, PastProjectArchive, ProjectGroup,
    ProjectProposal, WeeklyLog, VivaEvaluation, Notification
)
from .similarity import calculate_abstract_similarity

ALLOWED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg'}

def notify_group_members(group, msg, level='info'):
    for member in group.members.all():
        Notification.objects.create(recipient=member, message=msg, level=level)

def notify_user(user, msg, level='info'):
    if user:
        Notification.objects.create(recipient=user, message=msg, level=level)

def user_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user:
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            return redirect('dashboard')
        messages.error(request, 'Invalid username or password. Please try again.')
    return render(request, 'login.html')

def user_logout(request):
    logout(request)
    return redirect('login')

@login_required
def dashboard(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    role = profile.role
    notifications = request.user.notifications.all()[:8]
    unread_count = request.user.notifications.filter(is_read=False).count()

    base_ctx = {'notifications': notifications, 'unread_count': unread_count}

    if role == 'STUDENT':
        group = request.user.student_groups.first()
        proposal = getattr(group, 'proposal', None) if group else None
        logs = group.weekly_logs.all() if group else []
        viva = getattr(group, 'viva_evaluation', None) if group else None
        next_week = (logs.last().week_number + 1) if logs.exists() else 1
        base_ctx.update({
            'group': group, 'proposal': proposal,
            'logs': logs, 'viva': viva, 'next_week': min(next_week, 16)
        })
        return render(request, 'student_dashboard.html', base_ctx)

    elif role == 'GUIDE':
        groups = ProjectGroup.objects.filter(guide=request.user)
        base_ctx.update({'groups': groups})
        return render(request, 'guide_dashboard.html', base_ctx)

    elif role == 'EXAMINER':
        groups = ProjectGroup.objects.all()
        base_ctx.update({'groups': groups})
        return render(request, 'examiner_viva.html', base_ctx)

    else:  # COORDINATOR
        groups = ProjectGroup.objects.all()
        archives = PastProjectArchive.objects.all()
        stage_counts = {
            'pending': groups.filter(current_stage='TOPIC_PENDING').count(),
            'progress': groups.filter(current_stage='IN_PROGRESS').count(),
            'ready': groups.filter(current_stage='READY_FOR_VIVA').count(),
            'evaluated': groups.filter(current_stage='EVALUATED').count(),
        }
        base_ctx.update({'groups': groups, 'archives': archives, 'stage_counts': stage_counts})
        return render(request, 'coordinator_dashboard.html', base_ctx)

@login_required
def api_check_similarity(request):
    if request.method == 'POST':
        group = request.user.student_groups.first()
        title = request.POST.get('proposed_title', '')
        abstract = request.POST.get('abstract_text', '')
        exclude_id = group.id if group else None

        score, match_title, match_src, keywords = calculate_abstract_similarity(title, abstract, exclude_group_id=exclude_id)
        level = 'warning' if score >= 50 else 'info'
        msg = (
            f"High overlap ({score}%) detected with '{match_title}'."
            if score >= 50 else
            f"Similarity verified at {score}%. Topic is distinct."
        )
        return JsonResponse({
            'ok': True,
            'score': score,
            'match_title': match_title,
            'match_source': match_src,
            'keywords': keywords,
            'level': level,
            'message': msg
        })
    return JsonResponse({'ok': False, 'message': 'Invalid request'}, status=400)

@login_required
def submit_proposal(request):
    if request.method == 'POST':
        group = request.user.student_groups.first()
        proposal_existing = getattr(group, 'proposal', None)

        title = request.POST.get('proposed_title', '').strip() or (proposal_existing.proposed_title if proposal_existing else '')
        abstract = request.POST.get('abstract_text', '').strip() or (proposal_existing.abstract_text if proposal_existing else '')
        stack = request.POST.get('tech_stack', '').strip() or (proposal_existing.tech_stack if proposal_existing else '')

        score, match_title, match_src, keywords = calculate_abstract_similarity(title, abstract, exclude_group_id=group.id)
        proposal, _ = ProjectProposal.objects.update_or_create(
            group=group,
            defaults={
                'proposed_title': title,
                'abstract_text': abstract,
                'tech_stack': stack,
                'similarity_score': score,
                'closest_match_title': match_title,
                'closest_match_source': match_src,
                'status': 'PENDING',
            }
        )
        notify_user(group.guide, f"{group.group_name} updated proposal '{title}' (Similarity: {score}%).", 'info')

        level = 'warning' if score >= 50 else 'success'
        msg = (
            f"Proposal saved, but flagged at {score}% similarity with '{match_title}'."
            if score >= 50 else
            f"Proposal saved & sent to {group.guide.first_name}! Smart Similarity: {score}%."
        )
        return JsonResponse({
            'ok': True,
            'level': level,
            'message': msg,
            'score': score,
            'match_title': match_title,
            'match_source': match_src,
            'keywords': keywords,
            'status_display': proposal.get_status_display()
        })
    return JsonResponse({'ok': False, 'message': 'Invalid request'}, status=400)

@login_required
def add_weekly_log(request):
    if request.method == 'POST':
        group = request.user.student_groups.first()
        week = int(request.POST.get('week_number', 1))
        existing_log = WeeklyLog.objects.filter(group=group, week_number=week).first()

        tasks = request.POST.get('tasks_completed', '').strip() or (existing_log.tasks_completed if existing_log else '')
        link = request.POST.get('commit_or_doc_link', '').strip()
        if not link and existing_log:
            link = existing_log.commit_or_doc_link or ''

        log, created = WeeklyLog.objects.update_or_create(
            group=group, week_number=week,
            defaults={
                'tasks_completed': tasks,
                'commit_or_doc_link': link or None,
                'approval_status': 'PENDING'
            }
        )
        action_word = "logged" if created else "updated"
        notify_user(group.guide, f"{group.group_name} {action_word} Week {week} progress.", 'info')

        return JsonResponse({
            'ok': True,
            'level': 'success',
            'message': f"Week {week} progress {action_word} & synced!",
            'log': {
                'id': log.id,
                'week_number': log.week_number,
                'tasks_completed': log.tasks_completed,
                'commit_or_doc_link': log.commit_or_doc_link or '',
                'guide_remarks': log.guide_remarks or 'Awaiting guide review',
                'approval_status': log.approval_status,
                'status_display': log.get_approval_status_display(),
            }
        })
    return JsonResponse({'ok': False, 'message': 'Invalid request'}, status=400)

@login_required
def upload_final_submission(request):
    if request.method == 'POST':
        group = request.user.student_groups.first()
        repo = request.POST.get('github_repo_link', '').strip()
        if repo:
            group.github_repo_link = repo

        if 'final_report_pdf' in request.FILES:
            uploaded_file = request.FILES['final_report_pdf']
            ext = os.path.splitext(uploaded_file.name)[1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                return JsonResponse({
                    'ok': False,
                    'level': 'error',
                    'message': f'Unsupported file format ({ext}). Please upload PDF, PNG, JPG, or JPEG.'
                }, status=400)
            group.final_report_pdf = uploaded_file

        group.current_stage = 'READY_FOR_VIVA'
        group.save()

        notify_user(group.guide, f"{group.group_name} uploaded final deliverables and is Ready for Viva!", 'success')

        file_url = group.final_report_pdf.url if group.final_report_pdf else ''
        file_name = os.path.basename(group.final_report_pdf.name) if group.final_report_pdf else ''

        return JsonResponse({
            'ok': True,
            'level': 'success',
            'message': 'Deliverables locked in! Group status updated to Ready for Viva.',
            'stage_display': group.get_current_stage_display(),
            'github_repo_link': group.github_repo_link or '',
            'file_url': file_url,
            'file_name': file_name
        })
    return JsonResponse({'ok': False, 'message': 'Invalid request'}, status=400)

@login_required
def review_proposal(request, proposal_id):
    if request.method == 'POST':
        proposal = get_object_or_404(ProjectProposal, id=proposal_id)
        action = request.POST.get('status')
        remarks = request.POST.get('reviewer_remarks', '').strip()
        proposal.status = action
        proposal.reviewer_remarks = remarks
        proposal.save()

        if action == 'APPROVED':
            proposal.group.current_stage = 'IN_PROGRESS'
            proposal.group.save()
            notify_group_members(proposal.group, f"Proposal '{proposal.proposed_title}' was APPROVED by {request.user.first_name}!", 'success')
            level = 'success'
        else:
            notify_group_members(proposal.group, f"Revision requested by {request.user.first_name}: {remarks or 'Please update.'}", 'warning')
            level = 'warning'

        return JsonResponse({
            'ok': True,
            'level': level,
            'message': f"{proposal.group.group_name} proposal marked as {proposal.get_status_display()}.",
            'status': proposal.status,
            'status_display': proposal.get_status_display(),
            'stage_display': proposal.group.get_current_stage_display(),
            'remarks': remarks
        })
    return JsonResponse({'ok': False, 'message': 'Invalid request'}, status=400)

@login_required
def review_log(request, log_id):
    if request.method == 'POST':
        log = get_object_or_404(WeeklyLog, id=log_id)
        status = request.POST.get('approval_status')
        remarks = request.POST.get('guide_remarks', '').strip()
        log.approval_status = status
        log.guide_remarks = remarks
        log.save()

        lvl = 'success' if status == 'APPROVED' else 'warning'
        notify_group_members(
            log.group,
            f"Week {log.week_number} logbook {log.get_approval_status_display()} by {request.user.first_name}.",
            lvl
        )
        return JsonResponse({
            'ok': True,
            'level': lvl,
            'message': f"Week {log.week_number} status updated for {log.group.group_name}.",
            'status_display': log.get_approval_status_display(),
            'approval_status': log.approval_status
        })
    return JsonResponse({'ok': False, 'message': 'Invalid request'}, status=400)

@login_required
def submit_viva_marks(request, group_id):
    if request.method == 'POST':
        group = get_object_or_404(ProjectGroup, id=group_id)
        viva, _ = VivaEvaluation.objects.update_or_create(
            group=group,
            defaults={
                'examiner': request.user,
                'problem_definition_marks': int(request.POST.get('m1', 0)),
                'implementation_marks': int(request.POST.get('m2', 0)),
                'presentation_marks': int(request.POST.get('m3', 0)),
                'qa_defense_marks': int(request.POST.get('m4', 0)),
                'documentation_marks': int(request.POST.get('m5', 0)),
                'examiner_comments': request.POST.get('examiner_comments', '').strip(),
            }
        )
        group.current_stage = 'EVALUATED'
        group.save()

        notify_group_members(
            group,
            f"Viva Evaluated by {request.user.first_name}! Score: {viva.total_marks}/100 (Grade: {viva.grade}).",
            'success'
        )
        return JsonResponse({
            'ok': True,
            'level': 'success',
            'message': f"Viva grade locked for {group.group_name}: {viva.total_marks}/100 (Grade {viva.grade}).",
            'total_marks': viva.total_marks,
            'grade': viva.grade
        })
    return JsonResponse({'ok': False, 'message': 'Invalid request'}, status=400)

@login_required
def api_mark_notifications_read(request):
    if request.method == 'POST':
        request.user.notifications.filter(is_read=False).update(is_read=True)
        return JsonResponse({'ok': True, 'level': 'info', 'message': 'Notifications marked as read.'})
    return JsonResponse({'ok': False}, status=400)

@login_required
def export_marksheet_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="ProTrack_Official_Marksheet_2026.csv"'
    writer = csv.writer(response)
    writer.writerow(['Group Name', 'Students', 'Project Title', 'Smart Similarity %', 'Guide', 'Stage', 'Total Marks (100)', 'Grade'])

    for g in ProjectGroup.objects.all():
        members_str = ", ".join([m.first_name or m.username for m in g.members.all()])
        title = g.proposal.proposed_title if hasattr(g, 'proposal') else 'Not Submitted'
        sim = f"{g.proposal.similarity_score}%" if hasattr(g, 'proposal') else 'N/A'
        guide = g.guide.first_name if g.guide else 'Unassigned'
        marks = g.viva_evaluation.total_marks if hasattr(g, 'viva_evaluation') else 'Pending'
        grade = g.viva_evaluation.grade if hasattr(g, 'viva_evaluation') else 'Pending'
        writer.writerow([g.group_name, members_str, title, sim, guide, g.get_current_stage_display(), marks, grade])
    return response
"""

# --- portal/urls.py ---
files["portal/urls.py"] = """from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('api/check-similarity/', views.api_check_similarity, name='api_check_similarity'),
    path('api/notifications/read/', views.api_mark_notifications_read, name='api_mark_notifications_read'),
    path('submit-proposal/', views.submit_proposal, name='submit_proposal'),
    path('add-log/', views.add_weekly_log, name='add_weekly_log'),
    path('upload-final/', views.upload_final_submission, name='upload_final_submission'),
    path('review-proposal/<int:proposal_id>/', views.review_proposal, name='review_proposal'),
    path('review-log/<int:log_id>/', views.review_log, name='review_log'),
    path('submit-viva/<int:group_id>/', views.submit_viva_marks, name='submit_viva_marks'),
    path('export-csv/', views.export_marksheet_csv, name='export_marksheet_csv'),
]
"""

# --- portal/management/commands/seed_data.py ---
files["portal/management/commands/seed_data.py"] = """from django.core.management.base import BaseCommand
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
"""

# --- templates/base.html (8pt Grid + Royal Violet Palette + Non-Breaking Chips + Stateful JS Engine) ---
files["templates/base.html"] = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ProTrack — Academic Project & Viva Lifecycle Platform</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            /* Primary Brand Family */
            --p-primary: #604A8B;
            --p-secondary: #8066A6;
            --p-dark: #503A76;
            --p-muted: #A88EC5;
            --p-tint: #DCCFEB;
            --p-wash: #E9E1F7;

            /* Semantic Alert Palette */
            --s-error: #B03A3A;
            --s-error-bg: rgba(176, 58, 58, 0.12);
            --s-success: #2F7D57;
            --s-success-bg: rgba(47, 125, 87, 0.12);
            --s-info: #3B6FA3;
            --s-info-bg: rgba(59, 111, 163, 0.12);
            --s-warning: #9A6514;
            --s-warning-bg: rgba(154, 101, 20, 0.14);

            /* Neutrals & Surfaces */
            --surface-bg: #F6F4FA;
            --surface-card: #FFFFFF;
            --text-main: #1E192B;
            --text-secondary: #5E5473;
            --border-subtle: rgba(96, 74, 139, 0.14);

            /* Strict 8pt Spacing Scale */
            --sp-1: 8px;
            --sp-2: 16px;
            --sp-3: 24px;
            --sp-4: 32px;
            --sp-5: 40px;
            --Radius-card: 24px;
            --Radius-input: 16px;
            --Radius-pill: 999px;
        }

        body {
            background-color: var(--surface-bg);
            background-image: radial-gradient(at 0% 0%, var(--p-wash) 0px, transparent 55%);
            color: var(--text-main);
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Inter", sans-serif;
            font-size: 16px;
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
        }

        /* Frosted Navigation on 8pt Grid */
        .protrack-nav {
            background: rgba(255, 255, 255, 0.85);
            backdrop-filter: saturate(180%) blur(20px);
            -webkit-backdrop-filter: saturate(180%) blur(20px);
            border-bottom: 1px solid var(--border-subtle);
            padding: var(--sp-2) 0;
            position: sticky;
            top: 0;
            z-index: 1030;
        }

        .brand-logo {
            font-weight: 700;
            font-size: 1.35rem;
            letter-spacing: -0.025em;
            color: var(--p-dark);
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: var(--sp-1);
            white-space: nowrap;
        }

        .brand-icon-box {
            width: 40px;
            height: 40px;
            border-radius: 12px;
            background: linear-gradient(135deg, var(--p-primary), var(--p-dark));
            color: #FFFFFF;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 12px rgba(96, 74, 139, 0.25);
        }

        /* 8pt Grid Bento Cards */
        .bento-card {
            background: var(--surface-card);
            border-radius: var(--Radius-card);
            border: 1px solid var(--border-subtle);
            box-shadow: 0 8px 24px rgba(80, 58, 118, 0.05);
            padding: var(--sp-3);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }

        .bento-card:hover {
            box-shadow: 0 12px 32px rgba(80, 58, 118, 0.09);
        }

        /* Form Controls on 8pt Scale */
        .form-label {
            font-size: 0.88rem;
            font-weight: 600;
            color: var(--text-secondary);
            margin-bottom: var(--sp-1);
        }

        .form-control, .form-select {
            background-color: var(--p-wash);
            border: 1.5px solid transparent;
            border-radius: var(--Radius-input);
            padding: 12px 16px;
            font-size: 0.98rem;
            color: var(--text-main);
            transition: all 0.2s ease;
        }

        .form-control:focus, .form-select:focus {
            background-color: #FFFFFF;
            border-color: var(--p-primary);
            box-shadow: 0 0 0 4px rgba(96, 74, 139, 0.16);
            color: var(--text-main);
        }

        /* Non-Breaking Buttons & Interactive States */
        .btn-pro {
            background-color: var(--p-primary);
            color: #FFFFFF;
            border-radius: var(--Radius-pill);
            padding: 12px 24px;
            font-weight: 600;
            font-size: 0.95rem;
            border: 1px solid transparent;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            white-space: nowrap !important;
            flex-shrink: 0;
            transition: all 0.2s cubic-bezier(0.22, 1, 0.36, 1);
            cursor: pointer;
        }

        .btn-pro:hover:not(:disabled) {
            background-color: var(--p-dark);
            color: #FFFFFF;
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(80, 58, 118, 0.28);
        }

        .btn-pro:active:not(:disabled) {
            transform: translateY(0);
        }

        .btn-pro-secondary {
            background-color: var(--p-tint);
            color: var(--p-dark);
            border-radius: var(--Radius-pill);
            padding: 12px 24px;
            font-weight: 600;
            font-size: 0.95rem;
            border: 1px solid rgba(96, 74, 139, 0.15);
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            white-space: nowrap !important;
            flex-shrink: 0;
            transition: all 0.2s ease;
            cursor: pointer;
        }

        .btn-pro-secondary:hover:not(:disabled) {
            background-color: var(--p-muted);
            color: #FFFFFF;
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(96, 74, 139, 0.2);
        }

        /* Completed / Locked Button State (Prevents Duplicate Actions) */
        .btn-pro.btn-locked,
        .btn-pro-secondary.btn-locked,
        button:disabled.btn-locked {
            background-color: var(--s-success-bg) !important;
            color: var(--s-success) !important;
            border: 1.5px solid rgba(47, 125, 87, 0.35) !important;
            box-shadow: none !important;
            transform: none !important;
            cursor: not-allowed !important;
            opacity: 1 !important;
        }

        /* Non-Breaking Chips & Status Pills */
        .pro-chip {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 16px;
            border-radius: var(--Radius-pill);
            font-size: 0.85rem;
            font-weight: 600;
            white-space: nowrap !important;
            flex-shrink: 0;
            line-height: 1.2;
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }

        .pro-chip:hover {
            transform: translateY(-1px);
        }

        .chip-primary { background: var(--p-wash); color: var(--p-dark); border: 1px solid var(--p-tint); }
        .chip-member { background: var(--p-tint); color: var(--p-dark); }
        .chip-success { background: var(--s-success-bg); color: var(--s-success); }
        .chip-warning { background: var(--s-warning-bg); color: var(--s-warning); }
        .chip-error { background: var(--s-error-bg); color: var(--s-error); }
        .chip-info { background: var(--s-info-bg); color: var(--s-info); }

        /* Floating Toast Engine with Reverse Progress Bar */
        #toast-stack {
            position: fixed;
            top: 24px;
            right: 24px;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            gap: 12px;
            width: 380px;
            max-width: calc(100vw - 32px);
            pointer-events: none;
        }

        .pro-toast {
            pointer-events: auto;
            background: rgba(255, 255, 255, 0.97);
            backdrop-filter: blur(20px);
            border-radius: 16px;
            box-shadow: 0 16px 40px rgba(80, 58, 118, 0.18);
            border: 1px solid var(--border-subtle);
            overflow: hidden;
            transform: translateX(120%);
            opacity: 0;
            transition: transform 0.35s cubic-bezier(0.22, 1, 0.36, 1), opacity 0.25s ease;
        }

        .pro-toast.show {
            transform: translateX(0);
            opacity: 1;
        }

        .pro-toast-body {
            padding: 16px;
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 0.94rem;
            font-weight: 500;
            color: var(--text-main);
        }

        .toast-reverse-bar {
            height: 4px;
            width: 100%;
            animation: shrinkReverse 4.2s linear forwards;
        }

        .bar-success { background: var(--s-success); }
        .bar-warning { background: var(--s-warning); }
        .bar-error, .bar-danger { background: var(--s-error); }
        .bar-info { background: var(--s-info); }

        @keyframes shrinkReverse {
            0% { width: 100%; }
            100% { width: 0%; }
        }

        /* Clean Tables */
        .table-pro th {
            color: var(--text-secondary);
            font-weight: 600;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            border-bottom: 1px solid var(--border-subtle);
            padding: 12px 16px;
            white-space: nowrap;
        }

        .table-pro td {
            padding: 16px;
            border-bottom: 1px solid var(--border-subtle);
            vertical-align: middle;
        }
    </style>
</head>
<body class="d-flex flex-column min-vh-100">

    <!-- Floating Animated Reverse-Progress Toast Stack -->
    <div id="toast-stack"></div>

    <!-- Sticky Header -->
    <nav class="protrack-nav">
        <div class="container d-flex justify-content-between align-items-center gap-3">
            <a class="brand-logo" href="{% url 'dashboard' %}">
                <span class="brand-icon-box"><i class="bi bi-layers-half"></i></span>
                <span>ProTrack</span>
            </a>

            {% if user.is_authenticated %}
            <div class="d-flex align-items-center gap-2 gap-md-3 flex-nowrap">
                <!-- Notification Bell -->
                <div class="dropdown">
                    <button class="btn-pro-secondary py-2 px-3 position-relative" data-bs-toggle="dropdown" onclick="markNotificationsRead()">
                        <i class="bi bi-bell-fill"></i>
                        {% if unread_count > 0 %}
                        <span id="notif-badge" class="position-absolute top-0 start-100 translate-middle badge rounded-pill" style="background: var(--s-error);">
                            {{ unread_count }}
                        </span>
                        {% endif %}
                    </button>
                    <div class="dropdown-menu dropdown-menu-end p-3 shadow-lg border-0" style="width: 350px; border-radius: 20px;">
                        <div class="d-flex justify-content-between align-items-center mb-2 pb-2 border-bottom">
                            <span class="fw-bold small text-uppercase" style="color: var(--p-primary);">Activity Center</span>
                            <span class="pro-chip chip-info py-1 px-2" style="font-size: 0.75rem;">Real-Time</span>
                        </div>
                        <div id="notif-list">
                            {% for n in notifications %}
                            <div class="py-2 border-bottom small d-flex align-items-start gap-2">
                                <i class="bi bi-circle-fill mt-1" style="font-size: 7px; color: {% if n.level == 'success' %}var(--s-success){% elif n.level == 'warning' %}var(--s-warning){% elif n.level == 'error' %}var(--s-error){% else %}var(--s-info){% endif %};"></i>
                                <span>{{ n.message }}</span>
                            </div>
                            {% empty %}
                            <div class="text-muted small py-3 text-center">No new notifications</div>
                            {% endfor %}
                        </div>
                    </div>
                </div>

                <span class="pro-chip chip-primary d-none d-sm-inline-flex">
                    <i class="bi bi-person-badge"></i> {{ user.profile.get_role_display }}
                </span>
                <span class="fw-semibold d-none d-lg-inline text-nowrap">{{ user.first_name|default:user.username }}</span>
                <a href="{% url 'logout' %}" class="btn-pro-secondary py-2 px-3 text-decoration-none">
                    <i class="bi bi-box-arrow-right"></i> <span>Sign Out</span>
                </a>
            </div>
            {% endif %}
        </div>
    </nav>

    <!-- Main Container on 8pt Grid -->
    <main class="container my-4 flex-grow-1">
        {% block content %}{% endblock %}
    </main>

    <!-- Updated Official Footer -->
    <footer class="py-4 mt-auto border-top" style="background: rgba(255, 255, 255, 0.75); border-color: var(--border-subtle) !important;">
        <div class="container d-flex flex-wrap justify-content-between align-items-center gap-2 small" style="color: var(--text-secondary);">
            <span><strong>ProTrack</strong> — Academic Project & Viva Lifecycle Platform.</span>
            <span>ProTrack © 2026. All rights reserved.</span>
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        function getCSRFToken() {
            const el = document.querySelector('[name=csrfmiddlewaretoken]');
            return el ? el.value : '';
        }

        // Reverse-Progress Toast Notification Engine
        function showToast(message, level = 'success') {
            const stack = document.getElementById('toast-stack');
            const toast = document.createElement('div');
            toast.className = 'pro-toast';

            const iconMap = {
                'success': '<i class="bi bi-check-circle-fill fs-5" style="color: var(--s-success);"></i>',
                'warning': '<i class="bi bi-exclamation-triangle-fill fs-5" style="color: var(--s-warning);"></i>',
                'error': '<i class="bi bi-x-circle-fill fs-5" style="color: var(--s-error);"></i>',
                'danger': '<i class="bi bi-x-circle-fill fs-5" style="color: var(--s-error);"></i>',
                'info': '<i class="bi bi-info-circle-fill fs-5" style="color: var(--s-info);"></i>'
            };

            toast.innerHTML = `
                <div class="pro-toast-body">
                    ${iconMap[level] || iconMap.info}
                    <div class="flex-grow-1">${message}</div>
                    <button type="button" class="btn-close btn-sm" onclick="this.closest('.pro-toast').remove()"></button>
                </div>
                <div class="toast-reverse-bar bar-${level}"></div>
            `;

            stack.appendChild(toast);
            requestAnimationFrame(() => toast.classList.add('show'));

            setTimeout(() => {
                toast.classList.remove('show');
                setTimeout(() => toast.remove(), 350);
            }, 4200);
        }

        // Stateful Button Controller (Prevents Duplicate Submissions & Re-Enables on Edit)
        function setButtonLoading(btn, loadingText = 'Processing...') {
            if (!btn) return;
            if (!btn.dataset.defaultHtml) {
                btn.dataset.defaultHtml = btn.innerHTML;
            }
            btn.disabled = true;
            btn.innerHTML = `<span class="spinner-border spinner-border-sm"></span> <span>${loadingText}</span>`;
        }

        function lockActionButton(btn, completedLabel = 'Saved ✓') {
            if (!btn) return;
            if (!btn.dataset.defaultHtml) {
                btn.dataset.defaultHtml = btn.innerHTML;
            }
            btn.disabled = true;
            btn.classList.add('btn-locked');
            btn.innerHTML = `<i class="bi bi-check2-circle"></i> <span>${completedLabel}</span>`;
        }

        function unlockActionButton(btn) {
            if (!btn || !btn.classList.contains('btn-locked')) return;
            btn.disabled = false;
            btn.classList.remove('btn-locked');
            if (btn.dataset.defaultHtml) {
                btn.innerHTML = btn.dataset.defaultHtml;
            }
        }

        // Automatically watch all forms so locked buttons wake up only when inputs change
        document.addEventListener('DOMContentLoaded', () => {
            document.querySelectorAll('form[data-watch-dirty="true"]').forEach(form => {
                const unlockAllInForm = () => {
                    form.querySelectorAll('.btn-locked').forEach(btn => unlockActionButton(btn));
                };
                form.addEventListener('input', unlockAllInForm);
                form.addEventListener('change', unlockAllInForm);
            });
        });

        async function markNotificationsRead() {
            const badge = document.getElementById('notif-badge');
            if (!badge) return;
            badge.remove();
            await fetch("{% url 'api_mark_notifications_read' %}", {
                method: 'POST',
                headers: { 'X-CSRFToken': getCSRFToken() }
            });
        }

        {% if messages %}
            {% for m in messages %}
                showToast("{{ m|escapejs }}", "{{ m.tags|default:'info' }}");
            {% endfor %}
        {% endif %}
    </script>
</body>
</html>
"""

# --- templates/login.html ---
files["templates/login.html"] = """{% extends 'base.html' %}
{% block content %}
<div class="row justify-content-center align-items-center my-4">
    <div class="col-lg-5 col-md-7">
        <div class="bento-card p-4 p-md-5">
            <div class="text-center mb-4">
                <div class="brand-icon-box mx-auto mb-3" style="width: 56px; height: 56px; border-radius: 16px;">
                    <i class="bi bi-layers-half fs-3"></i>
                </div>
                <h2 class="fw-bold mb-1">Sign in to ProTrack</h2>
                <p class="small mb-0" style="color: var(--text-secondary);">Academic Project & Viva Lifecycle Platform</p>
            </div>

            <form method="POST" id="loginForm" onsubmit="handleLoginSubmit(event)">
                {% csrf_token %}
                <div class="mb-3">
                    <label class="form-label">Username</label>
                    <input type="text" name="username" id="id_username" class="form-control" placeholder="Enter your username" required>
                </div>

                <div class="mb-4">
                    <label class="form-label">Password</label>
                    <div class="position-relative">
                        <input type="password" name="password" id="id_password" class="form-control pe-5" placeholder="Enter your password" required>
                        <button type="button" onclick="togglePassword()" class="btn border-0 position-absolute top-50 end-0 translate-middle-y me-2" style="color: var(--p-primary);" title="Show or Hide Password">
                            <i id="eye_icon" class="bi bi-eye-slash fs-5"></i>
                        </button>
                    </div>
                </div>

                <button type="submit" id="loginBtn" class="btn-pro w-100 py-3">
                    <span>Sign In to Portal</span> <i class="bi bi-arrow-right"></i>
                </button>
            </form>
        </div>

        <!-- 1-Click Role Switcher with Real Faculty & Student Names -->
        <div class="bento-card mt-3 p-4">
            <div class="d-flex align-items-center justify-content-between mb-3">
                <span class="small fw-bold text-uppercase" style="color: var(--text-secondary);">1-Click Role Demo</span>
                <span class="pro-chip chip-primary">Instant Access</span>
            </div>
            <div class="row g-2">
                <div class="col-6">
                    <button class="btn-pro-secondary w-100 py-2" onclick="instantLogin(this, 'student1','Student@123')">
                        <i class="bi bi-person-workspace"></i> <span>Student</span>
                    </button>
                </div>
                <div class="col-6">
                    <button class="btn-pro-secondary w-100 py-2" onclick="instantLogin(this, 'guide1','Guide@123')">
                        <i class="bi bi-person-check"></i> <span>Prof. Saurabh</span>
                    </button>
                </div>
                <div class="col-6">
                    <button class="btn-pro-secondary w-100 py-2" onclick="instantLogin(this, 'coordinator1','Admin@123')">
                        <i class="bi bi-pie-chart"></i> <span>Prof. Prajakta</span>
                    </button>
                </div>
                <div class="col-6">
                    <button class="btn-pro-secondary w-100 py-2" onclick="instantLogin(this, 'examiner1','Viva@123')">
                        <i class="bi bi-award"></i> <span>Examiner</span>
                    </button>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
function togglePassword() {
    const input = document.getElementById('id_password');
    const icon = document.getElementById('eye_icon');
    if (input.type === 'password') {
        input.type = 'text';
        icon.className = 'bi bi-eye fs-5';
    } else {
        input.type = 'password';
        icon.className = 'bi bi-eye-slash fs-5';
    }
}

function handleLoginSubmit(e) {
    const btn = document.getElementById('loginBtn');
    setButtonLoading(btn, 'Authenticating...');
}

function instantLogin(clickedBtn, u, p) {
    document.getElementById('id_username').value = u;
    document.getElementById('id_password').value = p;
    setButtonLoading(clickedBtn, 'Signing in...');
    setButtonLoading(document.getElementById('loginBtn'), 'Authenticating...');
    showToast(`Signing in as ${u}...`, 'info');
    setTimeout(() => document.getElementById('loginForm').submit(), 300);
}
</script>
{% endblock %}
"""

# --- templates/student_dashboard.html ---
files["templates/student_dashboard.html"] = """{% extends 'base.html' %}
{% block content %}
<!-- Top Group Summary Bento Card -->
<div class="bento-card mb-4">
    <div class="d-flex flex-wrap justify-content-between align-items-start gap-3">
        <div>
            <span class="small fw-bold text-uppercase" style="color: var(--p-primary);">Student Project Workspace</span>
            <h2 class="fw-bold mb-2">{{ group.group_name }}</h2>
            <div class="d-flex flex-wrap align-items-center gap-2 mb-3">
                <span class="small fw-semibold me-1" style="color: var(--text-secondary);">Team Members:</span>
                {% for m in group.members.all %}
                <span class="pro-chip chip-member"><i class="bi bi-person-fill"></i> {{ m.first_name|default:m.username }}</span>
                {% endfor %}
            </div>
            <div class="small" style="color: var(--text-secondary);">
                Assigned Faculty Guide: <strong class="text-dark">{{ group.guide.first_name|default:"Unassigned" }}</strong>
            </div>
        </div>
        <div class="d-flex flex-wrap align-items-center gap-2">
            {% if viva %}
            <span class="pro-chip chip-success fs-6 px-3 py-2">
                <i class="bi bi-award-fill"></i> Score: {{ viva.total_marks }}/100 (Grade {{ viva.grade }})
            </span>
            {% endif %}
            <span id="stage-pill" class="pro-chip chip-primary fs-6 px-3 py-2">
                <i class="bi bi-disc"></i> <span id="stage-text">{{ group.get_current_stage_display }}</span>
            </span>
        </div>
    </div>
</div>

<!-- 12-Column 8pt Bento Grid -->
<div class="row g-4">
    <!-- Left Column: Proposal & Smart Similarity (7 Columns) -->
    <div class="col-lg-7">
        <div class="bento-card h-100">
            <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
                <h4 class="fw-bold mb-0">Project Proposal & Smart Similarity</h4>
                <span id="proposal-status-pill" class="pro-chip {% if proposal.status == 'APPROVED' %}chip-success{% elif proposal.status == 'REJECTED' %}chip-error{% else %}chip-warning{% endif %}">
                    {{ proposal.get_status_display|default:"Draft" }}
                </span>
            </div>
            <p class="small mb-3" style="color: var(--text-secondary);">
                Update any field below. Action buttons automatically lock once completed and unlock as soon as you edit a field.
            </p>

            <!-- Smart Similarity Meter -->
            <div id="sim-box" class="p-3 mb-4 rounded-4 {% if proposal.similarity_score >= 50 %}chip-error{% else %}chip-success{% endif %}" style="border: 1px solid currentColor;">
                <div class="d-flex justify-content-between align-items-center">
                    <span class="fw-bold"><i class="bi bi-cpu"></i> Smart Similarity Index</span>
                    <span id="sim-score" class="fs-4 fw-bold">{{ proposal.similarity_score|default:"0.0" }}%</span>
                </div>
                <div class="progress my-2" style="height: 8px; border-radius: 99px; background: rgba(0,0,0,0.08);">
                    <div id="sim-bar" class="progress-bar" style="width: {{ proposal.similarity_score|default:0 }}%; background-color: {% if proposal.similarity_score >= 50 %}var(--s-error){% else %}var(--s-success){% endif %};"></div>
                </div>
                <div id="sim-match" class="small">
                    Closest Match: <strong>{{ proposal.closest_match_title|default:"None" }}</strong> ({{ proposal.closest_match_source|default:"Archive" }})
                </div>
                {% if proposal.reviewer_remarks %}
                <div class="small mt-2 pt-2 border-top border-dark border-opacity-10">
                    <strong>Guide Remarks:</strong> "{{ proposal.reviewer_remarks }}"
                </div>
                {% endif %}
            </div>

            <form id="proposalForm" data-watch-dirty="true" onsubmit="saveProposalRealtime(event)">
                {% csrf_token %}
                <div class="mb-3">
                    <label class="form-label">Proposed Project Title</label>
                    <input type="text" name="proposed_title" id="prop_title" class="form-control" value="{{ proposal.proposed_title }}" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">Technologies & Frameworks</label>
                    <input type="text" name="tech_stack" id="prop_stack" class="form-control" value="{{ proposal.tech_stack }}" placeholder="Python, Django, Scikit-Learn" required>
                </div>
                <div class="mb-4">
                    <label class="form-label">Project Abstract</label>
                    <textarea name="abstract_text" id="prop_abstract" rows="4" class="form-control" required>{{ proposal.abstract_text }}</textarea>
                </div>
                <div class="d-flex flex-wrap gap-2">
                    <button type="button" id="btnCheckSim" onclick="checkSimilarityRealtime()" class="btn-pro-secondary flex-grow-1">
                        <i class="bi bi-shield-check"></i> <span>Check Similarity</span>
                    </button>
                    <button type="submit" id="btnSaveProposal" class="btn-pro flex-grow-1 btn-locked" disabled
                        data-default-html='<i class="bi bi-cloud-check"></i> <span>Save Proposal Changes</span>'>
                        <i class="bi bi-check2-circle"></i> <span>Proposal Up to Date ✓</span>
                    </button>
                </div>
            </form>
        </div>
    </div>

    <!-- Right Column: Weekly Progress + Multi-Format Deliverable Upload (5 Columns) -->
    <div class="col-lg-5 d-flex flex-column gap-4">
        <!-- Weekly Progress Logger -->
        <div class="bento-card">
            <div class="d-flex justify-content-between align-items-center gap-2 mb-2">
                <h4 class="fw-bold mb-0" id="log-form-heading">Weekly Progress</h4>
                <span class="pro-chip chip-primary" id="log-mode-badge">Week {{ next_week }}</span>
            </div>
            <p class="small mb-3" style="color: var(--text-secondary);">
                Log a new milestone or click <strong>Edit</strong> on any week below to patch existing progress.
            </p>

            <form id="logForm" data-watch-dirty="true" onsubmit="saveLogRealtime(event)">
                {% csrf_token %}
                <div class="row g-2 mb-3">
                    <div class="col-4">
                        <label class="form-label">Week #</label>
                        <input type="number" name="week_number" id="log_week" class="form-control" value="{{ next_week }}" min="1" max="16" required>
                    </div>
                    <div class="col-8">
                        <label class="form-label">GitHub Commit Link</label>
                        <input type="url" name="commit_or_doc_link" id="log_link" class="form-control" value="{{ group.github_repo_link|default:'https://github.com/ahmetrida/protrack' }}">
                    </div>
                </div>
                <div class="mb-3">
                    <label class="form-label">Completed Tasks / Updates</label>
                    <textarea name="tasks_completed" id="log_tasks" rows="2" class="form-control" placeholder="Describe what your team built or updated..." required></textarea>
                </div>
                <button type="submit" id="btnSaveLog" class="btn-pro w-100">
                    <i class="bi bi-journal-plus"></i> <span>Submit Weekly Progress</span>
                </button>
            </form>
        </div>

        <!-- Final Repository & Multi-Format File Upload -->
        <div class="bento-card">
            <div class="d-flex justify-content-between align-items-center gap-2 mb-2">
                <h4 class="fw-bold mb-0">Project Deliverables</h4>
                <span class="pro-chip chip-info">PDF • PNG • JPG • JPEG</span>
            </div>
            <p class="small mb-3" style="color: var(--text-secondary);">
                Link your GitHub repository and upload your report or architecture snapshot.
            </p>
            <form id="finalForm" data-watch-dirty="true" onsubmit="saveFinalRealtime(event)" enctype="multipart/form-data">
                {% csrf_token %}
                <div class="mb-3">
                    <label class="form-label">GitHub Repository URL</label>
                    <input type="url" name="github_repo_link" class="form-control" value="{{ group.github_repo_link|default:'https://github.com/ahmetrida/protrack' }}" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">Upload Report or Screenshot (PDF, PNG, JPG, JPEG)</label>
                    <input type="file" name="final_report_pdf" class="form-control" accept=".pdf,.png,.jpg,.jpeg">
                    <div id="file-link-box" class="mt-2">
                        {% if group.final_report_pdf %}
                        <a href="{{ group.final_report_pdf.url }}" target="_blank" class="pro-chip chip-success text-decoration-none mt-1">
                            <i class="bi bi-file-earmark-check-fill"></i> View Uploaded Deliverable
                        </a>
                        {% endif %}
                    </div>
                </div>
                <button type="submit" id="btnSaveFinal" class="btn-pro-secondary w-100">
                    <i class="bi bi-cloud-arrow-up-fill"></i> <span>Save Deliverables</span>
                </button>
            </form>
        </div>
    </div>
</div>

<!-- Weekly Progress Timeline Table -->
<div class="bento-card mt-4">
    <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
        <h4 class="fw-bold mb-0">Weekly Progress Timeline</h4>
        <span class="pro-chip chip-primary"><i class="bi bi-pencil-square"></i> Click Edit on any row to update</span>
    </div>
    <div class="table-responsive">
        <table class="table table-pro mb-0">
            <thead>
                <tr>
                    <th>Week</th>
                    <th>Progress Summary</th>
                    <th>Repository Link</th>
                    <th>Guide Remarks</th>
                    <th>Status</th>
                    <th class="text-end">Action</th>
                </tr>
            </thead>
            <tbody id="logbook-tbody">
                {% for log in logs %}
                <tr id="log-row-{{ log.week_number }}">
                    <td class="fw-bold text-nowrap">Week {{ log.week_number }}</td>
                    <td id="log-tasks-{{ log.week_number }}">{{ log.tasks_completed }}</td>
                    <td>
                        {% if log.commit_or_doc_link %}
                        <a href="{{ log.commit_or_doc_link }}" target="_blank" class="pro-chip chip-primary text-decoration-none py-1 px-3">
                            <span>Repo</span> <i class="bi bi-box-arrow-up-right"></i>
                        </a>
                        {% else %}-{% endif %}
                    </td>
                    <td class="small" style="color: var(--text-secondary);">{{ log.guide_remarks|default:"Awaiting guide review" }}</td>
                    <td>
                        <span class="pro-chip {% if log.approval_status == 'APPROVED' %}chip-success{% elif log.approval_status == 'CHANGES_NEEDED' %}chip-error{% else %}chip-warning{% endif %}">
                            {{ log.get_approval_status_display }}
                        </span>
                    </td>
                    <td class="text-end">
                        <button type="button" class="btn-pro-secondary py-1 px-3"
                            onclick="loadLogIntoEditor('{{ log.week_number }}', '{{ log.tasks_completed|escapejs }}', '{{ log.commit_or_doc_link|default:''|escapejs }}')">
                            <i class="bi bi-pencil-square"></i> <span>Edit</span>
                        </button>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>

<script>
function updateSimUI(data) {
    const box = document.getElementById('sim-box');
    const scoreEl = document.getElementById('sim-score');
    const bar = document.getElementById('sim-bar');
    const matchEl = document.getElementById('sim-match');

    scoreEl.textContent = `${data.score}%`;
    bar.style.width = `${data.score}%`;

    const isHigh = data.score >= 50;
    box.className = `p-3 mb-4 rounded-4 ${isHigh ? 'chip-error' : 'chip-success'}`;
    bar.style.backgroundColor = isHigh ? 'var(--s-error)' : 'var(--s-success)';

    const kwHtml = (data.keywords && data.keywords.length)
        ? ` • Overlapping terms: <em>${data.keywords.join(', ')}</em>`
        : '';
    matchEl.innerHTML = `Closest Match: <strong>${data.match_title}</strong> (${data.match_source})${kwHtml}`;
}

async function checkSimilarityRealtime() {
    const btn = document.getElementById('btnCheckSim');
    setButtonLoading(btn, 'Scanning Archive...');
    const form = document.getElementById('proposalForm');
    const res = await fetch("{% url 'api_check_similarity' %}", {
        method: 'POST',
        headers: { 'X-CSRFToken': getCSRFToken() },
        body: new FormData(form)
    });
    const data = await res.json();
    if (data.ok) {
        updateSimUI(data);
        lockActionButton(btn, `Verified (${data.score}%) ✓`);
        showToast(data.message, data.level);
    }
}

async function saveProposalRealtime(e) {
    e.preventDefault();
    const btn = document.getElementById('btnSaveProposal');
    setButtonLoading(btn, 'Saving Proposal...');
    const form = document.getElementById('proposalForm');
    const res = await fetch("{% url 'submit_proposal' %}", {
        method: 'POST',
        headers: { 'X-CSRFToken': getCSRFToken() },
        body: new FormData(form)
    });
    const data = await res.json();
    if (data.ok) {
        updateSimUI(data);
        const pill = document.getElementById('proposal-status-pill');
        pill.textContent = data.status_display;
        pill.className = 'pro-chip chip-warning';
        lockActionButton(btn, 'Proposal Saved ✓');
        showToast(data.message, data.level);
    }
}

function loadLogIntoEditor(week, tasks, link) {
    document.getElementById('log_week').value = week;
    document.getElementById('log_tasks').value = tasks;
    document.getElementById('log_link').value = link;
    document.getElementById('log-form-heading').textContent = `Edit Week ${week}`;
    document.getElementById('log-mode-badge').textContent = `Editing Week ${week}`;
    const btn = document.getElementById('btnSaveLog');
    unlockActionButton(btn);
    btn.innerHTML = `<i class="bi bi-check2-circle"></i> <span>Update Week ${week} Progress</span>`;
    btn.dataset.defaultHtml = btn.innerHTML;
    document.getElementById('log_tasks').focus();
    showToast(`Loaded Week ${week} for editing.`, 'info');
}

async function saveLogRealtime(e) {
    e.preventDefault();
    const btn = document.getElementById('btnSaveLog');
    setButtonLoading(btn, 'Saving Log...');
    const form = document.getElementById('logForm');
    const res = await fetch("{% url 'add_weekly_log' %}", {
        method: 'POST',
        headers: { 'X-CSRFToken': getCSRFToken() },
        body: new FormData(form)
    });
    const data = await res.json();
    if (data.ok) {
        const l = data.log;
        lockActionButton(btn, `Week ${l.week_number} Saved ✓`);
        showToast(data.message, data.level);

        const tbody = document.getElementById('logbook-tbody');
        const existingRow = document.getElementById(`log-row-${l.week_number}`);
        const rowHtml = `
            <td class="fw-bold text-nowrap">Week ${l.week_number}</td>
            <td id="log-tasks-${l.week_number}">${l.tasks_completed}</td>
            <td>${l.commit_or_doc_link ? `<a href="${l.commit_or_doc_link}" target="_blank" class="pro-chip chip-primary text-decoration-none py-1 px-3"><span>Repo</span> <i class="bi bi-box-arrow-up-right"></i></a>` : '-'}</td>
            <td class="small" style="color: var(--text-secondary);">${l.guide_remarks}</td>
            <td><span class="pro-chip chip-warning">${l.status_display}</span></td>
            <td class="text-end">
                <button type="button" class="btn-pro-secondary py-1 px-3"
                    onclick="loadLogIntoEditor('${l.week_number}', '${l.tasks_completed.replace(/'/g, "\\'")}', '${l.commit_or_doc_link}')">
                    <i class="bi bi-pencil-square"></i> <span>Edit</span>
                </button>
            </td>
        `;
        if (existingRow) {
            existingRow.innerHTML = rowHtml;
        } else {
            const tr = document.createElement('tr');
            tr.id = `log-row-${l.week_number}`;
            tr.innerHTML = rowHtml;
            tbody.appendChild(tr);
        }
    }
}

async function saveFinalRealtime(e) {
    e.preventDefault();
    const btn = document.getElementById('btnSaveFinal');
    setButtonLoading(btn, 'Uploading...');
    const form = document.getElementById('finalForm');
    const res = await fetch("{% url 'upload_final_submission' %}", {
        method: 'POST',
        headers: { 'X-CSRFToken': getCSRFToken() },
        body: new FormData(form)
    });
    const data = await res.json();
    if (data.ok) {
        document.getElementById('stage-text').textContent = data.stage_display;
        if (data.file_url) {
            document.getElementById('file-link-box').innerHTML = `
                <a href="${data.file_url}" target="_blank" class="pro-chip chip-success text-decoration-none mt-1">
                    <i class="bi bi-file-earmark-check-fill"></i> View ${data.file_name || 'Uploaded Deliverable'}
                </a>`;
        }
        lockActionButton(btn, 'Deliverables Saved ✓');
        showToast(data.message, data.level);
    } else {
        unlockActionButton(btn);
        showToast(data.message || 'Upload failed.', 'error');
    }
}
</script>
{% endblock %}
"""

# --- templates/guide_dashboard.html ---
files["templates/guide_dashboard.html"] = """{% extends 'base.html' %}
{% block content %}
<div class="bento-card mb-4 d-flex flex-wrap justify-content-between align-items-center gap-3">
    <div>
        <span class="small fw-bold text-uppercase" style="color: var(--p-primary);">Faculty Guide Workspace</span>
        <h2 class="fw-bold mb-0">{{ user.first_name|default:"Professor Saurabh Pagar" }}</h2>
    </div>
    <span class="pro-chip chip-primary fs-6">{{ groups|length }} Assigned Groups</span>
</div>

<div class="row g-4">
    {% for g in groups %}
    <div class="col-12">
        <div class="bento-card">
            <div class="d-flex flex-wrap justify-content-between align-items-start border-bottom pb-3 mb-4 gap-3">
                <div>
                    <h3 class="fw-bold mb-2">{{ g.group_name }}</h3>
                    <div class="d-flex flex-wrap gap-2 mb-2">
                        {% for m in g.members.all %}
                        <span class="pro-chip chip-member"><i class="bi bi-person"></i> {{ m.first_name|default:m.username }}</span>
                        {% empty %}
                        <span class="small text-muted">No members listed</span>
                        {% endfor %}
                    </div>
                    <div class="small">
                        GitHub Repo: {% if g.github_repo_link %}<a href="{{ g.github_repo_link }}" target="_blank" class="fw-semibold text-decoration-none" style="color: var(--p-primary);">{{ g.github_repo_link }}</a>{% else %}Not uploaded{% endif %}
                    </div>
                </div>
                <span id="guide-stage-{{ g.id }}" class="pro-chip chip-primary fs-6">{{ g.get_current_stage_display }}</span>
            </div>

            {% if g.proposal %}
            <div class="row g-4 align-items-center mb-4 p-3 rounded-4" style="background: var(--p-wash);">
                <div class="col-lg-7">
                    <div class="d-flex flex-wrap align-items-center gap-2 mb-2">
                        <span class="pro-chip {% if g.proposal.similarity_score >= 50 %}chip-error{% else %}chip-success{% endif %}">
                            Smart Similarity: {{ g.proposal.similarity_score }}%
                        </span>
                        <span id="prop-badge-{{ g.proposal.id }}" class="pro-chip {% if g.proposal.status == 'APPROVED' %}chip-success{% elif g.proposal.status == 'REJECTED' %}chip-error{% else %}chip-warning{% endif %}">
                            {{ g.proposal.get_status_display }}
                        </span>
                    </div>
                    <h5 class="fw-bold mb-1">{{ g.proposal.proposed_title }}</h5>
                    <p class="small mb-2" style="color: var(--text-secondary);">{{ g.proposal.abstract_text }}</p>
                    <div class="small" style="color: var(--text-secondary);">
                        Closest Match: <strong>{{ g.proposal.closest_match_title }}</strong> ({{ g.proposal.closest_match_source }})
                    </div>
                </div>
                <div class="col-lg-5">
                    <form data-watch-dirty="true" onsubmit="reviewProposalRealtime(event, {{ g.proposal.id }}, {{ g.id }})" class="bg-white p-3 rounded-4 border">
                        {% csrf_token %}
                        <label class="form-label">Guide Decision & Remarks</label>
                        <input type="text" name="reviewer_remarks" class="form-control mb-2" value="{{ g.proposal.reviewer_remarks|default:'' }}" placeholder="Enter remarks for students...">
                        <div class="d-flex gap-2">
                            <select name="status" class="form-select">
                                <option value="APPROVED" {% if g.proposal.status == 'APPROVED' %}selected{% endif %}>Approve Proposal</option>
                                <option value="REJECTED" {% if g.proposal.status == 'REJECTED' %}selected{% endif %}>Request Changes</option>
                            </select>
                            {% if g.proposal.status == 'APPROVED' %}
                            <button type="submit" id="btn-prop-{{ g.proposal.id }}" class="btn-pro btn-locked" disabled
                                data-default-html='<i class="bi bi-check2-circle"></i> <span>Update Decision</span>'>
                                <i class="bi bi-check2-circle"></i> <span>Approved ✓</span>
                            </button>
                            {% else %}
                            <button type="submit" id="btn-prop-{{ g.proposal.id }}" class="btn-pro"
                                data-default-html='<i class="bi bi-check2-circle"></i> <span>Confirm Decision</span>'>
                                <i class="bi bi-check2-circle"></i> <span>Confirm Decision</span>
                            </button>
                            {% endif %}
                        </div>
                    </form>
                </div>
            </div>
            {% endif %}

            <h5 class="fw-bold mb-3">Weekly Progress Sign-Offs</h5>
            <div class="table-responsive">
                <table class="table table-pro mb-0">
                    <thead>
                        <tr><th>Week</th><th>Tasks Completed</th><th>Status</th><th>Guide Action</th></tr>
                    </thead>
                    <tbody>
                        {% for log in g.weekly_logs.all %}
                        <tr>
                            <td class="fw-bold text-nowrap">Week {{ log.week_number }}</td>
                            <td>{{ log.tasks_completed }}</td>
                            <td>
                                <span id="log-pill-{{ log.id }}" class="pro-chip {% if log.approval_status == 'APPROVED' %}chip-success{% elif log.approval_status == 'CHANGES_NEEDED' %}chip-error{% else %}chip-warning{% endif %}">
                                    {{ log.get_approval_status_display }}
                                </span>
                            </td>
                            <td style="min-width: 360px;">
                                <form data-watch-dirty="true" onsubmit="reviewLogRealtime(event, {{ log.id }})" class="d-flex gap-2">
                                    {% csrf_token %}
                                    <input type="text" name="guide_remarks" class="form-control py-2" value="{{ log.guide_remarks|default:'' }}" placeholder="Guide feedback...">
                                    <select name="approval_status" class="form-select py-2 w-auto">
                                        <option value="APPROVED" {% if log.approval_status == 'APPROVED' %}selected{% endif %}>Sign Off</option>
                                        <option value="CHANGES_NEEDED" {% if log.approval_status == 'CHANGES_NEEDED' %}selected{% endif %}>Revise</option>
                                    </select>
                                    {% if log.approval_status == 'APPROVED' %}
                                    <button type="submit" id="btn-log-{{ log.id }}" class="btn-pro py-2 px-3 btn-locked" disabled
                                        data-default-html='<i class="bi bi-check2"></i> <span>Update</span>'>
                                        <i class="bi bi-check2-circle"></i> <span>Signed Off ✓</span>
                                    </button>
                                    {% else %}
                                    <button type="submit" id="btn-log-{{ log.id }}" class="btn-pro py-2 px-3"
                                        data-default-html='<i class="bi bi-check2"></i> <span>Sign Off</span>'>
                                        <i class="bi bi-check2"></i> <span>Sign Off</span>
                                    </button>
                                    {% endif %}
                                </form>
                            </td>
                        </tr>
                        {% empty %}
                        <tr><td colspan="4" class="text-muted text-center">No weekly logs submitted yet.</td></tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    {% endfor %}
</div>

<script>
async function reviewProposalRealtime(e, propId, groupId) {
    e.preventDefault();
    const btn = document.getElementById(`btn-prop-${propId}`);
    setButtonLoading(btn, 'Saving...');
    const res = await fetch(`/review-proposal/${propId}/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCSRFToken() },
        body: new FormData(e.target)
    });
    const data = await res.json();
    if (data.ok) {
        const badge = document.getElementById(`prop-badge-${propId}`);
        badge.textContent = data.status_display;
        badge.className = `pro-chip ${data.status === 'APPROVED' ? 'chip-success' : 'chip-error'}`;
        document.getElementById(`guide-stage-${groupId}`).textContent = data.stage_display;
        lockActionButton(btn, `${data.status_display} ✓`);
        showToast(data.message, data.level);
    }
}

async function reviewLogRealtime(e, logId) {
    e.preventDefault();
    const btn = document.getElementById(`btn-log-${logId}`);
    setButtonLoading(btn, 'Saving...');
    const res = await fetch(`/review-log/${logId}/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCSRFToken() },
        body: new FormData(e.target)
    });
    const data = await res.json();
    if (data.ok) {
        const pill = document.getElementById(`log-pill-${logId}`);
        pill.textContent = data.status_display;
        pill.className = `pro-chip ${data.approval_status === 'APPROVED' ? 'chip-success' : 'chip-warning'}`;
        lockActionButton(btn, `${data.status_display} ✓`);
        showToast(data.message, data.level);
    }
}
</script>
{% endblock %}
"""

# --- templates/examiner_viva.html ---
files["templates/examiner_viva.html"] = """{% extends 'base.html' %}
{% block content %}
<div class="bento-card mb-4 d-flex flex-wrap justify-content-between align-items-center gap-3">
    <div>
        <span class="small fw-bold text-uppercase" style="color: var(--p-primary);">External Examiner Viva Portal</span>
        <h2 class="fw-bold mb-0">{{ user.first_name|default:"Professor Secretly Anonymous" }}</h2>
    </div>
    <a href="{% url 'export_marksheet_csv' %}" class="btn-pro text-decoration-none">
        <i class="bi bi-download"></i> <span>Download Official Marksheet (CSV)</span>
    </a>
</div>

<div class="row g-4">
    {% for g in groups %}
    <div class="col-12">
        <div class="bento-card">
            <div class="d-flex flex-wrap justify-content-between align-items-start gap-3 mb-4">
                <div>
                    <h4 class="fw-bold mb-2">{{ g.group_name }} — {{ g.proposal.proposed_title|default:"Untitled" }}</h4>
                    <div class="d-flex flex-wrap gap-2 mb-2">
                        {% for m in g.members.all %}
                        <span class="pro-chip chip-member"><i class="bi bi-person"></i> {{ m.first_name|default:m.username }}</span>
                        {% endfor %}
                    </div>
                    <span class="small" style="color: var(--text-secondary);">
                        Guide: <strong>{{ g.guide.first_name|default:"Unassigned" }}</strong> •
                        Repo: {% if g.github_repo_link %}<a href="{{ g.github_repo_link }}" target="_blank" style="color: var(--p-primary);">{{ g.github_repo_link }}</a>{% else %}N/A{% endif %}
                    </span>
                </div>
                <span id="viva-badge-{{ g.id }}" class="pro-chip {% if g.viva_evaluation %}chip-success{% else %}chip-warning{% endif %} fs-6 px-3 py-2">
                    {% if g.viva_evaluation %}
                        Evaluated: {{ g.viva_evaluation.total_marks }}/100 (Grade {{ g.viva_evaluation.grade }})
                    {% else %}
                        Pending Viva Evaluation
                    {% endif %}
                </span>
            </div>

            <form data-watch-dirty="true" onsubmit="saveVivaRealtime(event, {{ g.id }})" oninput="calcLiveTotal({{ g.id }})" id="viva-form-{{ g.id }}">
                {% csrf_token %}
                <div class="row g-3 mb-3">
                    <div class="col-md-2 col-6">
                        <label class="form-label">Problem Def (20)</label>
                        <input type="number" name="m1" min="0" max="20" class="form-control viva-input-{{ g.id }}" value="{{ g.viva_evaluation.problem_definition_marks|default:18 }}" required>
                    </div>
                    <div class="col-md-2 col-6">
                        <label class="form-label">Implementation (20)</label>
                        <input type="number" name="m2" min="0" max="20" class="form-control viva-input-{{ g.id }}" value="{{ g.viva_evaluation.implementation_marks|default:19 }}" required>
                    </div>
                    <div class="col-md-2 col-6">
                        <label class="form-label">Presentation (20)</label>
                        <input type="number" name="m3" min="0" max="20" class="form-control viva-input-{{ g.id }}" value="{{ g.viva_evaluation.presentation_marks|default:18 }}" required>
                    </div>
                    <div class="col-md-2 col-6">
                        <label class="form-label">Q&A Defense (20)</label>
                        <input type="number" name="m4" min="0" max="20" class="form-control viva-input-{{ g.id }}" value="{{ g.viva_evaluation.qa_defense_marks|default:18 }}" required>
                    </div>
                    <div class="col-md-2 col-6">
                        <label class="form-label">Documentation (20)</label>
                        <input type="number" name="m5" min="0" max="20" class="form-control viva-input-{{ g.id }}" value="{{ g.viva_evaluation.documentation_marks|default:19 }}" required>
                    </div>
                    <div class="col-md-2 col-6 d-flex flex-column justify-content-end">
                        <div class="p-2 text-center rounded-4" style="background: var(--p-wash); border: 1px solid var(--p-tint);">
                            <span class="small d-block" style="color: var(--text-secondary);">Live Total</span>
                            <strong id="live-total-{{ g.id }}" class="fs-5" style="color: var(--p-dark);">{{ g.viva_evaluation.total_marks|default:92 }}/100</strong>
                        </div>
                    </div>
                </div>
                <div class="row g-2 align-items-center">
                    <div class="col-md-9">
                        <input type="text" name="examiner_comments" class="form-control" value="{{ g.viva_evaluation.examiner_comments|default:'' }}" placeholder="Enter official viva remarks...">
                    </div>
                    <div class="col-md-3">
                        {% if g.viva_evaluation %}
                        <button type="submit" id="btn-viva-{{ g.id }}" class="btn-pro w-100 btn-locked" disabled
                            data-default-html='<i class="bi bi-award"></i> <span>Update Viva Grade</span>'>
                            <i class="bi bi-check2-circle"></i> <span>Grade Locked ✓</span>
                        </button>
                        {% else %}
                        <button type="submit" id="btn-viva-{{ g.id }}" class="btn-pro w-100"
                            data-default-html='<i class="bi bi-award"></i> <span>Submit Viva Grade</span>'>
                            <i class="bi bi-award"></i> <span>Submit Viva Grade</span>
                        </button>
                        {% endif %}
                    </div>
                </div>
            </form>
        </div>
    </div>
    {% endfor %}
</div>

<script>
function calcLiveTotal(groupId) {
    const inputs = document.querySelectorAll(`.viva-input-${groupId}`);
    let sum = 0;
    inputs.forEach(inp => sum += parseInt(inp.value || 0, 10));
    document.getElementById(`live-total-${groupId}`).textContent = `${sum}/100`;
}

async function saveVivaRealtime(e, groupId) {
    e.preventDefault();
    const btn = document.getElementById(`btn-viva-${groupId}`);
    setButtonLoading(btn, 'Locking Grade...');
    const res = await fetch(`/submit-viva/${groupId}/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCSRFToken() },
        body: new FormData(e.target)
    });
    const data = await res.json();
    if (data.ok) {
        const badge = document.getElementById(`viva-badge-${groupId}`);
        badge.className = 'pro-chip chip-success fs-6 px-3 py-2';
        badge.textContent = `Evaluated: ${data.total_marks}/100 (Grade ${data.grade})`;
        lockActionButton(btn, 'Grade Locked ✓');
        showToast(data.message, data.level);
    }
}
</script>
{% endblock %}
"""

# --- templates/coordinator_dashboard.html ---
files["templates/coordinator_dashboard.html"] = """{% extends 'base.html' %}
{% block content %}
<div class="bento-card mb-4 d-flex flex-wrap justify-content-between align-items-center gap-3">
    <div>
        <span class="small fw-bold text-uppercase" style="color: var(--p-primary);">Project Coordinator Overview</span>
        <h2 class="fw-bold mb-0">{{ user.first_name|default:"Professor Prajakta Borse" }}</h2>
    </div>
    <a href="{% url 'export_marksheet_csv' %}" class="btn-pro text-decoration-none">
        <i class="bi bi-file-earmark-spreadsheet"></i> <span>Export Official Marksheet</span>
    </a>
</div>

<div class="row g-4 mb-4">
    <div class="col-lg-4">
        <div class="bento-card h-100 d-flex flex-column justify-content-between">
            <h5 class="fw-bold mb-3">Department Stage Breakdown</h5>
            <canvas id="stageChart" height="220"></canvas>
        </div>
    </div>
    <div class="col-lg-8">
        <div class="bento-card h-100">
            <h5 class="fw-bold mb-3">Registered Groups & Smart Similarity Status</h5>
            <div class="table-responsive">
                <table class="table table-pro mb-0">
                    <thead>
                        <tr><th>Group & Roster</th><th>Project Title</th><th>Similarity</th><th>Guide</th><th>Stage</th><th>Marks</th></tr>
                    </thead>
                    <tbody>
                        {% for g in groups %}
                        <tr>
                            <td>
                                <div class="fw-bold text-nowrap">{{ g.group_name }}</div>
                                <div class="small text-muted">
                                    {% for m in g.members.all %}{{ m.first_name }}{% if not forloop.last %}, {% endif %}{% endfor %}
                                </div>
                            </td>
                            <td>{{ g.proposal.proposed_title|default:"Not Submitted" }}</td>
                            <td>
                                {% if g.proposal %}
                                <span class="pro-chip {% if g.proposal.similarity_score >= 50 %}chip-error{% else %}chip-success{% endif %}">
                                    {{ g.proposal.similarity_score }}%
                                </span>
                                {% else %}-{% endif %}
                            </td>
                            <td class="text-nowrap small fw-medium">{{ g.guide.first_name|default:"Unassigned" }}</td>
                            <td><span class="pro-chip chip-primary">{{ g.get_current_stage_display }}</span></td>
                            <td class="fw-bold text-nowrap">
                                {% if g.viva_evaluation %}{{ g.viva_evaluation.total_marks }}/100 ({{ g.viva_evaluation.grade }}){% else %}Pending{% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<div class="bento-card">
    <h5 class="fw-bold mb-3">Departmental Past Project Archive (TF-IDF Reference Corpus)</h5>
    <div class="table-responsive">
        <table class="table table-pro mb-0">
            <thead><tr><th>Batch</th><th>Domain</th><th>Project Title</th><th>Abstract Summary</th></tr></thead>
            <tbody>
                {% for a in archives %}
                <tr>
                    <td><span class="pro-chip chip-primary">{{ a.batch_year }}</span></td>
                    <td class="fw-medium text-nowrap">{{ a.domain }}</td>
                    <td class="fw-semibold">{{ a.title }}</td>
                    <td class="small" style="color: var(--text-secondary);">{{ a.abstract|truncatechars:100 }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>

<script>
new Chart(document.getElementById('stageChart'), {
    type: 'doughnut',
    data: {
        labels: ['Topic Pending', 'In Progress', 'Ready for Viva', 'Evaluated'],
        datasets: [{
            data: [{{ stage_counts.pending }}, {{ stage_counts.progress }}, {{ stage_counts.ready }}, {{ stage_counts.evaluated }}],
            backgroundColor: ['#9A6514', '#604A8B', '#3B6FA3', '#2F7D57'],
            borderWidth: 0
        }]
    },
    options: {
        cutout: '72%',
        plugins: { legend: { position: 'bottom' } }
    }
});
</script>
{% endblock %}
"""

for filepath, content in files.items():
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ Updated {filepath}")

print("\n🗄️ Applying Database Migrations...")
subprocess.run([sys.executable, "manage.py", "makemigrations", "portal"], check=True)
subprocess.run([sys.executable, "manage.py", "migrate"], check=True)

print("\n🌱 Seeding Updated Team Claudeus Roster & Faculty Names...")
subprocess.run([sys.executable, "manage.py", "seed_data"], check=True)

print("\n🚀 ProTrack v3.0 Masterpiece Edition is Ready!")
print("👉 Run: python manage.py runserver 0.0.0.0:8000")