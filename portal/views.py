import re
import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from .models import (
    University, College, Department, UserProfile,
    ProjectGroup, ProjectProposal, WeeklyLog,
    VivaEvaluation, PastProjectArchive, Notification
)
from .similarity import check_abstract_similarity, FALLBACK_CORPUS

ALLOWED_PROOF_EXT = ('.jpg', '.jpeg', '.png', '.webp', '.pdf')
ALLOWED_AVATAR_EXT = ('.jpg', '.jpeg', '.png', '.webp')
ALLOWED_REPORT_EXT = ('.pdf', '.docx', '.doc', '.png', '.jpg', '.jpeg')

def notify_users(users, message):
    for u in users:
        if u:
            Notification.objects.create(user=u, message=message)

def validate_file_ext(uploaded_file, allowed_tuple):
    if not uploaded_file:
        return False
    return uploaded_file.name.lower().endswith(allowed_tuple)

def api_hierarchy(request):
    """Returns live cascading University -> College -> Department -> Registered Guides tree."""
    universities = list(University.objects.values('id', 'name'))
    colleges = list(College.objects.values('id', 'university_id', 'name'))
    departments = list(Department.objects.values('id', 'college_id', 'name', 'academic_year'))
    guides = []
    for g in UserProfile.objects.filter(role='GUIDE').select_related('user'):
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
            messages.error(request, "Invalid username or password. Please verify your credentials or create an account.")
    return render(request, 'login.html', {
        'total_universities': University.objects.count(),
        'total_colleges': College.objects.count(),
        'total_departments': Department.objects.count(),
        'total_users': UserProfile.objects.count(),
    })

