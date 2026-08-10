"""
HTMX views for cascading academic dropdowns in registration form.
"""
from django.shortcuts import render
from django.http import HttpResponse
from .models import Programme, AcademicLevel, AcademicYear, Semester


def load_academic_levels(request):
    """Load academic levels for a programme (HTMX endpoint)."""
    programme_id = request.GET.get('programme')
    levels = AcademicLevel.objects.filter(is_active=True).order_by('level')
    
    context = {'levels': levels}
    return render(request, 'users/partials/academic_level_options.html', context)


def load_academic_years(request):
    """Load academic years for an academic level (HTMX endpoint)."""
    level_id = request.GET.get('academic_level')
    years = AcademicYear.objects.all().order_by('-code')
    
    context = {'years': years}
    return render(request, 'users/partials/academic_year_options.html', context)


def load_semesters(request):
    """Load semesters for an academic year (HTMX endpoint)."""
    year_id = request.GET.get('academic_year')
    semesters = Semester.objects.filter(academic_year_id=year_id).order_by('number')
    
    context = {'semesters': semesters}
    return render(request, 'users/partials/semester_options.html', context)
