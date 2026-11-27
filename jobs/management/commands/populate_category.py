from typing import Any
from django.core.management.base import BaseCommand
from jobs.models import Category


class Command(BaseCommand):
  help = "Inserts predefined job categories into the database"

  def handle(self, *args: Any, **options: Any):
    categories = [
        "Software Development & Engineering",
        "Data Science & Analytics",
        "DevOps & Cloud Computing",
        "Quality Assurance & Testing",
        "UI/UX & Product Design",
        "Information Technology & Networking",
    ]

    for cat_name in categories:
      Category.objects.get_or_create(name=cat_name)

    self.stdout.write(
        self.style.SUCCESS("Successfully inserted all job categories!")
    )