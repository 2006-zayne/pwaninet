from django import forms
from django.contrib.auth.forms import UserCreationForm
from users.models import User, CollaborationStatus
from courses.models import Year


class PwaniSignupForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + \
            ('email', 'first_name', 'second_name', 'last_name', 'course', 'year')

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

        # Make email required
        self.fields['email'].required = True

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

    def clean_email(self):
        """Validate that email is unique across all users."""
        email = self.cleaned_data.get('email')
        if not email:
            return email

        # Normalize email to lowercase for consistency
        email = email.lower()

        # Check if email already exists
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                "A user with this email address already exists. "
                "Please use a different email address or log in to your existing account."
            )

        return email


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        # The students will only be allowed to edit the profile pic bio and
        # other fields if possible maybe nicknames but we will figure out that
        # later.
        # Note: course and year are intentionally excluded as they should not be editable
        fields = [
            'profile_pic', 'cover_photo', 'bio',
            'headline', 'interests', 'collaboration_status',
            'skills', 'projects',
            'github_url', 'linkedin_url', 'portfolio_url', 'twitter_url'
        ]
        help_texts = {
            'skills': 'Enter one skill per line. No JSON required - just simple text!',
            'projects': 'Format: Title|Description|Link (one project per line). Use | to separate parts.',
            'interests': 'Enter interests separated by commas, e.g., AI, Web Development, Music'
        }
        widgets = {
            'bio': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Write about yourself...'}),
            'headline': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'e.g., Computer Science Student | Open to Projects'}),
            'interests': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'e.g., AI, Web Development, Data Science (comma-separated)'}),
            'collaboration_status': forms.Select(
                attrs={'class': 'form-control'}),
            'skills': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter one skill per line, e.g.:\nPython\nJavaScript\nReact\nData Science'}),
            'projects': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 6,
                    'placeholder': 'Format: Title|Description|Link (one project per line)\nExample:\nMy Website|A personal portfolio|https://mysite.com\nWeather App|Weather dashboard|https://github.com/user/weather'}),
            'github_url': forms.URLInput(
                attrs={'class': 'form-control', 'placeholder': 'https://github.com/username'}),
            'linkedin_url': forms.URLInput(
                attrs={'class': 'form-control', 'placeholder': 'https://linkedin.com/in/username'}),
            'portfolio_url': forms.URLInput(
                attrs={'class': 'form-control', 'placeholder': 'https://yourportfolio.com'}),
            'twitter_url': forms.URLInput(
                attrs={'class': 'form-control', 'placeholder': 'https://twitter.com/username'}),
        }

    def __init__(self, *args, **kwargs):
        super(ProfileUpdateForm, self).__init__(*args, **kwargs)
        # THis ensure the file input is visible
        self.fields['profile_pic'].widget.attrs.update(
            {'class': 'form-control-file'})
        self.fields['cover_photo'].widget.attrs.update(
            {'class': 'form-control-file'})
        
        # Display school, course, and year as read-only for information
        if self.instance and self.instance.course:
            self.fields['course'] = forms.CharField(
                initial=self.instance.course.name,
                widget=forms.TextInput(attrs={'readonly': True, 'class': 'form-control'}),
                required=False,
                label='Course'
            )
        if self.instance and self.instance.course and self.instance.course.school:
            self.fields['school'] = forms.CharField(
                initial=self.instance.course.school.name,
                widget=forms.TextInput(attrs={'readonly': True, 'class': 'form-control'}),
                required=False,
                label='School'
            )
        if self.instance and self.instance.year:
            self.fields['year'] = forms.CharField(
                initial=f"Year {self.instance.year.level}",
                widget=forms.TextInput(attrs={'readonly': True, 'class': 'form-control'}),
                required=False,
                label='Year'
            )
        
        # Format skills for display (list to newline-separated)
        if self.instance and self.instance.skills:
            self.fields['skills'].initial = '\n'.join(self.instance.skills)
        
        # Format projects for display (list of dicts to Title|Description|Link format)
        if self.instance and self.instance.projects:
            project_lines = []
            for project in self.instance.projects:
                line = f"{project.get('title', '')}|{project.get('description', '')}|{project.get('link', '')}"
                project_lines.append(line)
            self.fields['projects'].initial = '\n'.join(project_lines)
    
    def clean_skills(self):
        """Convert skills textarea to list"""
        skills_text = self.cleaned_data.get('skills', '')
        if skills_text:
            # Handle case where data might already be a list (from API)
            if isinstance(skills_text, list):
                return skills_text

            # Handle case where data might be a JSON string
            if isinstance(skills_text, str) and skills_text.startswith('['):
                try:
                    import json
                    skills = json.loads(skills_text)
                    if isinstance(skills, list):
                        return skills
                except json.JSONDecodeError:
                    # If JSON parsing fails, continue with text processing
                    pass

            # Split by newlines and strip whitespace
            skills = [skill.strip() for skill in skills_text.split('\n') if skill.strip()]
            # Validate that skills is a list (will be stored as JSON)
            if not isinstance(skills, list):
                raise forms.ValidationError("Skills must be a list. Please enter one skill per line.")
            return skills
        return []

    def clean_projects(self):
        """Convert projects textarea to list of dicts"""
        projects_text = self.cleaned_data.get('projects', '')
        if projects_text:
            # Handle case where data might already be a list (from API)
            if isinstance(projects_text, list):
                return projects_text

            # Handle case where data might be a JSON string
            if isinstance(projects_text, str) and projects_text.startswith('['):
                try:
                    import json
                    projects = json.loads(projects_text)
                    if isinstance(projects, list):
                        return projects
                except json.JSONDecodeError:
                    # If JSON parsing fails, continue with text processing
                    pass

            # Process as text format
            projects = []
            for line in projects_text.split('\n'):
                line = line.strip()
                if line:
                    parts = line.split('|')
                    if len(parts) >= 2:
                        project = {
                            'title': parts[0].strip(),
                            'description': parts[1].strip(),
                            'link': parts[2].strip() if len(parts) > 2 else ''
                        }
                        projects.append(project)
                    else:
                        # Provide helpful error for invalid format
                        raise forms.ValidationError(
                            "Invalid project format. Use: Title|Description|Link (separate parts with | symbol). "
                            "Example: My Website|A personal portfolio|https://mysite.com"
                        )
            # Validate that projects is a list (will be stored as JSON)
            if not isinstance(projects, list):
                raise forms.ValidationError("Projects must be a list. Please check your format.")
            return projects
        return []


class NotificationPreferencesForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'notify_on_like',
            'notify_on_follow',
            'notify_on_invite',
            'notify_on_group_request',
            'notify_on_group_approved',
            'email_notifications'
        ]
        widgets = {
            'notify_on_like': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notify_on_follow': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notify_on_invite': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notify_on_group_request': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notify_on_group_approved': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'notify_on_like': 'Like notifications',
            'notify_on_follow': 'Follow notifications',
            'notify_on_invite': 'Group invite notifications',
            'notify_on_group_request': 'Group join request notifications',
            'notify_on_group_approved': 'Group approval notifications',
            'email_notifications': 'Email notifications'
        }
