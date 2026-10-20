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
    """Returns dynamic University -> College -> Department tree for cascading dropdowns."""
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
