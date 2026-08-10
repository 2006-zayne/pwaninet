import django_filters
from .models import NotificationObject
from notifications.notifications.registry import NotificationStatuses
from users.models import User


class NotificationFilter(django_filters.FilterSet):
    recipient = django_filters.ModelChoiceFilter(queryset=User.objects.all())
    notification_type = django_filters.ChoiceFilter(choices=NotificationObject.TYPE_CHOICES)
    category = django_filters.ChoiceFilter(choices=NotificationObject.CATEGORY_CHOICES)
    priority = django_filters.ChoiceFilter(choices=NotificationObject.PRIORITY_CHOICES)
    status = django_filters.ChoiceFilter(choices=[(s.value, s.name) for s in NotificationStatuses])
    context_type = django_filters.CharFilter()
    created_at_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_at_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = NotificationObject
        fields = ['recipient', 'notification_type', 'category', 'priority', 'status', 'context_type', 'created_at_after', 'created_at_before']
