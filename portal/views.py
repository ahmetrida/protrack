import csv
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
