# Force Launch - ProTrack v1.07 Enterprise Edition
import re
import csv
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.views.decorators.cache import never_cache
from django.db.models import Q
from .models import (
    University, College, Department, UserProfile,
    ProjectGroup, ProjectProposal, StudentProjectHistory, WeeklyLog,
    VivaEvaluation, PastProjectArchive, Notification,
    generate_join_code, validate_role_identifier
)
from .similarity import check_abstract_similarity, FALLBACK_CORPUS

ALLOWED_PROOF_EXT = ('.jpg', '.jpeg', '.png', '.webp', '.pdf')
ALLOWED_AVATAR_EXT = ('.jpg', '.jpeg', '.png', '.webp')
ALLOWED_REPORT_EXT = ('.pdf', '.docx', '.doc', '.png', '.jpg', '.jpeg')
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

def is_valid_email_address(email):
    if not email or not EMAIL_REGEX.match(email):
        return False
    try:
        validate_email(email)
        return True
    except ValidationError:
        return False

def notify_users(users, message):
    for u in users:
        if u and not u.is_superuser:
            Notification.objects.create(user=u, message=message)

def validate_file_ext(uploaded_file, allowed_tuple):
    if not uploaded_file:
        return False
    return uploaded_file.name.lower().endswith(allowed_tuple)

def archive_group_to_student_history(student_user, group):
    """Records a student's team and project details into StudentProjectHistory when leaving or removed."""
    prop = getattr(group, 'proposal', None)
    idea = prop.title if prop and prop.title else f"Project under {group.name}"
    desc = prop.abstract if prop and prop.abstract else f"Collaborated as a member of team {group.name} in {group.department.name}."
    stack = (prop.tech_stack if prop and prop.tech_stack else (prop.domain if prop and prop.domain else "Python, Django, Web Technologies"))
    StudentProjectHistory.objects.create(
        student=student_user,
        team_name=group.name,
        project_idea=idea,
        brief_description=desc,
        tech_stack=stack
    )

def get_authorized_profile_ids(viewer_user):
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
            if grp.requested_guide_id:
                allowed_user_ids.add(grp.requested_guide_id)
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
    # Allow shared public profile links to be viewed by authenticated ProTrack users
    # while keeping superadmin isolated
    if viewer_user.is_authenticated:
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
    username = request.GET.get('username', '').strip().lower()
    full_name = request.GET.get('full_name', '').strip().lower()
    identifier = request.GET.get('identifier', '').strip().lower()

    exists = User.objects.filter(username__iexact=username).exists() if username else False

    clean_name = re.sub(r'[^a-z0-9\s]', '', full_name)
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
    """
    Interactive classmate search restricted strictly to the student's department.
    Includes the team creator (current user) marked with is_self=True so they appear
    in the dropdown but cannot add themselves.
    """
    if request.user.is_superuser:
        return JsonResponse({'results': []})
    profile = getattr(request.user, 'profile', None)
    if not profile or not profile.department:
        return JsonResponse({'results': []})

    q = request.GET.get('q', '').strip()
    qs = UserProfile.objects.filter(
        department=profile.department,
        role='STUDENT',
        user__is_superuser=False
    ).filter(
        Q(user__student_groups__isnull=True) | Q(user=request.user)
    ).select_related('user', 'department').distinct()

    if q:
        qs = qs.filter(
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q) |
            Q(user__username__icontains=q) |
            Q(identifier__icontains=q)
        )

    results = []
    # Put creator first if matching
    for p in qs[:25]:
        results.append({
            'user_id': p.user.id,
            'full_name': p.user.get_full_name() or p.user.username,
            'username': p.user.username,
            'identifier': p.identifier,
            'class_division': p.class_division,
            'department': p.department.name if p.department else '',
            'avatar_url': p.avatar_url,
            'initials': p.initials,
            'is_self': (p.user.id == request.user.id),
        })
    results.sort(key=lambda x: (0 if x['is_self'] else 1, x['full_name'].lower()))
    return JsonResponse({'results': results})

