import django_filters
from .models import Notifications
from users.models import User
from groups.models import Group
from posts.models import Post


class NotificationFilter(django_filters.FilterSet):
    recipient = django_filters.ModelChoiceFilter(queryset=User.objects.all())
    sender = django_filters.ModelChoiceFilter(queryset=User.objects.all())
    group = django_filters.ModelChoiceFilter(queryset=Group.objects.all())
    post = django_filters.ModelChoiceFilter(queryset=Post.objects.all())
    notification_type = django_filters.ChoiceFilter(choices=Notifications.TYPE_CHOICES)
    is_read = django_filters.BooleanFilter()
    timestamp_after = django_filters.DateTimeFilter(field_name='timestamp', lookup_expr='gte')
    timestamp_before = django_filters.DateTimeFilter(field_name='timestamp', lookup_expr='lte')

    class Meta:
        model = Notifications
        fields = ['recipient', 'sender', 'group', 'post', 'notification_type', 'is_read', 'timestamp_after', 'timestamp_before']
