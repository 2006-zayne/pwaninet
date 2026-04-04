from django import forms 
from django.contrib.auth.forms import UserCreationForm
from .models import User, Unit, Post, Year

class PwaniSignupForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('first_name', 'second_name', 'last_name', 'course', 'year')
        
        #  WE use HTMX into the Signup dropdowns HTMX is a form of Java script which is directly injected into the HTML.
        widgets = {
            'course': forms.Select(attrs={
                'hx-get': '/load-years/',      # The endpoint for filtering
                'hx-target': '#id_year',       # Targets the 'year' field's HTML ID
                'class': 'form-control'
            }),
            'year': forms.Select(attrs={
                'class': 'form-control'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # To start with an empty Year list
        self.fields['year'].queryset = Year.objects.none()

        # Update queryset if course data is present (for validation and HTMX)
        if 'course' in self.data:
            try:
                course_id = int(self.data.get('course'))
                self.fields['year'].queryset = Year.objects.filter(course_id=course_id).order_by('level')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.course:
            self.fields['year'].queryset = self.instance.course.years.all()


class PostForm(forms.ModelForm):
    # Unit field definition as a dropdown
    unit = forms.ModelChoiceField(
        queryset=Unit.objects.all(),
        empty_label="Select Unit.",
        widget=forms.Select(attrs={'class': 'form-control'}) # Standard Issue Styling
    )

    class Meta:
        model = Post
        fields = ['unit', 'content'] 

        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 5, 
                'cols': 40, 
                'placeholder': 'What is on your mind?',
                'class': 'form-control'
            }),
        }

    # Filter units based on the user's Course and Year
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None) # Extract the user from the view
        super().__init__(*args, **kwargs)
        if user:
            # MISSION: Restrict units to the user's specific deployment sector
            self.fields['unit'].queryset = Unit.objects.filter(
                course=user.course, 
                year=user.year
            )