from django import forms
from django.contrib.auth.forms import UserCreationForm
from users.models import User
from courses.models import Year


class PwaniSignupForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + \
            ('first_name', 'second_name', 'last_name', 'course', 'year')

        # WE use HTMX into the Signup dropdowns HTMX is a form of Java script
        # which is directly injected into the HTML.
        widgets = {
            'course': forms.Select(attrs={
                'hx-get': '/courses/load-years/',      # The endpoint for filtering
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
                self.fields['year'].queryset = Year.objects.filter(
                    course_id=course_id).order_by('level')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.course:
            self.fields['year'].queryset = self.instance.course.years.all()


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        # The students will only be allowed to edit the profile pic bio and
        # other fields if possible maybe nicknames but we will figure out that
        # later.
        fields = ['profile_pic', 'bio']
        widgets = {
            'bio': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Write about yourself...'}),
        }

    def __init__(self, *args, **kwargs):
        super(ProfileUpdateForm, self).__init__(*args, **kwargs)
        # THis ensure the file input is visible
        self.fields['profile_pic'].widget.attrs.update(
            {'class': 'form-control-file'})
