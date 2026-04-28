from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'courses'

router = DefaultRouter()
router.register(r'courses', views.CourseViewSet, basename='course')
router.register(r'years', views.YearViewSet, basename='year')
router.register(r'units', views.UnitViewSet, basename='unit')

urlpatterns = [
    # API routes
    path('api/', include(router.urls)),
    
    # Web routes
    path('load-years/', views.load_years, name='load_years'),
]
