from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.db import models

from .models import (
    Category,
    Tag,
    Document,
    DocumentBookmark,
    DocumentDownload,
    DocumentView,
)
from .selectors.document_selectors import DocumentSelector


# ============== PAGE VIEWS ==============

def repository_home(request):
    """
    Repository landing page with search, categories, and document sections.
    """
    # Get categories
    categories = Category.objects.filter(is_active=True)
    
    # Get trending documents
    trending_documents = DocumentSelector.get_trending_documents(limit=10)
    
    # Get recently added documents
    recent_documents = DocumentSelector.list_documents_for_home(limit=10)
    
    # Get most downloaded documents
    most_downloaded = Document.objects.filter(
        status='ready',
        visibility='public'
    ).annotate(
        download_count=models.Count('downloads')
    ).order_by('-download_count')[:10]
    
    # Get recent searches from session (simpler approach)
    recent_searches = request.session.get('recent_searches', [])
    
    context = {
        'page_title': 'Document Repository',
        'categories': categories,
        'trending_documents': trending_documents,
        'recent_documents': recent_documents,
        'most_downloaded': most_downloaded,
        'recent_searches': recent_searches,
    }
    return render(request, 'documents/home.html', context)


def search_results(request):
    """
    Search results page with filters and sorting.
    """
    query = request.GET.get('q', '')
    category = request.GET.get('category')
    academic_unit = request.GET.get('unit')
    semester = request.GET.get('semester')
    file_type = request.GET.get('file_type')
    sort_by = request.GET.get('sort', 'relevance')
    
    # Save search to session if query exists
    if query:
        recent_searches = request.session.get('recent_searches', [])
        # Add query if not already in recent searches
        if query not in [s if isinstance(s, str) else s.get('query', '') for s in recent_searches]:
            recent_searches.insert(0, query)
            # Keep only last 5 searches
            recent_searches = recent_searches[:5]
            request.session['recent_searches'] = recent_searches
    
    filters = {}
    if category:
        filters['category'] = category
    if academic_unit:
        filters['academic_unit'] = academic_unit
    if semester:
        filters['semester'] = semester
    if file_type:
        filters['file_type'] = file_type
    
    documents = DocumentSelector.search_documents(
        query=query,
        filters=filters,
        limit=50
    )
    
    # Get categories for filter dropdown
    from .models import Category
    categories = Category.objects.filter(is_active=True)
    
    # Get academic units for filter dropdown
    from .academic.models import AcademicUnit, Semester
    academic_units = AcademicUnit.objects.filter(is_active=True)[:50]
    semesters = Semester.objects.all()
    
    context = {
        'page_title': 'Search Results',
        'query': query,
        'documents': documents,
        'category': category,
        'academic_unit': academic_unit,
        'semester': semester,
        'file_type': file_type,
        'sort_by': sort_by,
        'categories': categories,
        'academic_units': academic_units,
        'semesters': semesters,
    }
    return render(request, 'documents/search.html', context)


def clear_recent_searches(request):
    """
    Clear recent searches from session.
    """
    request.session['recent_searches'] = []
    from django.http import HttpResponseRedirect
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


def document_detail(request, document_id):
    """
    Individual document detail page with preview and metadata.
    """
    document = DocumentSelector.get_document_with_relations(document_id)
    
    if not document:
        from django.http import Http404
        raise Http404("Document not found")
    
    # Record view
    if request.user.is_authenticated:
        DocumentView.objects.create(
            document=document,
            user=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )
    
    # Get related documents (same category or academic unit)
    related_documents = Document.objects.filter(
        status='ready',
        visibility='public',
        category=document.category
    ).exclude(id=document.id)[:6]
    
    # Get primary academic unit
    primary_unit = None
    if hasattr(document, 'academic_units'):
        primary_unit = document.academic_units.filter(is_primary=True).first()
    
    context = {
        'page_title': document.title,
        'document': document,
        'related_documents': related_documents,
        'primary_unit': primary_unit,
    }
    return render(request, 'documents/document_detail.html', context)


from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


