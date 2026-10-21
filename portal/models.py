# Force Launch - ProTrack v1.07 Enterprise Edition
import re
import random
import string
from django.db import models
from django.contrib.auth.models import User

def generate_join_code():
    """Generates a unique, exactly 5-character uppercase alphanumeric join code."""
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

def validate_role_identifier(role, identifier):
    """
    Validates role-specific IDs without hyphens or dashes and without reformatting:
    - STUDENT: 3 chars -> 1 letter + 2 digits (e.g., A12)
    - GUIDE:   4 chars -> 2 letters + 2 digits (e.g., AB12)
    - ADMIN:   6 chars -> 4 letters + 2 digits (e.g., ABCD12)
    """
    if not identifier:
        return False, "ID / Roll Number is required."
    if '-' in identifier or ' ' in identifier:
        return False, "No hyphens, dashes, or spaces are allowed in Roll Numbers or IDs."

    role = (role or 'STUDENT').upper()
    if role == 'STUDENT':
        if not re.match(r'^[A-Za-z][0-9]{2}$', identifier):
            return False, "Student Roll Number must be 3 characters: 1 letter followed by 2 digits (e.g., A12)."
    elif role == 'GUIDE':
        if not re.match(r'^[A-Za-z]{2}[0-9]{2}$', identifier):
            return False, "Faculty ID must be 4 characters: 2 letters followed by 2 digits (e.g., AB12)."
    elif role == 'ADMIN':
        if not re.match(r'^[A-Za-z]{4}[0-9]{2}$', identifier):
            return False, "Admin ID must be 6 characters: 4 letters followed by 2 digits (e.g., ABCD12)."
    return True, ""

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

    identifier = models.CharField(max_length=60, blank=True, help_text="Roll Call (A12), Faculty ID (AB12), or Admin ID (ABCD12)")
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
    GUIDE_STATUS_CHOICES = [
        ('NONE', 'No Guide Requested'),
        ('PENDING', 'Pending Faculty Guide Acceptance'),
        ('ACCEPTED', 'Guide Assigned'),
        ('DECLINED', 'Guide Request Declined'),
    ]
    name = models.CharField(max_length=120)
    join_code = models.CharField(max_length=12, unique=True, default=generate_join_code)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='groups')
    creator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_groups')
    guide = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='guided_groups')
    requested_guide = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='requested_guide_groups')
    guide_status = models.CharField(max_length=20, choices=GUIDE_STATUS_CHOICES, default='NONE')
    students = models.ManyToManyField(User, related_name='student_groups', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.join_code or len(self.join_code) != 5 or ProjectGroup.objects.filter(join_code=self.join_code).exclude(pk=self.pk).exists():
            self.join_code = generate_join_code()
        if self.guide_id and self.guide_status != 'ACCEPTED':
            self.guide_status = 'ACCEPTED'
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
    tech_stack = models.CharField(max_length=250, blank=True, default='')
    abstract = models.TextField()
    similarity_score = models.FloatField(default=0.0)
    closest_match_title = models.CharField(max_length=250, blank=True, default='None')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    guide_remarks = models.TextField(blank=True)
    report_file = models.FileField(upload_to='reports/', null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

class StudentProjectHistory(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='project_histories')
    team_name = models.CharField(max_length=150)
    project_idea = models.CharField(max_length=250)
    brief_description = models.TextField()
    tech_stack = models.CharField(max_length=250)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.username} - {self.team_name}: {self.project_idea}"

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
