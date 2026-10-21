# Force Launch - ProTrack v1.08 Enterprise Edition
from django.contrib import admin
from .models import (
    University, College, Department, UserProfile,
    ProjectGroup, ProjectProposal, StudentProjectHistory, WeeklyLog,
    VivaEvaluation, PastProjectArchive, Notification
)

admin.site.register(University)
admin.site.register(College)
admin.site.register(Department)
admin.site.register(UserProfile)
admin.site.register(ProjectGroup)
admin.site.register(ProjectProposal)
admin.site.register(StudentProjectHistory)
admin.site.register(WeeklyLog)
admin.site.register(VivaEvaluation)
admin.site.register(PastProjectArchive)
admin.site.register(Notification)