@csrf_exempt
@require_http_methods(["GET", "POST"])
@login_required
def upload_document(request):
    """
    Multi-stage upload flow for documents.
    """
    if request.method == 'POST':
        # Handle file upload
        files = request.FILES.getlist('files')
        academic_unit_id = request.POST.get('academic_unit')
        category_id = request.POST.get('category')
        academic_year_id = request.POST.get('academic_year')
        semester_id = request.POST.get('semester')
        tags = request.POST.get('tags', '')
        
        if not files:
            from django.http import JsonResponse
            return JsonResponse({'success': False, 'error': 'No files uploaded'}, status=400)
        
        if not category_id:
            from django.http import JsonResponse
            return JsonResponse({'success': False, 'error': 'Category is required'}, status=400)
        
        try:
            # Create documents with status 'processing'
            from .models import Document, DocumentFile, DocumentVersion, DocumentAcademicUnit, DocumentTag, Tag
            from .academic.models import AcademicUnit, Semester, AcademicYear
            
            created_documents = []
            skipped_documents = []
            
            for index, file in enumerate(files):
                # Get individual file metadata if provided
                title = request.POST.get(f'file_{index}_title', file.name.replace('.pdf', '').replace('.docx', '').replace('.pptx', ''))
                description = request.POST.get(f'file_{index}_description', '')
                
                # Check if document with same title already exists for this user
                existing_doc = Document.objects.filter(
                    title=title,
                    uploaded_by=request.user
                ).first()
                
                if existing_doc:
                    skipped_documents.append(title)
                    continue
                
                # Create document (without academic unit/year/semester - those go in junction table)
                document = Document.objects.create(
                    title=title,
                    description=description,
                    uploaded_by=request.user,
                    status='processing',  # Start as processing, Celery will update to ready
                    visibility='public',
                    category_id=category_id
                )
                
                # Create document version
                document_version = DocumentVersion.objects.create(
                    document=document,
                    version_number=1,
                    is_latest=True,
                    created_by=request.user
                )
                
                # Create document file
                document_file = DocumentFile.objects.create(
                    document_version=document_version,
                    file=file,
                    original_filename=file.name,
                    size_bytes=file.size,
                    mime_type=file.content_type,
                    extension=file.name.split('.')[-1].lower() if '.' in file.name else '',
                    storage_path=file.name,
                    uploaded_by=request.user,
                    processing_status='pending',
                    checksum=None  # Will be generated by background processing
                )
                
                # Create academic unit relationship if provided
                if academic_unit_id and semester_id and academic_year_id:
                    DocumentAcademicUnit.objects.create(
                        document=document,
                        academic_unit_id=academic_unit_id,
                        semester_id=semester_id,
                        academic_year_id=academic_year_id,
                        is_primary=True
                    )
                
                # Create tag relationships if tags provided
                if tags:
                    tag_names = [tag.strip() for tag in tags.split(',') if tag.strip()]
                    for tag_name in tag_names:
                        tag, created = Tag.objects.get_or_create(
                            name=tag_name,
                            defaults={'slug': tag_name.lower().replace(' ', '-')}
                        )
                        DocumentTag.objects.create(document=document, tag=tag)
                
                created_documents.append(document)
            
            # Trigger Celery background processing for each document
            from .tasks.processing import process_document
            task_ids = []
            for document in created_documents:
                task = process_document.delay(document.id)
                task_ids.append(task.id)
            
            from django.http import JsonResponse
            return JsonResponse({
                'success': True, 
                'document_count': len(created_documents),
                'skipped_count': len(skipped_documents),
                'skipped_documents': skipped_documents,
                'task_ids': task_ids
            })
            
        except Exception as e:
            import traceback
            from django.http import JsonResponse
            return JsonResponse({'success': False, 'error': str(e), 'traceback': traceback.format_exc()}, status=500)
    
    # GET request - show upload form
    # Get categories and academic units for the form
    categories = Category.objects.filter(is_active=True)
    
    from .academic.models import AcademicUnit, Semester, AcademicYear
    academic_units = AcademicUnit.objects.filter(is_active=True)[:50]
    semesters = Semester.objects.all()
    academic_years = AcademicYear.objects.all()
    
    context = {
        'page_title': 'Upload Document',
        'categories': categories,
        'academic_units': academic_units,
        'semesters': semesters,
        'academic_years': academic_years,
    }
    return render(request, 'documents/upload.html', context)


