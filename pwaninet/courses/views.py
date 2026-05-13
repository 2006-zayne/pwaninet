from django.shortcuts import render
from rest_framework import viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from courses.models import Course, Year, Unit
from .serializers import (
    CourseSerializer, YearSerializer, UnitSerializer,
    UnitDetailSerializer, CourseWithYearsSerializer, YearWithUnitsSerializer
)
from .filters import CourseFilter, YearFilter, UnitFilter


def load_years(request):
    course_id = request.GET.get('course')
    years = Year.objects.filter(course_id=course_id).order_by('level')
    return render(request, 'courses/partials/year_options.html', {'years': years})


# API ViewSets
class CourseViewSet(viewsets.ModelViewSet):
    """
    API ViewSet for Course model.
    """
    queryset = Course.objects.all().select_related('school')
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = CourseFilter
    search_fields = ['name']
    ordering_fields = ['name']
    ordering = ['name']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CourseWithYearsSerializer
        return CourseSerializer


class YearViewSet(viewsets.ModelViewSet):
    """
    API ViewSet for Year model.
    """
    queryset = Year.objects.all().select_related('course__school')
    serializer_class = YearSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = YearFilter
    ordering_fields = ['level']
    ordering = ['level']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return YearWithUnitsSerializer
        return YearSerializer


class UnitViewSet(viewsets.ModelViewSet):
    """
    API ViewSet for Unit model.
    """
    queryset = Unit.objects.all().select_related('course__school', 'year')
    serializer_class = UnitSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = UnitFilter
    search_fields = ['code', 'name']
    ordering_fields = ['code', 'name']
    ordering = ['code']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return UnitDetailSerializer
        return UnitSerializer
