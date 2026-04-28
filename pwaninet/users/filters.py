import django_filters
from .models import User, Follow, GlobalRole
from courses.models import Course, Year


class UserFilter(django_filters.FilterSet):
    username = django_filters.CharFilter(lookup_expr='icontains')
    first_name = django_filters.CharFilter(lookup_expr='icontains')
    last_name = django_filters.CharFilter(lookup_expr='icontains')
    global_role = django_filters.ChoiceFilter(choices=GlobalRole.choices)
    course = django_filters.ModelChoiceFilter(queryset=Course.objects.all())
    year = django_filters.ModelChoiceFilter(queryset=Year.objects.all())
    search = django_filters.CharFilter(method='search_filter')

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'global_role', 'course', 'year']

    def search_filter(self, queryset, name, value):
        if value:
            return queryset.filter(
                username__icontains=value
            ) | queryset.filter(
                first_name__icontains=value
            ) | queryset.filter(
                last_name__icontains=value
            ) | queryset.filter(
                second_name__icontains=value
            )
        return queryset


class FollowFilter(django_filters.FilterSet):
    follower = django_filters.ModelChoiceFilter(queryset=User.objects.all())
    followed = django_filters.ModelChoiceFilter(queryset=User.objects.all())

    class Meta:
        model = Follow
        fields = ['follower', 'followed']