def upload_progress(request):
    """
    Upload progress tracking (for HTMX polling).
    """
    task_id = request.GET.get('task_id')
    
    if task_id:
        from celery.result import AsyncResult
        try:
            task = AsyncResult(task_id)
            from django.http import JsonResponse
            return JsonResponse({
                'status': task.status,
                'result': task.result if task.ready() else None,
            })
        except Exception as e:
            from django.http import JsonResponse
            return JsonResponse({'error': str(e)}, status=500)
    
    document_id = request.GET.get('document_id')
    
    if document_id:
        from .models import Document, DocumentFile
        try:
            document = Document.objects.get(id=document_id)
            document_file = DocumentFile.objects.filter(
                document_version__document=document
            ).first()
            
            from django.http import JsonResponse
            return JsonResponse({
                'status': document.status,
                'processing_status': document_file.processing_status if document_file else 'unknown',
                'has_preview': bool(document_file.preview_path) if document_file else False,
                'has_thumbnail': bool(document_file.thumbnail_path) if document_file else False,
            })
        except Document.DoesNotExist:
            from django.http import JsonResponse
            return JsonResponse({'error': 'Document not found'}, status=404)
    
    return render(request, 'documents/partials/upload_progress.html')


@login_required
def my_library(request):
    """
    Personal library dashboard with uploads, bookmarks, downloads.
    """
    user = request.user
    
    # Get statistics
    upload_count = Document.objects.filter(uploaded_by=user).count()
    bookmark_count = DocumentBookmark.objects.filter(user=user).count()
    download_count = DocumentDownload.objects.filter(user=user).count()
    view_count = DocumentView.objects.filter(user=user).count()
    
    # Get recent activity
    recent_uploads = Document.objects.filter(uploaded_by=user)[:5]
    recent_bookmarks = DocumentBookmark.objects.filter(user=user).select_related('document')[:5]
    
    context = {
        'page_title': 'My Library',
        'upload_count': upload_count,
        'bookmark_count': bookmark_count,
        'download_count': download_count,
        'view_count': view_count,
        'recent_uploads': recent_uploads,
        'recent_bookmarks': recent_bookmarks,
    }
    return render(request, 'documents/my_library.html', context)


@login_required
def clear_history(request):
    """
    Clear user's document view history.
    """
    if request.method == 'POST':
        DocumentView.objects.filter(user=request.user).delete()
        from django.contrib import messages
        messages.success(request, 'Your viewing history has been cleared.')
    from django.http import HttpResponseRedirect
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/documents/library/'))


@login_required
def my_uploads(request):
    """
    User's uploaded documents.
    """
    documents = DocumentSelector.list_documents_for_user(
        user_id=request.user.id,
        document_type='uploads',
        limit=50
    )
    
    context = {
        'page_title': 'My Uploads',
        'documents': documents,
    }
    return render(request, 'documents/library_uploads.html', context)


@login_required
def my_bookmarks(request):
    """
    User's bookmarked documents.
    """
    bookmarks = DocumentBookmark.objects.filter(
        user=request.user
    ).select_related('document').order_by('-created_at')
    
    context = {
        'page_title': 'My Bookmarks',
        'bookmarks': bookmarks,
    }
    return render(request, 'documents/library_bookmarks.html', context)


@login_required
def my_downloads(request):
    """
    User's download history.
    """
    downloads = DocumentDownload.objects.filter(
        user=request.user
    ).select_related('document', 'document_file').order_by('-downloaded_at')
    
    context = {
        'page_title': 'My Downloads',
        'downloads': downloads,
    }
    return render(request, 'documents/library_downloads.html', context)


@login_required
def my_history(request):
    """
    User's viewing history.
    """
    views = DocumentView.objects.filter(
        user=request.user
    ).select_related('document').order_by('-viewed_at')
    
    context = {
        'page_title': 'My History',
        'views': views,
    }
    return render(request, 'documents/library_history.html', context)
