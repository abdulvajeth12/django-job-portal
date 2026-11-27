from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import HttpResponseBadRequest
from .add_job_form import AddJobForm
from .forms import UserProfileForm
from .models import Application, Category, Job, Profile
from .notifications import send_application_status_email
from .pagination import JobPagination
from .permissions import IsEmployer, IsJobSeeker
from .serializers import ApplicationSerializer, JobSerializer, ProfileSerializer, RegisterSerializer
from django.db import IntegrityError, transaction
from django.urls import reverse


def _get_or_create_profile(user):
    if not user or not user.is_authenticated:
        return None
    profile, _ = Profile.objects.get_or_create(user=user)
    return profile


def _is_employer(user):
    profile = _get_or_create_profile(user)
    return bool(profile and profile.role == 'employer')


def _is_job_seeker(user):
    profile = _get_or_create_profile(user)
    return bool(profile and profile.role == 'job_seeker')


# --- HTML Views ---

def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        role = request.POST.get('role', 'job_seeker')

        if role not in ['job_seeker', 'employer']:
            role = 'job_seeker'

        if form.is_valid():
            user = form.save()
            profile = _get_or_create_profile(user)
            if profile is not None:
                profile.role = role
                profile.save(update_fields=['role'])

            login(request, user)
            if role == 'employer':
                return redirect('employer_dashboard')
            return redirect('jobs_list')
    else:
        form = UserCreationForm()

    return render(request, 'register.html', {'form': form})


def user_login(view_request):
    if view_request.method == 'POST':
        form = AuthenticationForm(view_request, data=view_request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(view_request, user)
                profile = _get_or_create_profile(user)
                if profile and profile.role == 'employer':
                    return redirect('employer_dashboard')
                return redirect('jobs_list')
    else:
        form = AuthenticationForm()

    return render(view_request, 'login.html', {'form': form})


@require_POST
def user_logout(view_request):
    logout(view_request)
    return redirect('user_login')


def jobs_list(request):
    query = request.GET.get("q", "").strip()
    category_id = request.GET.get("category", "").strip()
    min_salary = request.GET.get("min_salary", "").strip()
    max_salary = request.GET.get("max_salary", "").strip()

    jobs = Job.objects.filter(is_active=True).order_by('id')

    if query:
        jobs = jobs.filter(Q(title__icontains=query) | Q(company__icontains=query))

    if category_id.isdigit() and Category.objects.filter(id=int(category_id)).exists():
        jobs = jobs.filter(category_id=int(category_id))
    else:
        category_id = ""

    min_salary_value = None
    max_salary_value = None

    if min_salary:
        try:
            min_salary_value = float(min_salary)
            if min_salary_value < 0:
                min_salary_value = None
                min_salary = ""
        except ValueError:
            min_salary = ""

    if max_salary:
        try:
            max_salary_value = float(max_salary)
            if max_salary_value < 0:
                max_salary_value = None
                max_salary = ""
        except ValueError:
            max_salary = ""

    if min_salary_value is not None:
        jobs = jobs.filter(salary__gte=min_salary_value)

    if max_salary_value is not None:
        jobs = jobs.filter(salary__lte=max_salary_value)

    categories_data = [
        {
            "id": cat.id,
            "name": cat.name,
            "is_selected": str(cat.id) == category_id,
        }
        for cat in Category.objects.all()
    ]

    paginator = Paginator(jobs, 5)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "query": query,
        "categories": categories_data,
        "selected_category": category_id,
        "min_salary": min_salary,
        "max_salary": max_salary,
        "page_obj": page_obj,
    }
    return render(request, "jobs_list.html", context)


def job_details(request, slug):
    job = get_object_or_404(Job, slug=slug)
    return render(request, "job_details.html", {"job": job})


@login_required
def add_job(request):
    if not _is_employer(request.user):
        raise PermissionDenied("Access restricted to employers.")

    if request.method == "POST":
        form = AddJobForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            Job.objects.create(
                employer=request.user,
                title=data["title"],
                company=data["company"],
                salary=data["salary"],
                location=data["location"],
                description=data["description"],
                category=data["category"],
            )
            return redirect("employer_dashboard")
    else:
        form = AddJobForm()

    return render(request, "add_job.html", {"form": form})


