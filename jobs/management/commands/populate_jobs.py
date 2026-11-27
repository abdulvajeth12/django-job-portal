import random  # You can keep this if you still need it elsewhere, but it's no longer needed for categories
from typing import Any
from django.core.management.base import BaseCommand
from jobs.models import Category, Job


class Command(BaseCommand):
  help = 'Inserts predefined jobs with correct, non-random categories'

  def handle(self, *args: Any, **options: Any):
    # Clear existing jobs to avoid duplicates
    Job.objects.all().delete()

    # Define jobs data where each job is explicitly tied to a category name
    jobs_data = [


        {
            "title": "Python Developer",
            "company": "TechCorp India",
            "salary": 1200000,
            "location": "Bengaluru",
            "description": (
                "Looking for a skilled Django developer to build scalable APIs."
            ),
            "category_name": "Software Development & Engineering",
        },
        {
            "title": "Frontend Engineer",
            "company": "WebSolutions",
            "salary": 800000,
            "location": "Mumbai",
            "description": (
                "React and Tailwind CSS expertise required for building modern"
                " user interfaces."
            ),
            "category_name": "Software Development & Engineering",
        },
        {
            "title": "Data Analyst",
            "company": "DataMinds",
            "salary": 1000000,
            "location": "Pune",
            "description": (
                "SQL and Python pandas experience needed for deep financial"
                " data analysis."
            ),
            "category_name": "Data Science & Analytics",
        },
        {
            "title": "Backend Engineer",
            "company": "CloudScale Systems",
            "salary": 1500000,
            "location": "Hyderabad",
            "description": (
                "Design and maintain high-performance cloud infrastructure using"
                " AWS and Docker."
            ),
            "category_name": "Software Development & Engineering",
        },
        {
            "title": "Full Stack Developer",
            "company": "InnoTech Labs",
            "salary": 1350000,
            "location": "Chennai",
            "description": (
                "Develop end-to-end features using Python Django on the"
                " backend and JavaScript on the front."
            ),
            "category_name": "Software Development & Engineering",
        },
        {
            "title": "DevOps Engineer",
            "company": "NextGen Softwares",
            "salary": 1600000,
            "location": "Delhi",
            "description": (
                "Manage CI/CD pipelines, container orchestration, and server"
                " deployments."
            ),
            "category_name": "DevOps & Cloud Computing",
        },

    {
        "title": "Python Backend Developer",
        "company": "Tech Solutions",
        "salary": 600000,
        "location": "Chennai",
        "description": "Develop backend applications using Python and Django.",
        "category_name": "Software Development & Engineering",
    },
    {
        "title": "Junior Python Developer",
        "company": "CodeWorks",
        "salary": 450000,
        "location": "Bengaluru",
        "description": "Build APIs using Python and Flask.",
        "category_name": "Software Development & Engineering",
    },
    {
        "title": "Python Django Developer",
        "company": "WebTech",
        "salary": 500000,
        "location": "Coimbatore",
        "description": "Develop web applications using Django.",
        "category_name": "Software Development & Engineering",
    },
    {
        "title": "Senior Python Engineer",
        "company": "Innovate Systems",
        "salary": 900000,
        "location": "Hyderabad",
        "description": "Work on scalable Python backend systems.",
        "category_name": "Software Development & Engineering",
    },
    {
        "title": "Python API Developer",
        "company": "DevHub",
        "salary": 550000,
        "location": "Chennai",
        "description": "Develop and maintain REST APIs using Python.",
        "category_name": "Software Development & Engineering",
    },

      

    ]

    for data in jobs_data:
      # Fetch the specific category object from the database using its name
      category_obj = Category.objects.get(name=data["category_name"])

      # Create the job and link it to the correct category
      Job.objects.create(
          title=data["title"],
          company=data["company"],
          salary=data["salary"],
          location=data["location"],
          description=data["description"],
          category=category_obj,
      )

    self.stdout.write(
        self.style.SUCCESS("Successfully inserted jobs with correct categories!")
    )