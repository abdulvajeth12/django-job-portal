from django.db import models
from django.utils.text import slugify
from django.conf import settings

# Create your models here.

#category
class Category(models.Model):
    name = models.CharField(max_length=100,blank=True)

    def __str__(self):
        return self.name


class Job(models.Model):

    employer = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='posted_jobs',null=True,blank=True)
    title = models.CharField(max_length=100)
    company = models.CharField(max_length=100)
    salary = models.IntegerField()
    location = models.CharField(max_length=100)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(default="", blank=True, unique = True)
    category = models.ForeignKey(Category,default=1,on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_string = f"{self.title} {self.company} {self.location}"
            base_slug = slugify(base_string) or "job"

            slug = base_slug
            counter = 1

            while Job.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug

        super().save(*args, **kwargs)
        
    def __str__(self):
        return self.title

class About(models.Model):
    content = models.TextField()

# jobs/models.py
class Application(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
    ]

    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="applications")
    job = models.ForeignKey(
        Job, on_delete=models.CASCADE, related_name="applications")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending")
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Database-level guarantee that a user cannot apply to the same job twice
        constraints = [
            models.UniqueConstraint(fields=['applicant', 'job'], name='unique_job_application')
        ]

    def __str__(self):
        return f"{self.applicant.username} - {self.job.title}"



# (Keep your existing Category, Job, About, Application models...)

class Profile(models.Model):
    ROLE_CHOICES = [
        ('job_seeker', 'Job Seeker'),
        ('employer', 'Employer'),
        ('admin', 'Admin'),
    ]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(choices=ROLE_CHOICES, default='job_seeker', max_length=20)
    
    # New professional fields for Job Seekers
    phone = models.CharField(max_length=15, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    skills = models.CharField(max_length=255, blank=True, null=True, help_text="Comma-separated skills e.g. Python, Django, MySQL")
    resume = models.FileField(upload_to='resumes/', blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"