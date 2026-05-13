import django_filters
from .models import Group, Membership
from users.models import User
from courses.models import Course, Year


class GroupFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    created_by = django_filters.ModelChoiceFilter(queryset=User.objects.all())
    is_official = django_filters.BooleanFilter()
    join_policy = django_filters.ChoiceFilter(choices=Group.JoinPolicy.choices)
    course = django_filters.ModelChoiceFilter(queryset=Course.objects.all().select_related('school'))
    year = django_filters.ModelChoiceFilter(queryset=Year.objects.all().select_related('course__school'))
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    search = django_filters.CharFilter(method='search_filter')

    class Meta:
        model = Group
        fields = ['name', 'created_by', 'is_official', 'join_policy', 'course', 'year', 'created_after', 'created_before']

    def search_filter(self, queryset, name, value):
        if value:
            return queryset.filter(name__icontains=value) | queryset.filter(description__icontains=value)
        return queryset


class MembershipFilter(django_filters.FilterSet):
    user = django_filters.ModelChoiceFilter(queryset=User.objects.all())
    group = django_filters.ModelChoiceFilter(queryset=Group.objects.all())
    role = django_filters.ChoiceFilter(choices=Membership.MembershipRole.choices)
    status = django_filters.ChoiceFilter(choices=Membership.MembershipStatus.choices)
    joined_after = django_filters.DateTimeFilter(field_name='joined_at', lookup_expr='gte')
    joined_before = django_filters.DateTimeFilter(field_name='joined_at', lookup_expr='lte')

    class Meta:
        model = Membership
        fields = ['user', 'group', 'role', 'status', 'joined_after', 'joined_before']
