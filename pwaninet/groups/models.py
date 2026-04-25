from django.db import models
from django.conf import settings


class Groups(models.Model):
    name = models.CharField(max_length=200, unique=True)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_groups')
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='group_memberships', blank=True)
    description = models.TextField(max_length=500, blank=True)
    group_pic = models.ImageField(upload_to='group_profile_pic', null=True, blank=True)
    is_official = models.BooleanField(default=False)

    def __str__(self):
        return self.name
    
    @property
    def get_photo_url(self):
        if self.group_pic and hasattr(self.group_pic, 'url'):
            return self.group_pic.url
        return f"{settings.STATIC_URL}images/default_group.jpg"
