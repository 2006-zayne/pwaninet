from django import forms
from posts.models import Post
from posts.validators import validate_audio_size, validate_video_size, validate_document_size
from courses.models import Unit


class PostForm(forms.ModelForm):
    # Unit field definition as a dropdown
    unit = forms.ModelChoiceField(
        queryset=Unit.objects.all(),
        required=False,
        empty_label="Global Feed.",
        # Standard Issue Styling
        widget=forms.Select(attrs={'class': 'form-control'})
    )
   # group = Group.objects.all()
    # save video and docs as optional fields
    video = forms.FileField(
        required=False,
        validators=[validate_video_size],
        widget=forms.ClearableFileInput(
            attrs={
                'class': 'form-control-file',
                'accept': 'video/*'}))
    docs = forms.FileField(
        required=False,
        validators=[validate_document_size],
        widget=forms.ClearableFileInput(
            attrs={
                'class': 'form-control-file',
                'accept': '.pdf'}))
    audio = forms.FileField(
        required=False,
        validators=[validate_audio_size],
        widget=forms.ClearableFileInput(
            attrs={
                'class': 'form-control-file',
                'accept': 'audio/*'
            }))
    images = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(
            attrs={
                'class': 'form-control-file'
            }))

    class Meta:
        model = Post
        fields = [
            'unit',
            'group',
            'content',
            'video',
            'docs',
            'audio',
            'gradient_class',
            'has_signature']

        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 5,
                'cols': 40,
                'placeholder': 'What is on your mind?',
                'class': 'form-control'
            }),
            'gradient_class': forms.Select(attrs={'class': 'form-select'}),
            # 'group' : forms.Select(attrs={'class' : 'form-select'}),
        }

    # Filter units based on the user's Course and Year
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Extract the user from the view
        super().__init__(*args, **kwargs)
        if user:
            # Restrict units to the user's specific deployment sector
            self.fields['unit'].queryset = Unit.objects.filter(
                course=user.course,
                year=user.year
            )

    def clean_content(self):
        content = self.cleaned_data.get('content')
        if content and len(content) > 2500:
            raise forms.ValidationError("Post content cannot exceed 2500 characters.")
        return content
