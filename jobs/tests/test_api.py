from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from jobs.models import Application, Category, Job, Profile

User = get_user_model()


# ==============================================================================
# GROUP 1: API PERMISSIONS, OWNERSHIP & APPLICATION SCOPING (3 TESTS)
# Learning note: Verifies role-based access control (seeker vs employer),
# cross-employer ownership protection, and per-user application isolation.
# ==============================================================================
class JobPermissionsAndApplicationFlowTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.category, _ = Category.objects.get_or_create(name="Backend")

        self.seeker = User.objects.create_user(
            username="seeker_flow",
            email="seeker_flow@example.com",
            password="StrongPassword123!",
        )
        self.other_seeker = User.objects.create_user(
            username="other_seeker_flow",
            email="other_seeker_flow@example.com",
            password="StrongPassword123!",
        )
        self.employer = User.objects.create_user(
            username="employer_flow",
            email="employer_flow@example.com",
            password="StrongPassword123!",
        )
        self.other_employer = User.objects.create_user(
            username="other_employer_flow",
            email="other_employer_flow@example.com",
            password="StrongPassword123!",
        )

        Profile.objects.get_or_create(user=self.seeker, defaults={"role": "job_seeker"})
        Profile.objects.get_or_create(user=self.other_seeker, defaults={"role": "job_seeker"})
        Profile.objects.get_or_create(user=self.employer, defaults={"role": "employer"})
        Profile.objects.get_or_create(user=self.other_employer, defaults={"role": "employer"})

        self.job = Job.objects.create(
            employer=self.employer,
            title="Django REST Developer",
            company="Chennai Tech Labs",
            salary=900000,
            location="Chennai",
            description="Build REST APIs with Django and MySQL",
            category=self.category,
            is_active=True,
        )

    def test_seeker_cannot_create_job(self):
        self.client.force_authenticate(user=self.seeker)
        url = reverse("job-create-api")

        res = self.client.post(
            url,
            data={
                "title": "Unauthorized Job",
                "company": "Fake Corp",
                "salary": 500000,
                "location": "Chennai",
                "description": "Should be rejected",
                "category": self.category.id,
                "is_active": True,
            },
            format="json",
        )
        self.assertIn(
            res.status_code,
            (
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_403_FORBIDDEN,
                status.HTTP_405_METHOD_NOT_ALLOWED,
            ),
        )
        self.assertFalse(Job.objects.filter(title="Unauthorized Job").exists())

    def test_other_employer_cannot_modify_or_delete_job(self):
        self.client.force_authenticate(user=self.other_employer)
        patch_url = reverse("job-update-api", kwargs={"slug": self.job.slug})
        delete_url = reverse("job-delete-api", kwargs={"slug": self.job.slug})

        patch_res = self.client.patch(
            patch_url, data={"title": "Hijacked Title"}, format="json"
        )
        delete_res = self.client.delete(delete_url)

        self.assertIn(
            patch_res.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)
        )
        self.assertIn(
            delete_res.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)
        )
        self.job.refresh_from_db()
        self.assertEqual(self.job.title, "Django REST Developer")

    def test_my_applications_scoped_to_current_seeker(self):
        Application.objects.create(applicant=self.other_seeker, job=self.job)

        self.client.force_authenticate(user=self.seeker)
        apply_url = reverse("api_apply_job", kwargs={"slug": self.job.slug})
        apply_res = self.client.post(apply_url)
        self.assertEqual(apply_res.status_code, status.HTTP_201_CREATED)

        my_apps_url = reverse("api_my_applications")
        res = self.client.get(my_apps_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        items = res.data["results"] if isinstance(res.data, dict) else res.data
        self.assertEqual(len(items), 1)


# ==============================================================================
# GROUP 2: APPLICATION WORKFLOW, CLOSED JOBS & PROFILE UPLOAD (3 TESTS)
# Learning note: Tests inactive/closed job filtering, duplicate application
# prevention (UniqueConstraint + transaction.atomic), and multipart resume upload.
# ==============================================================================
class JobWorkflowAPITest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.category, _ = Category.objects.get_or_create(name="Backend")

        self.seeker = User.objects.create_user(
            username="seeker_test",
            email="seeker@example.com",
            password="StrongPassword123!",
        )
        self.employer = User.objects.create_user(
            username="employer_test",
            email="employer@example.com",
            password="StrongPassword123!",
        )

        Profile.objects.get_or_create(user=self.seeker, defaults={"role": "job_seeker"})
        Profile.objects.get_or_create(user=self.employer, defaults={"role": "employer"})

        self.active_job = Job.objects.create(
            employer=self.employer,
            title="Python Backend Engineer",
            company="Acme Corp",
            salary=800000,
            location="Chennai",
            description="Backend role using Django and MySQL",
            category=self.category,
            is_active=True,
        )
        self.closed_job = Job.objects.create(
            employer=self.employer,
            title="Senior Django Developer",
            company="Acme Corp",
            salary=1000000,
            location="Chennai",
            description="Closed role",
            category=self.category,
            is_active=False,
        )

    def test_closed_job_hidden_and_cannot_apply(self):
        self.client.force_authenticate(user=self.seeker)

        list_res = self.client.get(reverse("api_job_list"))
        self.assertEqual(list_res.status_code, status.HTTP_200_OK)
        items = list_res.data.get("results", list_res.data)
        slugs = [item["slug"] for item in items]
        self.assertNotIn(self.closed_job.slug, slugs)

        apply_res = self.client.post(
            reverse("api_apply_job", kwargs={"slug": self.closed_job.slug})
        )
        self.assertIn(
            apply_res.status_code,
            (status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN),
        )

    def test_duplicate_application_is_blocked(self):
        self.client.force_authenticate(user=self.seeker)
        url = reverse("api_apply_job", kwargs={"slug": self.active_job.slug})

        first = self.client.post(url)
        second = self.client.post(url)

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertIn(
            second.status_code,
            (status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT),
        )
        self.assertEqual(
            Application.objects.filter(applicant=self.seeker, job=self.active_job).count(),
            1,
        )

    def test_profile_patch_with_resume_upload(self):
        self.client.force_authenticate(user=self.seeker)
        resume = SimpleUploadedFile(
            "resume.txt", b"Python Backend Engineer", content_type="text/plain"
        )

        res = self.client.patch(
            reverse("api_profile"),
            data={
                "phone": "9876543210",
                "skills": "Python, Django, MySQL",
                "resume": resume,
            },
            format="multipart",
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["phone"], "9876543210")
        self.assertEqual(res.data["skills"], "Python, Django, MySQL")
        self.assertIsNotNone(res.data["resume"])


# ==============================================================================
# GROUP 3: JOB CRUD, FILTERING, ORDERING, PAGINATION & VALIDATION (26 TESTS)
# Learning note: Core CRUD + query params (location, salary range, search,
# ordering, pagination/page_size/invalid page) + serializer field validation.
# ==============================================================================
class JobAPITest(APITestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(username="testuser", password="password123")
        self.user.profile.role = "employer"
        self.user.profile.save()

        self.user_two = User.objects.create_user(
            username="testusertwo", password="password123"
        )
        self.user_two.profile.role = "employer"
        self.user_two.profile.save()

        self.jobseekeruser = User.objects.create_user(
            username="testjobseeker", password="password123"
        )
        self.jobseekeruser.profile.role = "job_seeker"
        self.jobseekeruser.profile.save()

        self.client.force_authenticate(user=self.user)

        self.category = Category.objects.create(
            name="Software Development & Engineering"
        )

        self.job = Job.objects.create(
            title="Test Python Developer",
            company="Test Company",
            salary=500000,
            location="Chennai",
            description="Backend developer",
            category=self.category,
            employer=self.user,
            is_active=True,
        )

        self.job_two = Job.objects.create(
            title="Second Employer Job",
            company="Another Company",
            salary=600000,
            location="Mumbai",
            description="Another employer's job",
            category=self.category,
            employer=self.user_two,
            is_active=True,
        )

    def test_joblist_filter(self):
        response = self.client.get("/api/jobs/?location=Chennai")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["location"], "Chennai")

    def test_joblist_salary_filter(self):
        response = self.client.get("/api/jobs/?min_salary=300000&max_salary=1600000")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for job in response.data["results"]:
            self.assertGreaterEqual(job["salary"], 300000)
            self.assertLessEqual(job["salary"], 1600000)

    def test_joblist_title_filter(self):
        response = self.client.get("/api/jobs/?search=Python")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["title"], "Test Python Developer")

    def test_joblist_company_filter(self):
        response = self.client.get("/api/jobs/?search=Test Company")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["title"], "Test Python Developer")

    def test_joblist_ordering(self):
        response = self.client.get("/api/jobs/?ordering=-salary")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        highest_salary_job = response.data["results"][0]
        self.assertEqual(highest_salary_job["salary"], 600000)

        second_salary_job = response.data["results"][1]
        self.assertEqual(second_salary_job["salary"], 500000)

    def test_joblist_pagination(self):
        response = self.client.get("/api/jobs/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 2)

    def test_joblist_custom_page_size(self):
        response = self.client.get("/api/jobs/?page_size=1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 1)

    def test_invalid_page_number_returns_404(self):
        response = self.client.get("/api/jobs/?page=9999")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_search_no_matching_job(self):
        response = self.client.get("/api/jobs/?search=NonExistentJobKeyword12345")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)

    def test_unauthenticated_user_cannot_create_job(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(
            "/api/jobs/create/",
            data={
                "title": "Anonymous Job",
                "company": "No Auth Corp",
                "salary": 400000,
                "location": "Chennai",
                "description": "Should fail",
                "category": self.category.id,
            },
            format="json",
        )
        self.assertIn(
            response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
        )

    def test_employer_cannot_modify_another_employer_job(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.put(
            f"/api/jobs/{self.job_two.slug}/update/",
            data={
                "title": "Malicious Takeover",
                "company": "Another Company",
                "salary": 600000,
                "location": "Mumbai",
                "description": "Attempting unauthorized edit",
                "category": self.category.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_missing_required_title_returns_400(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/jobs/create/",
            data={
                "company": "Test Company",
                "salary": 500000,
                "location": "Chennai",
                "description": "Missing title",
                "category": self.category.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("title", response.data)

    def test_negative_salary_returns_400(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/jobs/create/",
            data={
                "title": "Negative Salary Job",
                "company": "Test Company",
                "salary": -50000,
                "location": "Chennai",
                "description": "Should fail validation",
                "category": self.category.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("salary", response.data)

    def test_employer_b_delete_own_job(self):
        self.client.force_authenticate(user=self.user_two)
        response = self.client.delete(f"/api/jobs/{self.job_two.slug}/delete/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Job.objects.filter(pk=self.job_two.pk).exists())

    def test_employer_cannot_delete_other_employers_job(self):
        self.client.force_authenticate(user=self.user_two)
        response = self.client.delete(f"/api/jobs/{self.job.slug}/delete/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Job.objects.filter(pk=self.job.pk).exists())

    def test_employer_delete_own_job(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(f"/api/jobs/{self.job.slug}/delete/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Job.objects.filter(pk=self.job.pk).exists())

    def test_job_update_forbidden_employee(self):
        self.client.force_authenticate(user=self.user_two)
        response = self.client.put(
            f"/api/jobs/{self.job.slug}/update/",
            data={
                "title": "Unauthorized Job",
                "company": "Test Company",
                "salary": 500000,
                "location": "Chennai",
                "description": "Should fail",
                "category": self.category.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_job_create_jobseeker(self):
        self.client.force_authenticate(user=self.jobseekeruser)
        response = self.client.post(
            "/api/jobs/create/",
            data={
                "title": "Unauthenticate Job",
                "company": "Testing Company",
                "salary": 500000,
                "location": "Chennai",
                "description": "Should fail",
                "category": self.category.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_job_update_employee_b(self):
        self.client.force_authenticate(user=self.user_two)
        response = self.client.put(
            f"/api/jobs/{self.job_two.slug}/update/",
            data={
                "title": "Changed Second Employer Job",
                "company": "Test Company",
                "salary": 100000,
                "location": "mumbai",
                "description": "Should pass",
                "category": self.category.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.job_two.refresh_from_db()
        self.assertEqual(self.job_two.title, "Changed Second Employer Job")

    def test_job_update_for_employee_a(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.put(
            f"/api/jobs/{self.job.slug}/update/",
            data={
                "title": "Updated Employer A Job",
                "company": "Test Company",
                "salary": 500000,
                "location": "Chennai",
                "description": "Updated description",
                "category": self.category.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.job.refresh_from_db()
        self.assertEqual(self.job.title, "Updated Employer A Job")

    def test_job_put_api(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.put(
            f"/api/jobs/{self.job.slug}/update/",
            data={
                "title": "Tested Python Developer",
                "company": "Test Company",
                "salary": 600000,
                "location": "Chennai",
                "description": "Backend developer",
                "category": self.category.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.job.refresh_from_db()
        self.assertEqual(self.job.title, "Tested Python Developer")
        self.assertEqual(self.job.salary, 600000)

    def test_job_update_api(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            f"/api/jobs/{self.job.slug}/update/",
            data={"title": "Senior Python Developer", "salary": 800000},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.job.refresh_from_db()
        self.assertEqual(self.job.title, "Senior Python Developer")
        self.assertEqual(self.job.salary, 800000)

    def test_delete_api(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(f"/api/jobs/{self.job.slug}/delete/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Job.objects.filter(pk=self.job.pk).exists())

    def test_job_list_api(self):
        response = self.client.get("/api/jobs/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_job_create_api(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/jobs/create/",
            data={
                "title": "Test Python Developer",
                "company": "Test Company",
                "salary": "500000",
                "location": "Chennai",
                "description": "Backend developer",
                "category": self.category.id,
            },
            format="json",
        )
        data = response.data
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(data["title"], "Test Python Developer")
        self.assertEqual(Job.objects.count(), 3)

    def test_invalid_create_api(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/jobs/create/",
            data={
                "title": "Test Developer",
                "company": "Testing Company",
                "salary": "-300000",
                "location": "Chennai",
                "description": "test developer",
                "category": self.category.id,
            },
            format="json",
        )
        data = response.data
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Salary cannot be negative.", data["salary"])


# ==============================================================================
# GROUP 4: SERIALIZER READ-ONLY HARDENING & AUTH API TESTS
# Learning note: Ensures client payloads cannot override read_only fields like
# `employer` on Job or `role` on Profile, and checks registration/login flows.
# ==============================================================================
'''
class SerializerAndAuthHardeningAPITest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.category, _ = Category.objects.get_or_create(name="Backend")

        self.employer_a = User.objects.create_user(
            username="hardening_emp_a",
            email="hardening_emp_a@example.com",
            password="StrongPassword123!",
        )
        self.employer_b = User.objects.create_user(
            username="hardening_emp_b",
            email="hardening_emp_b@example.com",
            password="StrongPassword123!",
        )
        self.seeker = User.objects.create_user(
            username="hardening_seeker",
            email="hardening_seeker@example.com",
            password="StrongPassword123!",
        )

        self.employer_a.profile.role = "employer"
        self.employer_a.profile.save()
        self.employer_b.profile.role = "employer"
        self.employer_b.profile.save()
        self.seeker.profile.role = "job_seeker"
        self.seeker.profile.save()

        self.job = Job.objects.create(
            employer=self.employer_a,
            title="Hardened API Role",
            company="Chennai Cloud",
            salary=950000,
            location="Chennai",
            description="Ownership check role",
            category=self.category,
            is_active=True,
        )

    def test_employer_field_cannot_be_spoofed_on_create_or_update(self):
        self.client.force_authenticate(user=self.employer_a)

        create_res = self.client.post(
            reverse("job-create-api"),
            data={
                "title": "Spoofed Owner Job",
                "company": "Chennai Cloud",
                "salary": 700000,
                "location": "Chennai",
                "description": "Should belong to employer_a despite payload",
                "category": self.category.id,
                "employer": self.employer_b.id,
            },
            format="json",
        )
        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED)
        created_job = Job.objects.get(title="Spoofed Owner Job")
        self.assertEqual(created_job.employer, self.employer_a)

        patch_res = self.client.patch(
            reverse("job-update-api", kwargs={"slug": self.job.slug}),
            data={"employer": self.employer_b.id},
            format="json",
        )
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.job.refresh_from_db()
        self.assertEqual(self.job.employer, self.employer_a)

    def test_profile_role_cannot_be_escalated_via_api(self):
        self.client.force_authenticate(user=self.seeker)
        res = self.client.patch(
            reverse("api_profile"),
            data={"role": "employer", "bio": "Trying privilege escalation"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.seeker.profile.refresh_from_db()
        self.assertEqual(self.seeker.profile.role, "job_seeker")

    def test_register_validation_rejects_mismatched_passwords(self):
        # Update URL name below if your auth registration route uses a different name
        try:
            url = reverse("register-api")
        except Exception:
            self.skipTest("Update 'register-api' reverse name to match api_urls.py")

        res = self.client.post(
            url,
            data={
                "username": "new_dev_user",
                "email": "new_dev@example.com",
                "password": "StrongPassword123!",
                "password_confirm": "DifferentPassword123!",
                "role": "job_seeker",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username="new_dev_user").exists())
'''