@login_required
def edit_job(request, slug):
    job = get_object_or_404(Job, slug=slug, employer=request.user)

    if request.method == "POST":
        form = AddJobForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            job.title = data["title"]
            job.company = data["company"]
            job.salary = data["salary"]
            job.location = data["location"]
            job.description = data["description"]
            job.category = data["category"]
            job.save()
            return redirect("employer_dashboard")
    else:
        form = AddJobForm(initial={
            "title": job.title,
            "company": job.company,
            "salary": job.salary,
            "location": job.location,
            "description": job.description,
            "category": job.category,
        })

    return render(request, "edit_job.html", {"form": form, "job": job})


@login_required
def delete_job(request, slug):
    job = get_object_or_404(Job, slug=slug, employer=request.user)

    if request.method == "POST":
        job.delete()
        return redirect("employer_dashboard")

    return render(request, "delete_job.html", {"job": job})


@login_required
@require_POST
def toggle_job_status(request, slug):
    job = get_object_or_404(Job, slug=slug, employer=request.user)
    job.is_active = not job.is_active
    job.save(update_fields=["is_active"])
    return redirect("employer_dashboard")


@login_required
def employer_dashboard(request):
    if not _is_employer(request.user):
        raise PermissionDenied("Access restricted to employers.")

    jobs = Job.objects.filter(employer=request.user).order_by('-created_at')
    return render(request, 'employer_dashboard.html', {'jobs': jobs})


@login_required
def job_applicants(request, slug):
    job = get_object_or_404(Job, slug=slug)

    if not _is_employer(request.user):
        raise PermissionDenied("Access restricted to employers.")

    if job.employer != request.user:
        raise PermissionDenied("You do not have permission to view applicants for this job.")

    applications = (
        Application.objects.filter(job=job)
        .select_related('applicant', 'applicant__profile')
        .order_by('-applied_at')
    )

    if request.method == 'POST':
        app_id = request.POST.get('application_id')
        new_status = request.POST.get('status')
        valid_statuses = {choice[0] for choice in Application.STATUS_CHOICES}

        if new_status in valid_statuses:
            application = get_object_or_404(Application, id=app_id, job=job)
            old_status = application.status

            if old_status != new_status:
                with transaction.atomic():
                    application.status = new_status
                    application.save(update_fields=['status'])
                    transaction.on_commit(
                        lambda app=application: send_application_status_email(app)
                    )
                messages.success(
                    request,
                    f"Marked {application.applicant.username}'s application as {application.get_status_display()}."
                )

        return redirect('job_applicants', slug=job.slug)

    return render(
        request,
        'job_applicants.html',
        {'job': job, 'applications': applications},
    )


@login_required
def apply_job(request, slug):
    if not _is_job_seeker(request.user):
        raise PermissionDenied("Only job seekers can apply for jobs.")

    job = get_object_or_404(Job, slug=slug)
    if not job.is_active:
        raise PermissionDenied("This job is closed.")

    just_applied = request.GET.get("applied") == "1"
    already_applied = (
        not just_applied
        and Application.objects.filter(applicant=request.user, job=job).exists()
    )

    if request.method == "POST":
        if Application.objects.filter(applicant=request.user, job=job).exists():
            return render(
                request,
                "apply_job.html",
                {"job": job, "already_applied": True, "just_applied": False},
                status=400,
            )

        try:
            with transaction.atomic():
                Application.objects.create(applicant=request.user, job=job)
        except IntegrityError:
            return render(
                request,
                "apply_job.html",
                {"job": job, "already_applied": True, "just_applied": False},
                status=400,
            )

        return redirect(f"{reverse('apply_job', kwargs={'slug': job.slug})}?applied=1")

    return render(
        request,
        "apply_job.html",
        {
            "job": job,
            "already_applied": already_applied,
            "just_applied": just_applied,
        },
    )

@login_required
def my_applications(request):
    if not _is_job_seeker(request.user):
        raise PermissionDenied("Access restricted to job seekers.")

    applications = Application.objects.filter(applicant=request.user).order_by('-applied_at')
    return render(request, 'my_applications.html', {'applications': applications})


@login_required
def profile_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('profile_view')
    else:
        form = UserProfileForm(instance=profile)

    return render(request, 'profile.html', {'form': form, 'profile': profile})


