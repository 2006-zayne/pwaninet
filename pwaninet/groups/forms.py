from django import forms
from groups.models import Group


class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        # We only want users to fill in these specific fields
        fields = ['name', 'description', 'group_pic', 'cover_photo']

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
        }
