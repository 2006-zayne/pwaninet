from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import api

app_name = 'documents'

# API Router
router = DefaultRouter()
router.register(r'academic-years', api.AcademicYearViewSet, basename='academic-year')
router.register(r'semesters', api.SemesterViewSet, basename='semester')
router.register(r'faculties', api.FacultyViewSet, basename='faculty')
router.register(r'schools', api.SchoolViewSet, basename='school')
router.register(r'departments', api.DepartmentViewSet, basename='department')
router.register(r'programmes', api.ProgrammeViewSet, basename='programme')
router.register(r'academic-units', api.AcademicUnitViewSet, basename='academic-unit')
router.register(r'categories', api.CategoryViewSet, basename='category')
router.register(r'tags', api.TagViewSet, basename='tag')
router.register(r'documents', api.DocumentViewSet, basename='document')
router.register(r'my-documents', api.UserDocumentViewSet, basename='my-document')

urlpatterns = [
    # Repository Home
    path('', views.repository_home, name='home'),
    
    # Search
    path('search/', views.search_results, name='search'),
    path('search/clear/', views.clear_recent_searches, name='clear_recent_searches'),
    
    # Document Details
    path('document/<int:document_id>/', views.document_detail, name='document_detail'),
    
    # Upload Flow
    path('upload/', views.upload_document, name='upload'),
    path('upload/progress/', views.upload_progress, name='upload_progress'),
    
    # My Library
    path('library/', views.my_library, name='my_library'),
    path('library/uploads/', views.my_uploads, name='my_uploads'),
    path('library/bookmarks/', views.my_bookmarks, name='my_bookmarks'),
    path('library/downloads/', views.my_downloads, name='my_downloads'),
    path('library/history/', views.my_history, name='my_history'),
    path('library/clear-history/', views.clear_history, name='clear_history'),
    
    # API Endpoints
    path('api/', include(router.urls)),
]
