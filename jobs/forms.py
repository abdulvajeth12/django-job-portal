from django import forms
from .models import Profile

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['phone', 'bio', 'skills', 'resume']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Tell employers about your background...'}),
            'skills': forms.TextInput(attrs={'placeholder': 'Python, Django, MySQL, REST APIs'}),
        }