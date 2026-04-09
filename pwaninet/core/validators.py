from django.core.exceptions import ValidationError

def validate_image_size(value):
    # Maximum size is 5 MB
    limit_mb = 5
    if value.size > limit_mb * 1024 * 1024:
        raise ValidationError(f"Image too large! Maximum allowed is {limit_mb}MB.")

def validate_video_size(value):
    # Maximum size is 50 MB
    limit_mb = 50
    if value.size > limit_mb * 1024 * 1024:
        raise ValidationError(f"Video file exceeds mission parameters! Maximum allowed is {limit_mb}MB.")

def validate_document_size(value):
    # Maximum size is 10 MB
    limit_mb = 10
    if value.size > limit_mb * 1024 * 1024:
        raise ValidationError(f"Document too heavy! Maximum allowed is {limit_mb}MB.")