# --- DRF API Views ---

@api_view(['POST'])
def register_api(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response(
            {'message': 'User registered successfully!', 'user': user.username, 'email': user.email},
            status=status.HTTP_201_CREATED,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def login_api(request):
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response(
            {"error": "Both username and password are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = authenticate(username=username, password=password)
    if user is not None:
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"message": "Login successful", "token": token.key}, status=status.HTTP_200_OK)

    return Response(
        {"error": "Invalid username or password."},
        status=status.HTTP_401_UNAUTHORIZED,
    )


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def job_list_api(request):
    if request.method == 'GET':
        jobs = Job.objects.filter(is_active=True)

        search_query = request.query_params.get('search')
        location_query = request.query_params.get('location')
        min_salary = request.query_params.get('min_salary')
        max_salary = request.query_params.get('max_salary')
        ordering = request.query_params.get('ordering')

        if search_query:
            jobs = jobs.filter(
                Q(title__icontains=search_query)
                | Q(company__icontains=search_query)
                | Q(location__icontains=search_query)
            )

        if location_query:
            jobs = jobs.filter(location__icontains=location_query)

        if min_salary:
            try:
                min_salary = int(min_salary)
                if min_salary < 0:
                    raise ValueError
                jobs = jobs.filter(salary__gte=min_salary)
            except ValueError:
                return Response(
                    {"error": "Invalid minimum salary. Must be a valid positive integer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if max_salary:
            try:
                max_salary = int(max_salary)
                if max_salary < 0:
                    raise ValueError
                jobs = jobs.filter(salary__lte=max_salary)
            except ValueError:
                return Response(
                    {"error": "Invalid maximum salary. Must be a valid positive integer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        allowed_ordering = ['salary', '-salary', 'created_at', '-created_at', 'title', '-title']
        if ordering:
            if ordering in allowed_ordering:
                jobs = jobs.order_by(ordering)
            else:
                return Response(
                    {"error": "Invalid ordering field."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            jobs = jobs.order_by('-created_at')

        paginator = JobPagination()
        page = paginator.paginate_queryset(jobs, request)
        if page is not None:
            serializer = JobSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = JobSerializer(jobs, many=True)
        return Response(serializer.data)

    if not IsEmployer().has_permission(request, None):
        return Response(
            {"detail": "Only authenticated employers can post jobs."},
            status=status.HTTP_403_FORBIDDEN,
        )

    serializer = JobSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(employer=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def job_detail_api(request, slug):
    job = get_object_or_404(Job, slug=slug)
    serializer = JobSerializer(job)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsEmployer])
def job_create_api(request):
    serializer = JobSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(employer=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated, IsEmployer])
def job_update_api(request, slug):
    job = get_object_or_404(Job, slug=slug)
    if job.employer != request.user:
        return Response(
            {"detail": "You do not have permission to edit this job."},
            status=status.HTTP_403_FORBIDDEN,
        )

    partial = request.method == 'PATCH'
    serializer = JobSerializer(job, data=request.data, partial=partial)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsEmployer])
def job_delete_api(request, slug):
    job = get_object_or_404(Job, slug=slug)
    if job.employer != request.user:
        return Response(
            {"detail": "You do not have permission to delete this job."},
            status=status.HTTP_403_FORBIDDEN,
        )

    job.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def profile_api(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == 'GET':
        serializer = ProfileSerializer(profile)
        return Response(serializer.data)

    serializer = ProfileSerializer(profile, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(["POST"])
@permission_classes([IsJobSeeker])
def apply_job_api(request, slug):
    job = get_object_or_404(Job, slug=slug)

    if not job.is_active:
        return Response(
            {"detail": "This job posting is closed and no longer accepting applications."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        with transaction.atomic():
            application = Application.objects.create(applicant=request.user, job=job)
    except IntegrityError:
        return Response(
            {"detail": "You have already applied for this job."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer = ApplicationSerializer(application, context={"request": request})
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsJobSeeker])
def my_applications_api(request):
    applications = (
        Application.objects.filter(applicant=request.user)
        .select_related('job')
        .order_by('-applied_at')
    )
    serializer = ApplicationSerializer(applications, many=True)
    return Response(serializer.data)