from django import forms
from .models import Category


class AddJobForm(forms.Form):
  title = forms.CharField(max_length=100, required=True)
  company = forms.CharField(max_length=100, required=True)
  salary = forms.IntegerField(required=True)
  location = forms.CharField(max_length=100, required=True)
  description = forms.CharField(widget=forms.Textarea, required=True)

  # This dynamically populates a dropdown list from your Category table
  category = forms.ModelChoiceField(
      queryset=Category.objects.all(),empty_label="Select a Category",required=True)