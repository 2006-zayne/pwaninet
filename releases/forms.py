"""
Release forms for PwaniNet Release Center.

Provides Django forms for release creation and editing.
"""
from django import forms
from django.core.exceptions import ValidationError
from .models import Release, ReleaseItem
from .utils import validate_version


class ReleaseForm(forms.ModelForm):
    """
    Form for creating and editing releases.
    """
    
    class Meta:
        model = Release
        fields = [
            'version',
            'build_number',
            'release_title',
            'release_summary',
            'release_type',
            'release_channel',
            'status',
            'mandatory_update',
            'minimum_supported_version',
        ]
        widgets = {
            'release_title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter release title'
            }),
            'release_summary': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter release summary'
            }),
            'release_type': forms.Select(attrs={'class': 'form-select'}),
            'release_channel': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'mandatory_update': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'minimum_supported_version': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 1.0.0'
            }),
            'version': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 1.0.0',
                'readonly': 'readonly'
            }),
            'build_number': forms.NumberInput(attrs={
                'class': 'form-control',
                'readonly': 'readonly'
            }),
        }
    
    def clean_version(self):
        """Validate version format."""
        version = self.cleaned_data.get('version')
        if version and not validate_version(version):
            raise ValidationError('Invalid version format. Use semantic versioning (e.g., 1.0.0)')
        return version
    
    def clean_minimum_supported_version(self):
        """Validate minimum supported version format if provided."""
        version = self.cleaned_data.get('minimum_supported_version')
        if version and not validate_version(version):
            raise ValidationError('Invalid version format. Use semantic versioning (e.g., 1.0.0)')
        return version


class CreateReleaseForm(forms.ModelForm):
    """
    Form for creating a new release with automatic version generation.
    """
    
    release_type = forms.ChoiceField(
        choices=Release.RELEASE_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='Type of release determines version increment'
    )
    
    release_channel = forms.ChoiceField(
        choices=Release.RELEASE_CHANNEL_CHOICES,
        initial='STABLE',
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='Release channel for this release'
    )
    
    class Meta:
        model = Release
        fields = [
            'release_title',
            'release_summary',
            'release_type',
            'release_channel',
            'mandatory_update',
            'minimum_supported_version',
        ]
        widgets = {
            'release_title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter release title'
            }),
            'release_summary': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter release summary'
            }),
            'mandatory_update': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'minimum_supported_version': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 1.0.0 (optional)'
            }),
        }
    
    def clean_minimum_supported_version(self):
        """Validate minimum supported version format if provided."""
        version = self.cleaned_data.get('minimum_supported_version')
        if version and not validate_version(version):
            raise ValidationError('Invalid version format. Use semantic versioning (e.g., 1.0.0)')
        return version


class ReleaseItemForm(forms.ModelForm):
    """
    Form for creating and editing release items.
    """
    
    class Meta:
        model = ReleaseItem
        fields = [
            'category',
            'title',
            'description',
            'display_order',
        ]
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter item title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Enter item description'
            }),
            'display_order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0
            }),
        }


class PublishReleaseForm(forms.Form):
    """
    Form for publishing a release.
    """
    
    confirm = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='I confirm that this release is ready to be published'
    )
    
    set_as_current = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Set as current release',
        help_text='Mark this release as the currently deployed release'
    )


class ArchiveReleaseForm(forms.Form):
    """
    Form for archiving a release.
    """
    
    confirm = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='I confirm that this release should be archived'
    )
    
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Optional reason for archiving'
        }),
        help_text='Optional reason for archiving this release'
    )