@login_required
def api_sync_drafts(request):
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
# AUTHENTICATION & SESSION PERSISTENCE
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
        if not u:
            request.session['play_who_are_you'] = True
            messages.error(request, "Wait a minute! Please enter your Username to sign in.")
            return redirect('login')

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
        # Preserve exact case/formatting of identifier as entered by the user
        identifier = request.POST.get('identifier', '').strip()
        class_division = request.POST.get('class_division', 'Class-A').strip()
        whatsapp_number = request.POST.get('whatsapp_number', '').strip()

        if len(full_name) < 2 or not username:
            request.session['play_who_are_you'] = True
            messages.error(request, "Wait a minute! Both Full Name and Username are required.")
            return redirect('signup')

        if not is_valid_email_address(email):
            messages.error(request, "A valid Email Address (e.g., johndoe@example.com) is mandatory.")
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

        # Strict Role-Based Roll Number / ID Validation (no hyphens/dashes, exact length & format)
        is_valid_id, id_err_msg = validate_role_identifier(role, identifier)
        if not is_valid_id:
            messages.error(request, id_err_msg)
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
            notify_users([preferred_guide_user], f"Student {full_name} ({identifier}) selected you as their preferred Faculty Guide.")

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
# DEDICATED PRIVATE SUPERADMIN FLOW
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
        if not u:
            request.session['play_who_are_you'] = True
            messages.error(request, "Wait a minute! Superadmin username is required.")
            return redirect('superadmin_login')

        user = authenticate(request, username=u, password=p)
        if user and user.is_superuser:
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

    UserProfile.objects.filter(user=request.user).delete()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_superadmin_profile':
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip()
            new_username = request.POST.get('username', '').strip()

            if not new_username:
                request.session['play_who_are_you'] = True
                messages.error(request, "Wait a minute! Username cannot be empty.")
                return redirect('superadmin_dashboard')

            if not is_valid_email_address(email):
                messages.error(request, "Please provide a valid email address.")
                return redirect('superadmin_dashboard')

            if new_username != request.user.username:
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
        messages.error(request, "Access Denied: This profile is outside your authorized scope.")
        return redirect('dashboard_router')

    student_group = target_user.student_groups.first() if target_profile.role == 'STUDENT' else None
    guided_groups = ProjectGroup.objects.filter(guide=target_user) if target_profile.role == 'GUIDE' else []
    student_histories = target_user.project_histories.all() if target_profile.role == 'STUDENT' else []

    return render(request, 'public_profile.html', {
        'target_user': target_user,
        'target_profile': target_profile,
        'student_group': student_group,
        'guided_groups': guided_groups,
        'student_histories': student_histories,
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

            if not full_name:
                request.session['play_who_are_you'] = True
                messages.error(request, "Wait a minute! Full Name cannot be empty.")
                return redirect('profile_settings')

            if not is_valid_email_address(email):
                messages.error(request, "A valid Email Address is mandatory.")
                return redirect('profile_settings')

            is_valid_id, id_err_msg = validate_role_identifier(profile.role, identifier)
            if not is_valid_id:
                messages.error(request, id_err_msg)
                return redirect('profile_settings')

            parts = full_name.split(' ', 1)
            request.user.first_name = parts[0]
            request.user.last_name = parts[1] if len(parts) > 1 else ''
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
            messages.success(request, "Your profile, email, avatar, and contact handles have been saved!")
            return redirect('profile_settings')

        elif action == 'add_history' and profile.role == 'STUDENT':
            team_name = request.POST.get('team_name', '').strip()
            project_idea = request.POST.get('project_idea', '').strip()
            brief_description = request.POST.get('brief_description', '').strip()
            tech_stack = request.POST.get('tech_stack', '').strip()
            if team_name and project_idea and brief_description and tech_stack:
                StudentProjectHistory.objects.create(
                    student=request.user,
                    team_name=team_name,
                    project_idea=project_idea,
                    brief_description=brief_description,
                    tech_stack=tech_stack
                )
                request.session['play_success_sound'] = True
                messages.success(request, f"Added '{project_idea}' ({team_name}) to your Student Project History.")
            else:
                messages.error(request, "Please complete all fields (Team Name, Project Idea, Brief Description, and Technology Stack).")
            return redirect('profile_settings')

        elif action == 'delete_history' and profile.role == 'STUDENT':
            hid = request.POST.get('history_id', '')
            if hid.isdigit():
                StudentProjectHistory.objects.filter(id=int(hid), student=request.user).delete()
                messages.info(request, "Project history entry removed.")
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
        'student_histories': request.user.project_histories.all() if profile.role == 'STUDENT' else [],
        'active_tab': 'profile_settings',
        'notifications': request.user.notifications.filter(is_read=False)[:6],
    })

