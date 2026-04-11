from django import forms 
from django.contrib.auth.forms import UserCreationForm
from .models import User, Unit, Post, Year ,Groups

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
        required=False,
        empty_label="Select Unit.",
        widget=forms.Select(attrs={'class': 'form-control'}) # Standard Issue Styling
    )

    class Meta:
        model = Post
        fields = ['unit', 'content' , 'image' , 'video' , 'docs' , 'gradient_class'] 

        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 5, 
                'cols': 40, 
                'placeholder': 'What is on your mind?',
                'class': 'form-control'
            }),
            'gradient_class': forms.Select(attrs={'class': 'form-select'}),
        }

    # Filter units based on the user's Course and Year
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None) # Extract the user from the view
        super().__init__(*args, **kwargs)
        if user:
            # Restrict units to the user's specific deployment sector
            self.fields['unit'].queryset = Unit.objects.filter(
                course=user.course, 
                year=user.year
            )

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['profile_pic' , 'bio']#The students will only be allowed to edit the profile pic bio and other fields if possible maybe nicknames but we will figure out that later.
        widgets = {
            'bio' : forms.Textarea(attrs={'class': 'form-control', 'rows':3,'placeholder':'Write about yourself...'}),
        }

    def __init__(self, *args, **kwargs):
        super(ProfileUpdateForm, self).__init__(*args, **kwargs)
        # THis ensure the file input is visible
        self.fields['profile_pic'].widget.attrs.update({'class': 'form-control-file'})


class GroupForm(forms.ModelForm):
    class Meta:
        model = Groups
        # We only want users to fill in these specific fields
        fields = ['name', 'description', 'group_pic']
        
        # Adding Bootstrap classes so the form looks sharp on your ProBook
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control rounded-pill', 'placeholder': 'Squad Name'}),
            'description': forms.Textarea(attrs={'class': 'form-control rounded-4', 'rows': 3, 'placeholder': 'What is this squad about?'}),
            'group_pic': forms.FileInput(attrs={'class': 'form-control'}),
        }