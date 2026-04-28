import django_filters
from .models import Course, Year, Unit


class CourseFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Course
        fields = ['name']


class YearFilter(django_filters.FilterSet):
    course = django_filters.ModelChoiceFilter(queryset=Course.objects.all())
    level = django_filters.NumberFilter()
    level_gte = django_filters.NumberFilter(field_name='level', lookup_expr='gte')
    level_lte = django_filters.NumberFilter(field_name='level', lookup_expr='lte')

    class Meta:
        model = Year
        fields = ['course', 'level']


class UnitFilter(django_filters.FilterSet):
    course = django_filters.ModelChoiceFilter(queryset=Course.objects.all())
    year = django_filters.ModelChoiceFilter(queryset=Year.objects.all())
    code = django_filters.CharFilter(lookup_expr='icontains')
    name = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Unit
        fields = ['course', 'year', 'code', 'name']