# ==============================================================================
# STUDENT WORKSPACE — TEAM MEMBERSHIP, GUIDE REQUESTS & PROJECT HISTORY
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
    if group and not group.creator_id:
        first_member = group.students.first()
        if first_member:
            group.creator = first_member
            group.save(update_fields=['creator'])

    # Strictly display only Faculty Guides belonging to the student/team's department
    dept_guides = User.objects.filter(
        is_superuser=False,
        profile__department=dept,
        profile__role='GUIDE'
    ).select_related('profile') if dept else User.objects.none()

    # Include current user (creator) + unassigned students in the same department
    dept_students = User.objects.filter(
        is_superuser=False,
        profile__department=dept,
        profile__role='STUDENT'
    ).filter(
        Q(student_groups__isnull=True) | Q(id=request.user.id)
    ).select_related('profile').distinct() if dept else User.objects.none()

    if request.method == 'POST':
        action = request.POST.get('action')

        # 1. Create a New Team (Prevent self-addition & duplicate members; send Guide Request)
        if action == 'create_group' and not group:
            group_name = request.POST.get('group_name', '').strip()
            guide_id = request.POST.get('guide_id', '').strip()
            raw_teammate_ids = request.POST.getlist('teammate_ids')

            if not group_name:
                messages.error(request, "Project Group Name is required.")
                return redirect('student_dashboard')

            requested_guide_user = None
            if guide_id.isdigit():
                requested_guide_user = User.objects.filter(
                    id=int(guide_id),
                    is_superuser=False,
                    profile__department=dept,
                    profile__role='GUIDE'
                ).first()
            elif profile.preferred_guide and profile.preferred_guide.profile.department_id == (dept.id if dept else None):
                requested_guide_user = profile.preferred_guide

            unique_code = generate_join_code()
            new_group = ProjectGroup.objects.create(
                name=group_name,
                join_code=unique_code,
                department=dept,
                creator=request.user,
                guide=None,
                requested_guide=requested_guide_user,
                guide_status='PENDING' if requested_guide_user else 'NONE'
            )
            new_group.students.add(request.user)

            # Deduplicate teammate IDs & prevent creator from adding themselves twice
            seen_ids = {request.user.id}
            added_names = []
            for tid in raw_teammate_ids:
                if str(tid).isdigit():
                    uid = int(tid)
                    if uid == request.user.id:
                        continue
                    if uid in seen_ids:
                        continue
                    seen_ids.add(uid)
                    tm = User.objects.filter(
                        id=uid,
                        is_superuser=False,
                        profile__department=dept,
                        profile__role='STUDENT'
                    ).first()
                    if tm and not tm.student_groups.exists():
                        new_group.students.add(tm)
                        added_names.append(tm.get_full_name() or tm.username)
                        notify_users([tm], f"{request.user.get_full_name() or request.user.username} added you to project team '{new_group.name}'.")

            if requested_guide_user:
                notify_users(
                    [requested_guide_user],
                    f"Team '{new_group.name}' ({dept.name}) requested you as their Faculty Guide. Please accept or decline in your Guide Console."
                )

            request.session['play_success_sound'] = True
            guide_msg = f" Mentorship request sent to {requested_guide_user.get_full_name() or requested_guide_user.username}." if requested_guide_user else ""
            messages.success(request, f"Team '{new_group.name}' created! Share 5-character Join Code {new_group.join_code} with teammates.{guide_msg}")
            return redirect('student_dashboard')

        # 2. Join Existing Team via 5-Char Code (Prevent duplicates)
        elif action == 'join_group' and not group:
            raw_code = request.POST.get('join_code', '').strip().upper()
            if not re.match(r'^[A-Z0-9]{5}$', raw_code):
                messages.error(request, "Invalid Join Code format. Please enter a valid 5-character alphanumeric group code (e.g. A8K2P).")
                return redirect('student_dashboard')

            target_group = ProjectGroup.objects.filter(join_code=raw_code, department=dept).first()
            if not target_group:
                messages.error(request, f"No active team in {dept.name} matches the 5-character code '{raw_code}'.")
            elif target_group.students.filter(id=request.user.id).exists():
                messages.warning(request, f"You are already a member of '{target_group.name}'.")
            else:
                target_group.students.add(request.user)
                notify_users(target_group.students.exclude(id=request.user.id), f"{request.user.get_full_name() or request.user.username} joined {target_group.name}!")
                request.session['play_success_sound'] = True
                messages.success(request, f"Successfully joined '{target_group.name}'!")
            return redirect('student_dashboard')

        # 3. Invite / Add Eligible Classmate to Existing Team (Creator only, prevent duplicates & self)
        elif action == 'add_member_to_group' and group:
            if group.creator_id != request.user.id:
                messages.error(request, "Only the Team Creator can add or remove members.")
                return redirect('student_dashboard')
            raw_ids = request.POST.getlist('teammate_ids')
            added_count = 0
            for tid in set(raw_ids):
                if str(tid).isdigit():
                    uid = int(tid)
                    if uid == request.user.id or group.students.filter(id=uid).exists():
                        continue
                    tm = User.objects.filter(
                        id=uid,
                        is_superuser=False,
                        profile__department=dept,
                        profile__role='STUDENT'
                    ).first()
                    if tm and not tm.student_groups.exists():
                        group.students.add(tm)
                        added_count += 1
                        notify_users([tm], f"{request.user.get_full_name() or request.user.username} added you to team '{group.name}'.")
            if added_count > 0:
                request.session['play_success_sound'] = True
                messages.success(request, f"Added {added_count} classmate(s) to '{group.name}'.")
            else:
                messages.warning(request, "No new eligible classmates were selected or they are already in a team.")
            return redirect('student_dashboard')

        # 4. Team Creator Removes a Member (with confirmation & validation)
        elif action == 'remove_member' and group:
            if group.creator_id != request.user.id:
                messages.error(request, "Only the Team Creator is authorized to remove team members.")
                return redirect('student_dashboard')
            member_id = request.POST.get('member_id', '').strip()
            if not member_id.isdigit() or int(member_id) == request.user.id:
                messages.error(request, "Invalid member removal request. Use 'Leave Team' if you wish to leave.")
                return redirect('student_dashboard')

            target_member = group.students.filter(id=int(member_id)).first()
            if not target_member:
                messages.error(request, "Selected user is not a member of this team.")
            else:
                archive_group_to_student_history(target_member, group)
                group.students.remove(target_member)
                notify_users([target_member], f"You have been removed from project team '{group.name}' by the team creator.")
                request.session['play_success_sound'] = True
                messages.success(request, f"Removed {target_member.get_full_name() or target_member.username} from {group.name}.")
            return redirect('student_dashboard')

        # 5. Member Leaves Team (with confirmation, validation & history archiving)
        elif action == 'leave_group' and group:
            confirm_leave = request.POST.get('confirm_leave', 'yes')
            if confirm_leave != 'yes':
                return redirect('student_dashboard')

            group_name = group.name
            archive_group_to_student_history(request.user, group)
            group.students.remove(request.user)
            remaining = list(group.students.all())
            if remaining:
                if group.creator_id == request.user.id:
                    group.creator = remaining[0]
                    group.save(update_fields=['creator'])
                notify_users(remaining, f"{request.user.get_full_name() or request.user.username} left team '{group_name}'.")
            else:
                group.delete()

            request.session['play_success_sound'] = True
            messages.success(request, f"You have left team '{group_name}'. Your participation has been saved to your Student Project History.")
            return redirect('student_dashboard')

        # 6. Request a Faculty Guide from the Team's Department
        elif action == 'request_guide' and group:
            guide_id = request.POST.get('guide_id', '').strip()
            if not guide_id.isdigit():
                messages.error(request, "Please select a Faculty Guide from your department.")
                return redirect('student_dashboard')

            target_guide = User.objects.filter(
                id=int(guide_id),
                is_superuser=False,
                profile__department=dept,
                profile__role='GUIDE'
            ).first()
            if not target_guide:
                messages.error(request, "Selected guide does not belong to your department.")
                return redirect('student_dashboard')

            group.requested_guide = target_guide
            group.guide_status = 'PENDING'
            group.save(update_fields=['requested_guide', 'guide_status'])
            notify_users(
                [target_guide],
                f"Team '{group.name}' ({dept.name}) has requested you as their Faculty Guide. Please accept or decline in your Guide Console."
            )
            request.session['play_success_sound'] = True
            messages.success(request, f"Guide request sent to {target_guide.get_full_name() or target_guide.username}! They will be assigned once they accept.")
            return redirect('student_dashboard')

        # 7. Submit / Update Project Proposal (includes Technology Stack)
        elif action == 'submit_proposal' and group:
            title = request.POST.get('title', '').strip()
            domain = request.POST.get('domain', '').strip()
            tech_stack = request.POST.get('tech_stack', '').strip()
            abstract = request.POST.get('abstract', '').strip()
            report_file = request.FILES.get('report_file')

            if len(title) < 5 or not domain or not tech_stack or len(abstract.split()) < 6:
                messages.error(request, "Project Title, Technical Domain, Technology Stack, and a detailed Abstract (at least 6 words) are required.")
                return redirect('student_dashboard')

            if report_file and not validate_file_ext(report_file, ALLOWED_REPORT_EXT):
                messages.error(request, "Report file must be PDF, DOCX, PNG, or JPG.")
                return redirect('student_dashboard')

            sim_res = check_abstract_similarity(title, abstract, department=dept, exclude_group_id=group.id)
            proposal, _ = ProjectProposal.objects.get_or_create(group=group)
            proposal.title = title
            proposal.domain = domain
            proposal.tech_stack = tech_stack
            proposal.abstract = abstract
            proposal.similarity_score = sim_res['score']
            proposal.closest_match_title = sim_res['closest_match']
            proposal.status = 'PENDING'
            if report_file:
                proposal.report_file = report_file
            proposal.save()

            if group.guide:
                notify_users([group.guide], f"{group.name} submitted proposal '{title}' (Similarity: {sim_res['score']}%).")
            elif group.requested_guide:
                notify_users([group.requested_guide], f"{group.name} (pending your guide acceptance) prepared proposal '{title}'.")
            request.session['play_success_sound'] = True
            messages.success(request, f"Proposal saved! AI Similarity Score: {sim_res['score']}%.")
            return redirect('student_dashboard')

        # 8. Submit Weekly Log
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

        # 9. Add Previous Team / Project Idea to Student History directly from Dashboard
        elif action == 'add_history':
            team_name = request.POST.get('team_name', '').strip()
            project_idea = request.POST.get('project_idea', '').strip()
            brief_description = request.POST.get('brief_description', '').strip()
            tech_stack = request.POST.get('tech_stack', '').strip()
            if team_name and project_idea and brief_description and tech_stack:
                StudentProjectHistory.objects.create(
                    student=request.user,
                    team_name=team_name,
                    project_idea=project_idea,
                    brief_description=brief_description,
                    tech_stack=tech_stack
                )
                request.session['play_success_sound'] = True
                messages.success(request, f"Added '{project_idea}' to your Student Project History.")
            else:
                messages.error(request, "All history fields (Team Name, Project Idea, Brief Description, and Technology Stack) are required.")
            return redirect('student_dashboard')

        elif action == 'delete_history':
            hid = request.POST.get('history_id', '')
            if hid.isdigit():
                StudentProjectHistory.objects.filter(id=int(hid), student=request.user).delete()
                messages.info(request, "History entry removed.")
            return redirect('student_dashboard')

    proposal = getattr(group, 'proposal', None) if group else None
    logs = group.logs.all() if group else []
    viva = getattr(group, 'viva', None) if group else None
    next_week = (logs.count() + 1) if group else 1
    student_histories = request.user.project_histories.all()

    return render(request, 'student_dashboard.html', {
        'group': group,
        'proposal': proposal,
        'logs': logs,
        'viva': viva,
        'next_week': next_week,
        'dept_guides': dept_guides,
        'dept_students': dept_students,
        'student_histories': student_histories,
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
# FACULTY GUIDE WORKSPACE — GUIDE REQUEST ACCEPTANCE & MENTORING
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

        # Accept a Team's Guide Request -> officially assigns the guide
        if action == 'accept_guide_request':
            gid = request.POST.get('group_id')
            grp = get_object_or_404(ProjectGroup, id=gid, department=dept)
            grp.guide = request.user
            grp.requested_guide = None
            grp.guide_status = 'ACCEPTED'
            grp.save()
            notify_users(
                grp.students.all(),
                f"Faculty Guide {request.user.get_full_name() or request.user.username} accepted your guide request and is now assigned to '{grp.name}'!"
            )
            request.session['play_success_sound'] = True
            messages.success(request, f"You have accepted the request and are now assigned as the Faculty Guide for '{grp.name}'.")

        elif action == 'decline_guide_request':
            gid = request.POST.get('group_id')
            grp = get_object_or_404(ProjectGroup, id=gid, department=dept, requested_guide=request.user)
            grp.requested_guide = None
            grp.guide_status = 'DECLINED'
            grp.save()
            notify_users(
                grp.students.all(),
                f"Faculty Guide {request.user.get_full_name() or request.user.username} was unable to accept the guide request for '{grp.name}'. Please request another guide from {dept.name}."
            )
            messages.info(request, f"Declined guide request for '{grp.name}'.")

        elif action == 'claim_group':
            gid = request.POST.get('group_id')
            grp = get_object_or_404(ProjectGroup, id=gid, department=dept)
            grp.guide = request.user
            grp.requested_guide = None
            grp.guide_status = 'ACCEPTED'
            grp.save()
            notify_users(grp.students.all(), f"Guide {request.user.get_full_name() or request.user.username} accepted mentorship of {grp.name}.")
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
            notify_users(prop.group.students.all(), f"Guide {request.user.get_full_name() or request.user.username} {verb} your proposal '{prop.title}'.")
            request.session['play_success_sound'] = True
            messages.success(request, f"Saved review for {prop.group.name}.")

        elif action == 'verify_log':
            lid = request.POST.get('log_id')
            feedback = request.POST.get('guide_feedback', '').strip()
            log_item = get_object_or_404(WeeklyLog, id=lid, group__guide=request.user, group__department=dept)
            log_item.is_verified = True
            log_item.guide_feedback = feedback or "Verified & signed off by Project Guide."
            log_item.save()
            notify_users(log_item.group.students.all(), f"Week {log_item.week_number} log verified by {request.user.get_full_name() or request.user.username}.")
            request.session['play_success_sound'] = True
            messages.success(request, f"Verified Week {log_item.week_number} for {log_item.group.name}.")

        return redirect('guide_dashboard')

    my_groups = ProjectGroup.objects.filter(guide=request.user, department=dept).prefetch_related('students__profile', 'logs')
    pending_requests = ProjectGroup.objects.filter(
        department=dept,
        requested_guide=request.user,
        guide__isnull=True
    ).prefetch_related('students__profile')
    unassigned_groups = ProjectGroup.objects.filter(
        department=dept,
        guide__isnull=True
    ).exclude(requested_guide=request.user).prefetch_related('students__profile')
    registered_mentees = UserProfile.objects.filter(preferred_guide=request.user, department=dept, user__is_superuser=False).select_related('user')

    pending_proposals = ProjectProposal.objects.filter(group__guide=request.user, group__department=dept, status='PENDING').count()
    unverified_logs = WeeklyLog.objects.filter(group__guide=request.user, group__department=dept, is_verified=False).count()

    return render(request, 'guide_dashboard.html', {
        'my_groups': my_groups,
        'pending_requests': pending_requests,
        'unassigned_groups': unassigned_groups,
        'registered_mentees': registered_mentees,
        'pending_proposals': pending_proposals,
        'unverified_logs': unverified_logs,
        'active_tab': 'guide_dashboard',
        'notifications': request.user.notifications.filter(is_read=False)[:6],
    })

# ==============================================================================
# EXAMINER & HOD ANALYTICS PORTAL
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
# INSTITUTION ADMIN COMMAND CENTER — GUIDE ASSIGNMENT & GOVERNANCE
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

        elif action == 'assign_guide':
            gid = request.POST.get('group_id', '').strip()
            guide_id = request.POST.get('guide_id', '').strip()
            grp = get_object_or_404(ProjectGroup, id=gid)
            if admin_col and grp.department.college_id != admin_col.id:
                messages.error(request, "Unauthorized: You can only manage groups within your authorized College.")
                return redirect('admin_dashboard')

            if not guide_id.isdigit():
                grp.guide = None
                grp.requested_guide = None
                grp.guide_status = 'NONE'
                grp.save()
                messages.info(request, f"Cleared guide assignment for '{grp.name}'.")
                return redirect('admin_dashboard')

            guide_user = get_object_or_404(
                User,
                id=int(guide_id),
                is_superuser=False,
                profile__role='GUIDE',
                profile__department=grp.department
            )
            grp.guide = guide_user
            grp.requested_guide = None
            grp.guide_status = 'ACCEPTED'
            grp.save()
            notify_users(
                grp.students.all(),
                f"Admin assigned Faculty Guide {guide_user.get_full_name() or guide_user.username} to your project team '{grp.name}'."
            )
            notify_users(
                [guide_user],
                f"Admin assigned you as Faculty Guide for project team '{grp.name}' ({grp.department.name})."
            )
            request.session['play_success_sound'] = True
            messages.success(request, f"Assigned {guide_user.get_full_name() or guide_user.username} to team '{grp.name}'.")

        return redirect('admin_dashboard')

    dept_filter = request.GET.get('dept_id', '').strip()
    search_q = request.GET.get('q', '').strip().lower()

    all_universities = University.objects.filter(id=admin_uni.id) if admin_uni else University.objects.all()
    all_colleges = College.objects.filter(id=admin_col.id).select_related('university') if admin_col else College.objects.select_related('university').all()
    all_departments = Department.objects.filter(college=admin_col).select_related('college__university') if admin_col else Department.objects.select_related('college__university').all()

    guides_qs = UserProfile.objects.filter(role='GUIDE', user__is_superuser=False).select_related('user', 'department', 'college', 'university')
    students_qs = UserProfile.objects.filter(role='STUDENT', user__is_superuser=False).select_related('user', 'department', 'college', 'preferred_guide')
    groups_qs = ProjectGroup.objects.select_related('department__college', 'guide', 'requested_guide', 'creator').prefetch_related('students__profile')

    if admin_col:
        guides_qs = guides_qs.filter(college=admin_col)
        students_qs = students_qs.filter(college=admin_col)
        groups_qs = groups_qs.filter(department__college=admin_col)
    elif admin_uni:
        guides_qs = guides_qs.filter(university=admin_uni)
        students_qs = students_qs.filter(university=admin_uni)
        groups_qs = groups_qs.filter(department__college__university=admin_uni)

    # Keep a full department-scoped guide list for the group assignment dropdowns
    college_guides_all = list(guides_qs)

    if dept_filter.isdigit():
        guides_qs = guides_qs.filter(department_id=int(dept_filter))
        students_qs = students_qs.filter(department_id=int(dept_filter))
        groups_qs = groups_qs.filter(department_id=int(dept_filter))

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
        'college_guides_all': college_guides_all,
        'students_qs': students_qs,
        'groups_qs': groups_qs,
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
    writer.writerow(['Group Name', 'Join Code', 'Department', 'Students', 'Project Guide', 'Proposal Title', 'Technology Stack', 'Status', 'AI Similarity (%)', 'Verified Logs', 'Viva Score (/100)', 'Grade'])

    for g in groups:
        students_str = ", ".join([f"{s.get_full_name() or s.username} ({s.profile.identifier})" for s in g.students.filter(is_superuser=False)])
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
            prop.tech_stack if prop else "—",
            prop.get_status_display() if prop else "No Proposal",
            f"{prop.similarity_score}%" if prop else "0%",
            verified_logs,
            viva.total_score if viva else "Pending",
            viva.grade_badge if viva else "Pending"
        ])
    return response
