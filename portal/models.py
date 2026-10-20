from django.db import models
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
