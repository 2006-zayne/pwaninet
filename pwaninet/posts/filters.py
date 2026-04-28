import django_filters
from .models import Post, Comment, Like, Report
from users.models import User
from groups.models import Group
from courses.models import Course, Unit


class PostFilter(django_filters.FilterSet):
    author = django_filters.ModelChoiceFilter(queryset=User.objects.all())
    group = django_filters.ModelChoiceFilter(queryset=Group.objects.all())
    course = django_filters.ModelChoiceFilter(queryset=Course.objects.all())
    unit = django_filters.ModelChoiceFilter(queryset=Unit.objects.all())
    gradient_class = django_filters.ChoiceFilter(choices=Post.GRADIENT_CHOICES)
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    search = django_filters.CharFilter(method='search_filter')
    repost_of = django_filters.ModelChoiceFilter(queryset=Post.objects.all())
    has_media = django_filters.BooleanFilter(method='has_media_filter')
    has_video = django_filters.BooleanFilter(field_name='video')
    has_docs = django_filters.BooleanFilter(field_name='docs')

    class Meta:
        model = Post
        fields = ['author', 'group', 'course', 'unit', 'gradient_class', 'created_after', 'created_before', 'repost_of']

    def search_filter(self, queryset, name, value):
        if value:
            return queryset.filter(content__icontains=value)
        return queryset

    def has_media_filter(self, queryset, name, value):
        if value:
            return queryset.filter(images__isnull=False).distinct()
        return queryset


class CommentFilter(django_filters.FilterSet):
    post = django_filters.ModelChoiceFilter(queryset=Post.objects.all())
    author = django_filters.ModelChoiceFilter(queryset=User.objects.all())
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = Comment
        fields = ['post', 'author', 'created_after', 'created_before']


class LikeFilter(django_filters.FilterSet):
    post = django_filters.ModelChoiceFilter(queryset=Post.objects.all())
    user = django_filters.ModelChoiceFilter(queryset=User.objects.all())
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = Like
        fields = ['post', 'user', 'created_after', 'created_before']


class ReportFilter(django_filters.FilterSet):
    post = django_filters.ModelChoiceFilter(queryset=Post.objects.all())
    reporter = django_filters.ModelChoiceFilter(queryset=User.objects.all())
    reason = django_filters.CharFilter(lookup_expr='icontains')
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = Report
        fields = ['post', 'reporter', 'reason', 'created_after', 'created_before']