def signup_view(request):
    if request.user.is_authenticated:
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

        # Basic Input Validations
        if len(full_name) < 2:
            messages.error(request, "Please enter your full name (e.g. John Doe).")
            return redirect('signup')

        if not re.match(r'^[a-zA-Z0-9_.-]{3,30}$', username):
            messages.error(request, "Username must be 3-30 characters using letters, numbers, dots, hyphens, or underscores.")
            return redirect('signup')

        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, f"Username '@{username}' is already taken. Try one of the suggested usernames.")
            return redirect('signup')

        if len(password) < 6:
            messages.error(request, "Password must be at least 6 characters long.")
            return redirect('signup')

        if not identifier:
            messages.error(request, "Please provide your Roll Call, Faculty ID, or Admin ID.")
            return redirect('signup')

        # Role-specific Institution & Proof Resolution
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
                messages.error(request, "Admin registration requires both Front and Back ID Proof uploads to verify authenticity.")
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
            # STUDENT or GUIDE: Strictly must select from Admin-populated dropdowns
            if not (uni_id.isdigit() and col_id.isdigit() and dept_id.isdigit()):
                messages.error(request, "Please select your University, College, and Department from the dropdown menus provided by your Admin.")
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
                        profile__department=department,
                        profile__role='GUIDE'
                    ).first()

        parts = full_name.split(' ', 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ''

        user = User.objects.create_user(
            username=username,
            email=email or f"{username}@example.com",
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

        # Notify Department Admins and Selected Guide
        dept_admins = User.objects.filter(profile__department=department, profile__role='ADMIN').exclude(id=user.id)
        notify_users(dept_admins, f"New {role.title()} registered in {department.name}: {full_name} ({identifier}).")
        if preferred_guide_user:
            notify_users([preferred_guide_user], f"Student {full_name} ({identifier}) selected you as their Project Guide.")

        login(request, user)
        messages.success(request, f"Account created! Welcome to {department.name}, {full_name}.")
        return redirect('dashboard_router')

    guides_list = UserProfile.objects.filter(role='GUIDE').select_related('user', 'department')
    return render(request, 'signup.html', {
        'universities': University.objects.all(),
        'colleges': College.objects.all(),
        'departments': Department.objects.all(),
        'guides_list': guides_list,
    })

def logout_view(request):
    logout(request)
    messages.info(request, "You have signed out safely.")
    return redirect('login')

@login_required
def dashboard_router(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if profile.role == 'ADMIN':
        return redirect('admin_dashboard')
    elif profile.role == 'GUIDE':
        return redirect('guide_dashboard')
    return redirect('student_dashboard')

@login_required
def mark_notifications_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect(request.META.get('HTTP_REFERER', 'dashboard_router'))

# ==============================================================================
# UNIVERSAL SETTINGS, PROFILE & WHATSAPP/SOCIAL DIRECTORY
# ==============================================================================
@login_required
def profile_settings_view(request):
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

            if full_name:
                parts = full_name.split(' ', 1)
                request.user.first_name = parts[0]
                request.user.last_name = parts[1] if len(parts) > 1 else ''
            if email:
                request.user.email = email
            request.user.save()

            if identifier:
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
                    g_user = User.objects.filter(id=int(pref_guide_id), profile__department=dept, profile__role='GUIDE').first()
                    if g_user:
                        profile.preferred_guide = g_user

            profile.save()
            messages.success(request, "Your profile, WhatsApp contact, and social links have been updated!")
            return redirect('profile_settings')

        elif action == 'change_password':
            new_pass = request.POST.get('new_password', '').strip()
            if len(new_pass) < 6:
                messages.error(request, "New password must be at least 6 characters.")
            else:
                request.user.set_password(new_pass)
                request.user.save()
                update_session_auth_hash(request, request.user)
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

    # Directory of everyone in the same department (or all if Admin filters)
    role_filter = request.GET.get('role_filter', 'ALL').strip()
    search_q = request.GET.get('q', '').strip()

    directory_qs = UserProfile.objects.filter(department=dept).select_related('user', 'department', 'college') if dept else UserProfile.objects.all().select_related('user')
    if role_filter in ('STUDENT', 'GUIDE', 'ADMIN'):
        directory_qs = directory_qs.filter(role=role_filter)
    elif role_filter == 'EXAMINER':
        directory_qs = directory_qs.filter(is_examiner=True)

    if search_q:
        directory_qs = [
            p for p in directory_qs
            if search_q.lower() in (p.user.get_full_name() or p.user.username).lower()
            or search_q.lower() in (p.identifier or '').lower()
        ]

    dept_guides = User.objects.filter(profile__department=dept, profile__role='GUIDE').select_related('profile') if dept else []

    return render(request, 'settings_profile.html', {
        'directory_profiles': directory_qs,
        'role_filter': role_filter,
        'search_q': search_q,
        'dept_guides': dept_guides,
        'notifications': request.user.notifications.filter(is_read=False)[:6],
    })

# ==============================================================================
# STUDENT WORKSPACE
# ==============================================================================
@login_required
def student_dashboard(request):
    profile = request.user.profile
    dept = profile.department
    group = request.user.student_groups.first()

    dept_guides = User.objects.filter(profile__department=dept, profile__role='GUIDE').select_related('profile')
    dept_students = User.objects.filter(
        profile__department=dept,
        profile__role='STUDENT',
        student_groups__isnull=True
    ).exclude(id=request.user.id).select_related('profile')
    open_groups = ProjectGroup.objects.filter(department=dept).prefetch_related('students', 'guide')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create_group' and not group:
            group_name = request.POST.get('group_name', '').strip()
            guide_id = request.POST.get('guide_id', '').strip()
            teammate_ids = request.POST.getlist('teammate_ids')

            if not group_name:
                messages.error(request, "Please enter a name for your project group.")
                return redirect('student_dashboard')

            guide_user = None
            if guide_id.isdigit():
                guide_user = User.objects.filter(id=int(guide_id), profile__department=dept, profile__role='GUIDE').first()
            elif profile.preferred_guide:
                guide_user = profile.preferred_guide

            new_group = ProjectGroup.objects.create(name=group_name, department=dept, guide=guide_user)
            new_group.students.add(request.user)

            for tid in teammate_ids:
                if tid.isdigit():
                    tm = User.objects.filter(id=int(tid), profile__department=dept, profile__role='STUDENT').first()
                    if tm and not tm.student_groups.exists():
                        new_group.students.add(tm)
                        notify_users([tm], f"{request.user.get_full_name()} added you to project group '{new_group.name}'.")

            if guide_user:
                notify_users([guide_user], f"Project group '{new_group.name}' is assigned under your mentorship.")
            messages.success(request, f"Group '{new_group.name}' initialized! Share Join Code {new_group.join_code} with teammates.")
            return redirect('student_dashboard')

        elif action == 'join_group' and not group:
            join_code = request.POST.get('join_code', '').strip().upper()
            target_group = ProjectGroup.objects.filter(join_code__iexact=join_code, department=dept).first()
            if not target_group:
                messages.error(request, f"No group found in {dept.name} with Join Code '{join_code}'.")
            else:
                target_group.students.add(request.user)
                notify_users(target_group.students.exclude(id=request.user.id), f"{request.user.get_full_name()} joined {target_group.name}!")
                messages.success(request, f"Successfully joined '{target_group.name}'!")
            return redirect('student_dashboard')

        elif action == 'submit_proposal' and group:
            title = request.POST.get('title', '').strip()
            domain = request.POST.get('domain', '').strip()
            abstract = request.POST.get('abstract', '').strip()
            report_file = request.FILES.get('report_file')

            if len(title) < 5 or len(abstract.split()) < 6:
                messages.error(request, "Please provide a descriptive project title and an abstract of at least 6 words.")
                return redirect('student_dashboard')

            if report_file and not validate_file_ext(report_file, ALLOWED_REPORT_EXT):
                messages.error(request, "Report file must be PDF, DOCX, PNG, or JPG.")
                return redirect('student_dashboard')

            sim_res = check_abstract_similarity(title, abstract, department=dept, exclude_group_id=group.id)
            proposal, _ = ProjectProposal.objects.get_or_create(group=group)
            proposal.title = title
            proposal.domain = domain or "Software Systems"
            proposal.abstract = abstract
            proposal.similarity_score = sim_res['score']
            proposal.closest_match_title = sim_res['closest_match']
            proposal.status = 'PENDING'
            if report_file:
                proposal.report_file = report_file
            proposal.save()

            if group.guide:
                notify_users([group.guide], f"{group.name} submitted proposal '{title}' (Similarity: {sim_res['score']}%).")
            messages.success(request, f"Proposal submitted to your guide! AI Similarity Score: {sim_res['score']}%.")
            return redirect('student_dashboard')

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
                    notify_users([group.guide], f"{group.name} submitted Week {week_num} progress log.")
                messages.success(request, f"Week {week_num} milestone recorded.")
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
    if profile.role not in ('GUIDE', 'ADMIN'):
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
            messages.success(request, f"You are now guiding '{grp.name}'.")

        elif action == 'review_proposal':
            pid = request.POST.get('proposal_id')
            decision = request.POST.get('decision')
            remarks = request.POST.get('guide_remarks', '').strip()
            prop = get_object_or_404(ProjectProposal, id=pid, group__guide=request.user)
            prop.status = decision
            prop.guide_remarks = remarks
            prop.save()
            verb = "approved" if decision == 'APPROVED' else "requested changes on"
            notify_users(prop.group.students.all(), f"Guide {request.user.get_full_name()} {verb} your proposal '{prop.title}'.")
            messages.success(request, f"Saved review for {prop.group.name}.")

        elif action == 'verify_log':
            lid = request.POST.get('log_id')
            feedback = request.POST.get('guide_feedback', '').strip()
            log_item = get_object_or_404(WeeklyLog, id=lid, group__guide=request.user)
            log_item.is_verified = True
            log_item.guide_feedback = feedback or "Verified & signed off by Project Guide."
            log_item.save()
            notify_users(log_item.group.students.all(), f"Week {log_item.week_number} log verified by {request.user.get_full_name()}.")
            messages.success(request, f"Verified Week {log_item.week_number} for {log_item.group.name}.")

        return redirect('guide_dashboard')

    my_groups = ProjectGroup.objects.filter(guide=request.user).prefetch_related('students__profile', 'logs')
    unassigned_groups = ProjectGroup.objects.filter(department=dept, guide__isnull=True).prefetch_related('students')
    registered_mentees = UserProfile.objects.filter(preferred_guide=request.user).select_related('user')

    pending_proposals = ProjectProposal.objects.filter(group__guide=request.user, status='PENDING').count()
    unverified_logs = WeeklyLog.objects.filter(group__guide=request.user, is_verified=False).count()

    return render(request, 'guide_dashboard.html', {
        'my_groups': my_groups,
        'unassigned_groups': unassigned_groups,
        'registered_mentees': registered_mentees,
        'pending_proposals': pending_proposals,
        'unverified_logs': unverified_logs,
        'notifications': request.user.notifications.filter(is_read=False)[:6],
    })

# ==============================================================================
# EXAMINER & HOD ANALYTICS PORTAL (REPLICATED HOD FEATURES + VIVA RUBRIC)
# ==============================================================================
@login_required
def examiner_dashboard(request):
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
            messages.success(request, f"Published Viva grade for {grp.name} ({viva.total_score}/100).")

        elif action == 'add_archive':
            title = request.POST.get('title', '').strip()
            year = request.POST.get('year', '2025').strip()
            domain = request.POST.get('domain', 'Computer Science').strip()
            abstract = request.POST.get('abstract', '').strip()
            if title and abstract:
                PastProjectArchive.objects.create(department=dept, title=title, year=year, domain=domain, abstract=abstract)
                messages.success(request, f"Added '{title}' to {dept.name} TF-IDF archive corpus.")

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
            messages.success(request, f"Loaded {added} benchmark abstracts into {dept.name}'s similarity engine.")

        return redirect('examiner_dashboard')

    groups = ProjectGroup.objects.filter(department=dept).prefetch_related('students__profile', 'logs')
    archives = PastProjectArchive.objects.filter(department=dept)
    dept_students_count = UserProfile.objects.filter(department=dept, role='STUDENT').count()

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
        'notifications': request.user.notifications.filter(is_read=False)[:6],
    })

# ==============================================================================
# INSTITUTION ADMIN COMMAND CENTER (GOVERNANCE + HIERARCHY + EXAMINER PROMOTION)
# ==============================================================================
@login_required
def admin_dashboard(request):
    profile = request.user.profile
    if profile.role != 'ADMIN':
        messages.error(request, "Only verified Institution Admins can access the Admin Governance Console.")
        return redirect('dashboard_router')

    if request.method == 'POST':
        action = request.POST.get('action')

        # 1. Add University
        if action == 'add_university':
            name = request.POST.get('university_name', '').strip()
            if name:
                University.objects.get_or_create(name=name, defaults={'created_by': request.user})
                messages.success(request, f"University '{name}' is now live across all signup dropdowns.")

        # 2. Add College under University
        elif action == 'add_college':
            uni_id = request.POST.get('university_id', '')
            col_name = request.POST.get('college_name', '').strip()
            if uni_id.isdigit() and col_name:
                u = get_object_or_404(University, id=int(uni_id))
                College.objects.get_or_create(university=u, name=col_name)
                messages.success(request, f"College '{col_name}' added under {u.name}.")

        # 3. Add Department under College
        elif action == 'add_department':
            col_id = request.POST.get('college_id', '')
            dept_name = request.POST.get('department_name', '').strip()
            acad_year = request.POST.get('academic_year', '2026-2027').strip()
            if col_id.isdigit() and dept_name:
                c = get_object_or_404(College, id=int(col_id))
                Department.objects.get_or_create(college=c, name=dept_name, defaults={'academic_year': acad_year})
                messages.success(request, f"Department '{dept_name}' added under {c.name}! Students and Guides can now enroll.")

        # 4. Promote or Demote Faculty Guide as Examiner
        elif action == 'toggle_examiner':
            prof_id = request.POST.get('profile_id', '')
            target_prof = get_object_or_404(UserProfile, id=prof_id, role='GUIDE')
            target_prof.is_examiner = not target_prof.is_examiner
            target_prof.save()
            state_str = "Promoted to External Examiner & HOD Analytics role" if target_prof.is_examiner else "Demoted to standard Faculty Guide role"
            notify_users([target_prof.user], f"Admin {request.user.get_full_name()} updated your role privileges: {state_str}.")
            messages.success(request, f"{target_prof.user.get_full_name() or target_prof.user.username}: {state_str}.")

        # 5. Reassign Group Guide
        elif action == 'assign_guide':
            gid = request.POST.get('group_id', '')
            guide_id = request.POST.get('guide_id', '')
            grp = get_object_or_404(ProjectGroup, id=gid)
            guide_user = get_object_or_404(User, id=guide_id, profile__role='GUIDE')
            grp.guide = guide_user
            grp.save()
            notify_users(grp.students.all(), f"Admin assigned {guide_user.get_full_name()} as your Project Guide.")
            messages.success(request, f"Assigned {guide_user.get_full_name()} to {grp.name}.")

        # 6. Delete Department Entity if needed
        elif action == 'delete_department':
            did = request.POST.get('dept_id', '')
            if did.isdigit():
                Department.objects.filter(id=int(did)).delete()
                messages.info(request, "Department removed.")

        return redirect('admin_dashboard')

    # Comprehensive Admin Datasets & Search Filters
    dept_filter = request.GET.get('dept_id', '').strip()
    search_q = request.GET.get('q', '').strip().lower()

    all_universities = University.objects.all()
    all_colleges = College.objects.select_related('university').all()
    all_departments = Department.objects.select_related('college__university').all()

    guides_qs = UserProfile.objects.filter(role='GUIDE').select_related('user', 'department', 'college', 'university')
    students_qs = UserProfile.objects.filter(role='STUDENT').select_related('user', 'department', 'college', 'preferred_guide')
    admins_qs = UserProfile.objects.filter(role='ADMIN').select_related('user', 'department', 'college')
    groups_qs = ProjectGroup.objects.select_related('department__college', 'guide').prefetch_related('students')

    if dept_filter.isdigit():
        guides_qs = guides_qs.filter(department_id=int(dept_filter))
        students_qs = students_qs.filter(department_id=int(dept_filter))
        groups_qs = groups_qs.filter(department_id=int(dept_filter))

    if search_q:
        guides_qs = [g for g in guides_qs if search_q in (g.user.get_full_name() or g.user.username).lower() or search_q in g.identifier.lower()]
        students_qs = [s for s in students_qs if search_q in (s.user.get_full_name() or s.user.username).lower() or search_q in s.identifier.lower()]

    return render(request, 'admin_dashboard.html', {
        'all_universities': all_universities,
        'all_colleges': all_colleges,
        'all_departments': all_departments,
        'guides_qs': guides_qs,
        'students_qs': students_qs,
        'admins_qs': admins_qs,
        'groups_qs': groups_qs,
        'dept_filter': dept_filter,
        'search_q': search_q,
        'examiners_count': UserProfile.objects.filter(is_examiner=True).count(),
        'notifications': request.user.notifications.filter(is_read=False)[:6],
    })

@login_required
def export_department_csv(request):
    dept = request.user.profile.department
    response = HttpResponse(content_type='text/csv')
    dept_label = dept.name.replace(' ', '_') if dept else 'All_Departments'
    response['Content-Disposition'] = f'attachment; filename="ProTrack_{dept_label}_Master_Report.csv"'
    writer = csv.writer(response)
    writer.writerow(['Group Name', 'Join Code', 'Department', 'Students', 'Project Guide', 'Proposal Title', 'Status', 'AI Similarity (%)', 'Verified Logs', 'Viva Score (/100)', 'Grade'])

    groups = ProjectGroup.objects.filter(department=dept) if dept else ProjectGroup.objects.all()
    for g in groups:
        students_str = ", ".join([s.get_full_name() or s.username for s in g.students.all()])
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
