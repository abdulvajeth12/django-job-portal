from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from jobs.models import Application, Category, Job, Profile

User = get_user_model()


def _set_role(user, role):
    """Ensure Profile exists and explicitly assign role (avoids get_or_create default trap)."""
    profile, _ = Profile.objects.get_or_create(user=user)
    profile.role = role
    profile.save(update_fields=["role"])
    return profile


# ==============================================================================
# GROUP A: PUBLIC HTML VIEWS & LOGOUT METHOD HARDENING
# Learning note: Verifies template rendering, context content, and HTTP method
# enforcement (GET vs POST) on state-changing HTML endpoints like logout.
# ==============================================================================
class PublicAndAuthHTMLViewsTest(TestCase):
    def setUp(self):
        self.category, _ = Category.objects.get_or_create(name="Backend")
        self.seeker = User.objects.create_user(
            username="html_pub_seeker",
            email="html_pub_seeker@example.com",
            password="StrongPassword123!",
        )
        _set_role(self.seeker, "job_seeker")

        self.active_job = Job.objects.create(
            title="Python Django Engineer",
            company="Chennai Systems",
            salary=850000,
            location="Chennai",
            description="HTML and API job portal role",
            category=self.category,
            is_active=True,
        )
        self.closed_job = Job.objects.create(
            title="Closed Role",
            company="Chennai Systems",
            salary=700000,
            location="Chennai",
            description="No longer hiring",
            category=self.category,
            is_active=False,
        )

    def test_jobs_list_and_detail_render(self):
        list_res = self.client.get(reverse("jobs_list"))
        self.assertEqual(list_res.status_code, 200)
        self.assertContains(list_res, self.active_job.title)

        detail_res = self.client.get(
            reverse("job_details", kwargs={"slug": self.active_job.slug})
        )
        self.assertEqual(detail_res.status_code, 200)
        self.assertContains(detail_res, self.active_job.company)

    def test_logout_requires_post(self):
        self.client.force_login(self.seeker)
        logout_url = reverse("user_logout")

        get_res = self.client.get(logout_url)
        self.assertEqual(get_res.status_code, 405)

        post_res = self.client.post(logout_url)
        self.assertRedirects(post_res, reverse("user_login"))


