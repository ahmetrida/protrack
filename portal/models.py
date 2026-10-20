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
