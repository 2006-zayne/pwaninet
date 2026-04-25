from django.shortcuts import render
from courses.models import Year


def load_years(request):
    course_id = request.GET.get('course')
    years = Year.objects.filter(course_id=course_id).order_by('level')
    return render(request, 'courses/partials/year_options.html', {'years': years})
