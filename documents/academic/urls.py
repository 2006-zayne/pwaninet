"""
URL patterns for academic HTMX endpoints.
"""
from django.urls import path
from . import views

app_name = 'academic'

urlpatterns = [
    path('dashboard/', views.academic_dashboard, name='dashboard'),
    path('programme-units/add/', views.add_programme_unit_api, name='add_programme_unit'),
    path('profile/update/', views.update_academic_profile_api, name='update_academic_profile'),
    path('lookup-unit/', views.lookup_academic_unit_api, name='lookup_unit'),
    path('units-for-context/', views.units_for_context_api, name='units_for_context'),
    path('load-levels/', views.load_academic_levels, name='load_levels'),
    path('load-years/', views.load_academic_years, name='load_years'),
    path('load-semesters/', views.load_semesters, name='load_semesters'),
    path('my-units/', views.student_units_api, name='student_units_api'),
    path('my-units/sync/', views.sync_student_units_api, name='sync_student_units_api'),
    path('my-units/enroll/', views.enroll_student_unit, name='enroll_student_unit'),
    path('my-units/<int:unit_id>/unenroll/', views.unenroll_student_unit, name='unenroll_student_unit'),
]
