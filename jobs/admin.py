from django.contrib import admin
from .models import Job, Category, About, Application

# Register your models here.
admin.site.register(Job)
admin.site.register(Category)
admin.site.register(About)
admin.site.register(Application)   