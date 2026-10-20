from django.contrib import admin
from .models import UserProfile, PastProjectArchive, ProjectGroup, ProjectProposal, WeeklyLog, VivaEvaluation, Notification

admin.site.register(UserProfile)
admin.site.register(PastProjectArchive)
admin.site.register(ProjectGroup)
admin.site.register(ProjectProposal)
admin.site.register(WeeklyLog)
admin.site.register(VivaEvaluation)
admin.site.register(Notification)
