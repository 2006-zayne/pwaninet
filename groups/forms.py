from django import forms
from groups.models import Group, JoinPolicy, PostVisibility, EditPermission, InvitePermission


class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        # We only want users to fill in these specific fields
        fields = ['name', 'description', 'group_pic', 'cover_photo', 'join_policy']

        # Adding Bootstrap classes so the form looks sharp on your ProBook
        widgets = {
            'name': forms.TextInput(
                attrs={
                    'class': 'form-control rounded-pill',
                    'placeholder': 'Squad Name'}),
            'description': forms.Textarea(
                attrs={
                    'class': 'form-control rounded-4',
                    'rows': 3,
                    'placeholder': 'What is this squad about?'}),
            'group_pic': forms.FileInput(
                attrs={
                    'class': 'form-control'}),
            'cover_photo': forms.FileInput(
                attrs={
                    'class': 'form-control'}),
            'join_policy': forms.Select(
                attrs={
                    'class': 'form-control rounded-pill'}),
        }


class GroupDetailsForm(forms.ModelForm):
    """Form for editing group details (name, description, profile pic, cover photo)"""
    class Meta:
        model = Group
        fields = ['name', 'description', 'group_pic', 'cover_photo']
        
        widgets = {
            'name': forms.TextInput(
                attrs={
                    'placeholder': 'Group Name'}),
            'description': forms.Textarea(
                attrs={
                    'rows': 4,
                    'placeholder': 'Tell people about your group...'}),
            'group_pic': forms.FileInput(
                attrs={
                    'accept': 'image/*'}),
            'cover_photo': forms.FileInput(
                attrs={
                    'accept': 'image/*'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove the required attribute from file fields to allow optional updates
        self.fields['group_pic'].required = False
        self.fields['cover_photo'].required = False


class RoleAssignmentForm(forms.Form):
    """Form for assigning roles to group members"""
    user_id = forms.IntegerField(widget=forms.HiddenInput())
    role = forms.ChoiceField(
        choices=[
            ('MEMBER', 'Member'),
            ('DELEGATE', 'Delegate'),
            ('MODERATOR', 'Moderator'),
            ('ADMIN', 'Admin'),
        ],
        widget=forms.Select(attrs={
            'class': 'django-form-field'
        })
    )


class GroupPrivacyForm(forms.ModelForm):
    """Form for group privacy settings"""
    class Meta:
        model = Group
        fields = ['join_policy', 'post_visibility', 'edit_permission', 'invite_permission']
        
        widgets = {
            'join_policy': forms.Select(attrs={
                'class': 'django-form-field'
            }),
            'post_visibility': forms.Select(attrs={
                'class': 'django-form-field'
            }),
            'edit_permission': forms.Select(attrs={
                'class': 'django-form-field'
            }),
            'invite_permission': forms.Select(attrs={
                'class': 'django-form-field'
            }),
        }