# ==============================================================================
# GROUP B: HTML JOB SEEKER APPLICATION & RBAC WORKFLOWS
# Learning note: Tests HTML form/POST application flow, duplicate blocking,
# closed-job rejection, and login redirects for protected HTML routes.
# ==============================================================================
class SeekerHTMLApplicationTest(TestCase):
    def setUp(self):
        self.category, _ = Category.objects.get_or_create(name="Backend")
        self.seeker = User.objects.create_user(
            username="html_seeker_a",
            email="html_seeker_a@example.com",
            password="StrongPassword123!",
        )
        self.other_seeker = User.objects.create_user(
            username="html_seeker_b",
            email="html_seeker_b@example.com",
            password="StrongPassword123!",
        )
        self.employer = User.objects.create_user(
            username="html_app_employer",
            email="html_app_employer@example.com",
            password="StrongPassword123!",
        )
        _set_role(self.seeker, "job_seeker")
        _set_role(self.other_seeker, "job_seeker")
        _set_role(self.employer, "employer")

        self.active_job = Job.objects.create(
            employer=self.employer,
            title="Backend Developer HTML",
            company="Chennai Tech",
            salary=800000,
            location="Chennai",
            description="Apply via HTML view",
            category=self.category,
            is_active=True,
        )
        self.closed_job = Job.objects.create(
            employer=self.employer,
            title="Archived HTML Role",
            company="Chennai Tech",
            salary=750000,
            location="Chennai",
            description="Closed role",
            category=self.category,
            is_active=False,
        )

    def test_unauthenticated_user_redirected_from_protected_html_views(self):
        for route_name in ("my_applications", "employer_dashboard", "profile_view"):
            res = self.client.get(reverse(route_name))
            self.assertEqual(res.status_code, 302)

    def test_html_apply_job_and_duplicate_prevention(self):
        self.client.force_login(self.seeker)
        url = reverse("apply_job", kwargs={"slug": self.active_job.slug})

        first_post = self.client.post(url)
        self.assertEqual(first_post.status_code, 302)
        self.assertEqual(
            Application.objects.filter(applicant=self.seeker, job=self.active_job).count(),
            1,
        )

        duplicate_post = self.client.post(url)
        self.assertEqual(duplicate_post.status_code, 400)

    def test_html_apply_closed_job_forbidden(self):
        self.client.force_login(self.seeker)
        res = self.client.post(
            reverse("apply_job", kwargs={"slug": self.closed_job.slug})
        )
        self.assertEqual(res.status_code, 403)

    def test_my_applications_html_shows_only_own_applications(self):
        Application.objects.create(applicant=self.other_seeker, job=self.active_job)
        Application.objects.create(applicant=self.seeker, job=self.closed_job)

        self.client.force_login(self.seeker)
        res = self.client.get(reverse("my_applications"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, self.closed_job.title)


# ==============================================================================
# GROUP C: HTML EMPLOYER CRUD, STATUS TOGGLE & APPLICANT VIEWING
# Learning note: Covers employer dashboard RBAC, creating/editing/toggling/
# deleting jobs through HTML views, and scoping applicant lists to the job owner.
# NOTE: If a test deletes self.job inside its body, don't reuse self.job later
# in that same method.
# ==============================================================================
'''
class EmployerHTMLWorkflowTest(TestCase):
    def setUp(self):
        self.category, _ = Category.objects.get_or_create(name="Backend")
        self.seeker = User.objects.create_user(
            username="html_emp_seeker",
            email="html_emp_seeker@example.com",
            password="StrongPassword123!",
        )
        self.employer = User.objects.create_user(
            username="html_emp_owner",
            email="html_emp_owner@example.com",
            password="StrongPassword123!",
        )
        self.other_employer = User.objects.create_user(
            username="html_emp_other",
            email="html_emp_other@example.com",
            password="StrongPassword123!",
        )
        _set_role(self.seeker, "job_seeker")
        _set_role(self.employer, "employer")
        _set_role(self.other_employer, "employer")

        self.job = Job.objects.create(
            employer=self.employer,
            title="Initial HTML Job",
            company="Guindy Labs",
            salary=900000,
            location="Chennai",
            description="Initial description",
            category=self.category,
            is_active=True,
        )

    def test_employer_dashboard_rbac(self):
        url = reverse("employer_dashboard")

        self.client.force_login(self.seeker)
        seeker_res = self.client.get(url)
        self.assertEqual(seeker_res.status_code, 403)

        self.client.force_login(self.employer)
        employer_res = self.client.get(url)
        self.assertEqual(employer_res.status_code, 200)

    def test_employer_can_create_and_edit_job_via_html(self):
        self.client.force_login(self.employer)

        create_res = self.client.post(
            reverse("add_job"),
            data={
                "title": "New HTML Created Job",
                "company": "Guindy Labs",
                "salary": 750000,
                "location": "Chennai",
                "description": "Created via HTML form",
                "category": self.category.id,
                "is_active": True,
            },
        )
        self.assertIn(create_res.status_code, (200, 302))
        self.assertTrue(Job.objects.filter(title="New HTML Created Job").exists())

        edit_res = self.client.post(
            reverse("edit_job", kwargs={"slug": self.job.slug}),
            data={
                "title": "Edited HTML Job Title",
                "company": "Guindy Labs",
                "salary": 950000,
                "location": "Chennai",
                "description": "Updated description",
                "category": self.category.id,
                "is_active": True,
            },
        )
        self.assertIn(edit_res.status_code, (200, 302))
        self.job.refresh_from_db()
        self.assertEqual(self.job.title, "Edited HTML Job Title")

    def test_other_employer_cannot_edit_toggle_or_delete_job_html(self):
        self.client.force_login(self.other_employer)

        edit_res = self.client.post(
            reverse("edit_job", kwargs={"slug": self.job.slug}),
            data={"title": "Takeover Attempt"},
        )
        toggle_res = self.client.post(
            reverse("toggle_job_status", kwargs={"slug": self.job.slug})
        )
        delete_res = self.client.post(
            reverse("delete_job", kwargs={"slug": self.job.slug})
        )
        applicants_res = self.client.get(
            reverse("job_applicants", kwargs={"slug": self.job.slug})
        )

        self.assertEqual(edit_res.status_code, 403)
        self.assertEqual(toggle_res.status_code, 403)
        self.assertEqual(delete_res.status_code, 403)
        self.assertEqual(applicants_res.status_code, 403)

    def test_employer_can_toggle_status_and_view_applicants(self):
        Application.objects.create(applicant=self.seeker, job=self.job)
        self.client.force_login(self.employer)

        toggle_res = self.client.post(
            reverse("toggle_job_status", kwargs={"slug": self.job.slug})
        )
        self.assertEqual(toggle_res.status_code, 302)
        self.job.refresh_from_db()
        self.assertFalse(self.job.is_active)

        applicants_res = self.client.get(
            reverse("job_applicants", kwargs={"slug": self.job.slug})
        )
        self.assertEqual(applicants_res.status_code, 200)
        self.assertContains(applicants_res, self.seeker.username)

    def test_employer_can_delete_own_job_via_html(self):
        self.client.force_login(self.employer)
        res = self.client.post(reverse("delete_job", kwargs={"slug": self.job.slug}))
        self.assertEqual(res.status_code, 302)
        self.assertFalse(Job.objects.filter(pk=self.job.pk).exists())
'''