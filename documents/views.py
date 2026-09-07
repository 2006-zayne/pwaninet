import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.db import models
from django.core.cache import cache
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)

from .models import (
    Category,
    Tag,
    Document,
    DocumentBookmark,
    DocumentDownload,
    DocumentView,
)
from documents.engagement.models import DocumentRating, DocumentShare, DocumentAnalytics
from .selectors.document_selectors import DocumentSelector
from pwaninet.utils.htmx import htmx_location_response


# ============== PAGE VIEWS ==============

def repository_home(request):
    """
    Repository landing page with search, categories, and document sections.
    """
    # Get categories
    categories = Category.objects.filter(is_active=True)
    
    # Get trending documents with personalization
    trending_documents = DocumentSelector.get_trending_documents(
        limit=10,
        user=request.user if request.user.is_authenticated else None
    )
    
    # Get recently added documents with personalization
    recent_documents = DocumentSelector.list_documents_for_home(
        limit=10,
        user=request.user if request.user.is_authenticated else None
    )
    
    # Get popular documents with personalization
    popular_documents = DocumentSelector.get_popular_documents(
        limit=10,
        user=request.user if request.user.is_authenticated else None
    )
    
    # Get recent searches from session (simpler approach)
    recent_searches = request.session.get('recent_searches', [])
    
    context = {
        'page_title': 'Document Repository',
        'categories': categories,
        'trending_documents': trending_documents,
        'recent_documents': recent_documents,
        'popular_documents': popular_documents,
        'recent_searches': recent_searches,
        'document_content_partial': 'documents/partials/home_content.html',
        'show_library_button': True,
        'show_upload_button': True,
    }
    if request.headers.get('HX-Request'):
        return render(request, 'documents/partials/documents_navigation_partial.html', context)
    return render(request, 'documents/home.html', context)


def search_results(request):
    """
    Search results page with filters and sorting.
    """
    query = request.GET.get('q', '')
    category = request.GET.get('category')
    academic_unit = request.GET.get('unit')
    academic_level = request.GET.get('academic_level')
    semester = request.GET.get('semester')
    academic_year = request.GET.get('academic_year')
    programme = request.GET.get('programme')
    school = request.GET.get('school')
    department = request.GET.get('department')
    file_type = request.GET.get('file_type')
    sort_by = request.GET.get('sort', 'relevance')
    
    # Personalized filters
    my_programme = request.GET.get('my_programme')
    my_units = request.GET.get('my_units')
    my_semester = request.GET.get('my_semester')
    my_level = request.GET.get('my_level')
    my_academic_year = request.GET.get('my_academic_year')
    
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
    if academic_level:
        filters['academic_level'] = academic_level
    if semester:
        filters['semester'] = semester
    if academic_year:
        filters['academic_year'] = academic_year
    if programme:
        filters['programme'] = programme
    if school:
        filters['school'] = school
    if department:
        filters['department'] = department
    if file_type:
        filters['file_type'] = file_type
    
    # Apply personalized filters if user is authenticated
    if request.user.is_authenticated:
        if my_programme and request.user.programme:
            filters['programme'] = request.user.programme.id
        if my_units and request.user.programme:
            from .academic.models import ProgrammeUnit
            user_units = ProgrammeUnit.objects.filter(
                programme=request.user.programme
            ).values_list('academic_unit_id', flat=True)
            if user_units:
                filters['academic_units'] = list(user_units)
        if my_semester and request.user.semester:
            filters['semester'] = request.user.semester.id
        if my_level and request.user.academic_level:
            filters['academic_level'] = request.user.academic_level.id
        if my_academic_year and request.user.academic_year:
            filters['academic_year'] = request.user.academic_year.id
    
    # Get "Did you mean" suggestion
    from search.services.unified_search_service import UnifiedSearchService
    unified_service = UnifiedSearchService()
    did_you_mean = unified_service.get_document_did_you_mean(query) if query else None
    
    documents = DocumentSelector.search_documents(
        query=query,
        filters=filters,
        limit=50,
        user=request.user if request.user.is_authenticated else None,
        sort_by=sort_by,
    )
    
    # Get categories for filter dropdown
    from .models import Category
    categories = Category.objects.filter(is_active=True)
    
    # Get academic entities for filter dropdown
    from .academic.models import AcademicUnit, Semester, AcademicYear, AcademicLevel, Programme, School, Department
    academic_units = AcademicUnit.objects.filter(is_active=True)[:50]
    semesters = Semester.objects.all()
    academic_years = AcademicYear.objects.all()
    academic_levels = AcademicLevel.objects.filter(is_active=True)
    programmes = Programme.objects.filter(is_active=True)
    schools = School.objects.all()
    departments = Department.objects.all()
    
    context = {
        'page_title': 'Search Results',
        'query': query,
        'documents': documents,
        'category': category,
        'academic_unit': academic_unit,
        'academic_level': academic_level,
        'semester': semester,
        'academic_year': academic_year,
        'programme': programme,
        'school': school,
        'department': department,
        'file_type': file_type,
        'sort_by': sort_by,
        'my_programme': my_programme,
        'my_units': my_units,
        'my_semester': my_semester,
        'my_level': my_level,
        'my_academic_year': my_academic_year,
        'categories': categories,
        'academic_units': academic_units,
        'semesters': semesters,
        'academic_years': academic_years,
        'academic_levels': academic_levels,
        'programmes': programmes,
        'schools': schools,
        'departments': departments,
        'did_you_mean': did_you_mean,
        'document_content_partial': 'documents/partials/search_content.html',
        'show_library_button': True,
        'show_upload_button': True,
    }
    if request.headers.get('HX-Request'):
        return render(request, 'documents/partials/documents_navigation_partial.html', context)
    return render(request, 'documents/search.html', context)


def clear_recent_searches(request):
    """
    Clear recent searches from session.
    """
    request.session['recent_searches'] = []
    if request.headers.get('HX-Request'):
        return htmx_location_response(request.META.get('HTTP_REFERER', '/documents/search/'))
    from django.http import HttpResponseRedirect
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/documents/search/'))


def search_suggestions_view(request):
    """
    Autocomplete search suggestions endpoint returning JSON.
    """
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'suggestions': []})

    from search.services.unified_search_service import UnifiedSearchService
    search_service = UnifiedSearchService()
    suggestions = search_service.get_document_suggestions(q)
    return JsonResponse({'suggestions': suggestions})


def document_detail(request, document_id):
    """
    Individual document detail page with preview and metadata.
    """
    document = DocumentSelector.get_document_with_relations(document_id)
    
    if not document:
        from django.http import Http404
        raise Http404("Document not found")
    
    # Record view asynchronously with caching
    cache_key = f'doc_view_{document_id}_{request.session.session_key or request.META.get("REMOTE_ADDR")}'
    if not cache.get(cache_key):
        # Create view record
        if request.user.is_authenticated:
            DocumentView.objects.create(
                document=document,
                user=request.user,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )
        else:
            DocumentView.objects.create(
                document=document,
                session_key=request.session.session_key or 'anon',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )
        # Cache for 5 minutes to prevent duplicate views
        cache.set(cache_key, True, 300)
    
    # Get cached view count or fetch from database
    view_count_cache_key = f'doc_view_count_{document_id}'
    cached_view_count = cache.get(view_count_cache_key)
    if cached_view_count is None:
        # Cache view count for 10 minutes
        cached_view_count = document.views.count()
        cache.set(view_count_cache_key, cached_view_count, 600)
    
    # Get cached download count
    download_count_cache_key = f'doc_download_count_{document_id}'
    cached_download_count = cache.get(download_count_cache_key)
    if cached_download_count is None:
        # Cache download count for 10 minutes
        cached_download_count = document.downloads.count()
        cache.set(download_count_cache_key, cached_download_count, 600)
    
    # Get cached bookmark count
    bookmark_count_cache_key = f'doc_bookmark_count_{document_id}'
    cached_bookmark_count = cache.get(bookmark_count_cache_key)
    if cached_bookmark_count is None:
        # Cache bookmark count for 10 minutes
        cached_bookmark_count = document.bookmarks.count()
        cache.set(bookmark_count_cache_key, cached_bookmark_count, 600)
    
    # Get related documents using improved relevance algorithm
    related_documents = DocumentSelector.get_related_documents(document, limit=6)
    
    # Get primary academic unit
    primary_unit = None
    if hasattr(document, 'academic_units'):
        primary_unit = document.academic_units.filter(is_primary=True).first()
    
    # Check if user has bookmarked this document
    is_bookmarked = False
    if request.user.is_authenticated:
        is_bookmarked = document.bookmarks.filter(user=request.user).exists()
    
    # Get user's rating
    user_rating = None
    if request.user.is_authenticated:
        rating_obj = document.ratings.filter(user=request.user).first()
        if rating_obj:
            user_rating = rating_obj.rating
    
    # Get or create analytics
    analytics, _ = DocumentAnalytics.objects.get_or_create(document=document)
    can_manage = user_can_manage_document(request.user, document)
    versions = document.versions.prefetch_related('files').order_by('-version_number')
    
    context = {
        'page_title': document.title,
        'document': document,
        'related_documents': related_documents,
        'primary_unit': primary_unit,
        'is_bookmarked': is_bookmarked,
        'user_rating': user_rating,
        'analytics': analytics,
        'can_manage': can_manage,
        'versions': versions,
        'document_content_partial': 'documents/partials/document_detail_content.html',
        'show_library_button': True,
        'show_upload_button': False,
    }
    if request.headers.get('HX-Request'):
        return render(request, 'documents/partials/documents_navigation_partial.html', context)
    return render(request, 'documents/document_detail.html', context)


def user_can_manage_document(user, document) -> bool:
    """Check if the user has permission to edit, delete, or manage the document."""
    if not user or not user.is_authenticated:
        return False
    if document.uploaded_by_id == user.id:
        return True
    if user.is_staff or user.is_superuser:
        return True
    from users.models import GlobalRole
    if getattr(user, 'global_role', None) in [GlobalRole.PRESIDENT, GlobalRole.DELEGATE]:
        return True
    return False


@login_required
def edit_document(request, document_id):
    """Edit document metadata (title, description, category, academic unit, visibility, language)."""
    document = Document.objects.filter(id=document_id).first()
    if not document:
        return JsonResponse({'success': False, 'error': 'Document not found'}, status=404)

    if not user_can_manage_document(request.user, document):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    from .academic.models import AcademicUnit, Programme
    from .models import DocumentAcademicUnit

    if request.method == 'GET':
        categories = Category.objects.filter(is_active=True).order_by('name')
        programmes = Programme.objects.filter(is_active=True).order_by('name')
        academic_units = AcademicUnit.objects.filter(is_active=True).order_by('name')
        primary_academic_unit = document.academic_units.filter(is_primary=True).first()

        context = {
            'document': document,
            'categories': categories,
            'programmes': programmes,
            'academic_units': academic_units,
            'primary_academic_unit': primary_academic_unit,
        }
        return render(request, 'documents/partials/edit_document_modal.html', context)

    # POST update
    title = request.POST.get('title', '').strip()
    if not title:
        return JsonResponse({'success': False, 'error': 'Title is required'}, status=400)

    description = request.POST.get('description', '').strip()
    category_id = request.POST.get('category')
    visibility = request.POST.get('visibility', document.visibility)
    language = request.POST.get('language', document.language)
    academic_unit_id = request.POST.get('academic_unit')

    if category_id:
        try:
            document.category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Invalid category'}, status=400)

    document.title = title
    document.description = description
    if visibility in ['public', 'private', 'restricted']:
        document.visibility = visibility
    if language in ['en', 'sw', 'fr', 'other']:
        document.language = language
    document.save()

    # Update academic unit
    if academic_unit_id:
        try:
            unit = AcademicUnit.objects.get(id=academic_unit_id)
            doc_unit = document.academic_units.filter(is_primary=True).first()
            if doc_unit:
                doc_unit.academic_unit = unit
                doc_unit.save(update_fields=['academic_unit'])
            else:
                from .academic.models import Semester, AcademicYear as AcadYear
                current_semester = Semester.objects.filter(is_current=True).first()
                current_year = AcadYear.objects.filter(is_current=True).first()
                if current_semester and current_year:
                    DocumentAcademicUnit.objects.create(
                        document=document,
                        academic_unit=unit,
                        semester=current_semester,
                        academic_year=current_year,
                        is_primary=True
                    )
                else:
                    logger.warning(
                        f"Cannot create DocumentAcademicUnit for document {document.id}: "
                        "no current semester or academic year configured"
                    )
        except AcademicUnit.DoesNotExist:
            pass

    # Update search index
    try:
        from documents.services.search_service import SearchService
        SearchService().index_document(document)
    except Exception as e:
        logger.warning(f"Error re-indexing document {document.id} after edit: {e}")

    if request.headers.get('HX-Request'):
        response = HttpResponse(status=200)
        response['HX-Refresh'] = 'true'
        return response

    from django.contrib import messages
    messages.success(request, 'Document updated successfully.')
    return redirect('documents:document_detail', document_id=document.id)


@login_required
def delete_document_modal(request, document_id):
    """Return confirmation modal HTML for document deletion."""
    document = Document.objects.filter(id=document_id).first()
    if not document:
        return JsonResponse({'success': False, 'error': 'Document not found'}, status=404)

    if not user_can_manage_document(request.user, document):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    return render(request, 'documents/partials/delete_document_modal.html', {'document': document})


@login_required
def delete_document(request, document_id):
    """Soft-delete a document (archive)."""
    document = Document.objects.filter(id=document_id).first()
    if not document:
        return JsonResponse({'success': False, 'error': 'Document not found'}, status=404)

    if not user_can_manage_document(request.user, document):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    if request.method == 'POST':
        document.archive()

        # Remove from search index
        try:
            from documents.search.models import DocumentSearchIndex
            DocumentSearchIndex.objects.filter(document=document).delete()
        except Exception as e:
            logger.warning(f"Error removing document {document.id} from search index: {e}")

        from django.contrib import messages
        messages.success(request, 'Document has been deleted.')

        if request.headers.get('HX-Request'):
            referer = request.META.get('HTTP_REFERER', '')
            if f'/document/{document_id}' in referer:
                return htmx_location_response(request.build_absolute_uri(reverse('documents:my_library')))
            return HttpResponse(status=200)

        return redirect('documents:my_library')

    return JsonResponse({'error': 'POST required'}, status=405)


@login_required
def toggle_document_availability(request, document_id):
    """Toggle document availability (mark unavailable / available)."""
    document = Document.objects.filter(id=document_id).first()
    if not document:
        return JsonResponse({'success': False, 'error': 'Document not found'}, status=404)

    if not user_can_manage_document(request.user, document):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    if request.method == 'POST':
        new_avail = document.toggle_availability()

        try:
            from documents.services.search_service import SearchService
            SearchService().index_document(document)
        except Exception as e:
            logger.warning(f"Error updating search index after availability toggle for {document.id}: {e}")

        msg = "Document is now available to students." if new_avail else "Document marked unavailable."
        from django.contrib import messages
        messages.success(request, msg)

        if request.headers.get('HX-Request'):
            response = HttpResponse(status=200)
            response['HX-Refresh'] = 'true'
            return response

        return redirect('documents:document_detail', document_id=document.id)

    return JsonResponse({'error': 'POST required'}, status=405)


@login_required
def upload_new_version(request, document_id):
    """Upload a new version of an existing document."""
    document = Document.objects.filter(id=document_id).first()
    if not document:
        return JsonResponse({'success': False, 'error': 'Document not found'}, status=404)

    if not user_can_manage_document(request.user, document):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    if request.method == 'GET':
        return render(request, 'documents/partials/new_version_modal.html', {'document': document})

    # POST
    new_file = request.FILES.get('file')
    if not new_file:
        return JsonResponse({'success': False, 'error': 'No file uploaded'}, status=400)

    change_notes = request.POST.get('change_notes', '').strip()

    from documents.services.upload_service import UploadService
    service = UploadService()

    try:
        version = service.create_document_version(
            document=document,
            file=new_file,
            user=request.user,
            change_notes=change_notes,
        )
        return JsonResponse({
            'success': True,
            'message': f'Version {version.version_number} uploaded successfully and is being processed.',
            'version_number': version.version_number,
        })
    except ValueError as ve:
        return JsonResponse({'success': False, 'error': str(ve)}, status=400)
    except Exception as e:
        logger.error(f"Error uploading new version for document {document.id}: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': f'Upload failed: {str(e)}'}, status=500)



from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


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
        academic_level_id = request.POST.get('academic_level')
        tags = request.POST.get('tags', '')
        
        if not files:
            from django.http import JsonResponse
            return JsonResponse({'success': False, 'error': 'No files uploaded'}, status=400)
        
        if not category_id:
            from django.http import JsonResponse
            return JsonResponse({'success': False, 'error': 'Category is required'}, status=400)
        
        from .services.upload_service import UploadService
        upload_service = UploadService()
        for file in files:
            is_valid, error_msg = upload_service.validate_file(file)
            if not is_valid:
                from django.http import JsonResponse
                return JsonResponse({'success': False, 'error': f"{file.name}: {error_msg}"}, status=400)

        try:
            # Create documents with status 'processing'
            from .models import Document, DocumentFile, DocumentVersion, DocumentAcademicUnit, DocumentTag, Tag
            from .academic.models import AcademicUnit, Semester, AcademicYear, AcademicLevel
            
            created_documents = []
            skipped_documents = []
            
            for index, file in enumerate(files):
                # Get individual file metadata if provided
                raw_title = request.POST.get(f'file_{index}_title')
                if raw_title and raw_title.strip():
                    title = raw_title.strip()
                else:
                    title = file.name.rsplit('.', 1)[0] if '.' in file.name else file.name
                description = request.POST.get(f'file_{index}_description', '')
                
                # Check if document with same title already exists for this user; ensure unique title
                base_title = title
                counter = 1
                while Document.objects.filter(title=title, uploaded_by=request.user).exists():
                    title = f"{base_title} ({counter})"
                    counter += 1
                
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
                if academic_unit_id and semester_id and academic_year_id and academic_level_id:
                    DocumentAcademicUnit.objects.create(
                        document=document,
                        academic_unit_id=academic_unit_id,
                        semester_id=semester_id,
                        academic_year_id=academic_year_id,
                        academic_level_id=academic_level_id,
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
    
    from .academic.models import AcademicUnit, Semester, AcademicYear, AcademicLevel
    academic_units = AcademicUnit.objects.filter(is_active=True)[:50]
    semesters = Semester.objects.all()
    academic_years = AcademicYear.objects.all()
    academic_levels = AcademicLevel.objects.filter(is_active=True)
    
    context = {
        'page_title': 'Upload Document',
        'categories': categories,
        'academic_units': academic_units,
        'semesters': semesters,
        'academic_years': academic_years,
        'academic_levels': academic_levels,
        'document_content_partial': 'documents/partials/upload_content.html',
        'show_library_button': True,
        'show_upload_button': False,
    }
    if request.headers.get('HX-Request'):
        return render(request, 'documents/partials/documents_navigation_partial.html', context)
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
    upload_count = Document.objects.filter(uploaded_by=user).exclude(status='archived').count()
    bookmark_count = DocumentBookmark.objects.filter(user=user).count()
    download_count = DocumentDownload.objects.filter(user=user).count()
    view_count = DocumentView.objects.filter(user=user).count()
    
    # Get recent activity
    recent_uploads = list(Document.objects.filter(
        uploaded_by=user
    ).exclude(
        status='archived'
    ).select_related(
        'category'
    ).prefetch_related(
        'versions__files',
        'academic_units__academic_unit'
    ).order_by('-created_at')[:5])
    recent_bookmarks = DocumentBookmark.objects.filter(user=user).select_related('document')[:5]
    has_processing_uploads = any(doc.is_processing for doc in recent_uploads)
    
    context = {
        'page_title': 'My Library',
        'upload_count': upload_count,
        'bookmark_count': bookmark_count,
        'download_count': download_count,
        'view_count': view_count,
        'recent_uploads': recent_uploads,
        'recent_bookmarks': recent_bookmarks,
        'has_processing_uploads': has_processing_uploads,
        'document_content_partial': 'documents/partials/my_library_content.html',
        'show_library_button': False,
        'show_upload_button': True,
    }
    if request.headers.get('HX-Request'):
        return render(request, 'documents/partials/documents_navigation_partial.html', context)
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
    if request.headers.get('HX-Request'):
        return htmx_location_response(request.META.get('HTTP_REFERER', '/documents/library/'))
    from django.http import HttpResponseRedirect
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/documents/library/'))


@login_required
def my_uploads(request):
    """
    User's uploaded documents.
    """
    documents = list(DocumentSelector.list_documents_for_user(
        user_id=request.user.id,
        document_type='uploads',
        limit=50
    ))
    has_processing_uploads = any(doc.is_processing for doc in documents)
    
    context = {
        'page_title': 'My Uploads',
        'documents': documents,
        'has_processing_uploads': has_processing_uploads,
        'document_content_partial': 'documents/partials/library_uploads_content.html',
        'show_library_button': False,
        'show_upload_button': True,
    }
    if request.headers.get('HX-Request'):
        return render(request, 'documents/partials/documents_navigation_partial.html', context)
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
        'document_content_partial': 'documents/partials/library_bookmarks_content.html',
        'show_library_button': False,
        'show_upload_button': True,
    }
    if request.headers.get('HX-Request'):
        return render(request, 'documents/partials/documents_navigation_partial.html', context)
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
        'document_content_partial': 'documents/partials/library_downloads_content.html',
        'show_library_button': False,
        'show_upload_button': True,
    }
    if request.headers.get('HX-Request'):
        return render(request, 'documents/partials/documents_navigation_partial.html', context)
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
        'document_content_partial': 'documents/partials/library_history_content.html',
        'show_library_button': False,
        'show_upload_button': True,
    }
    if request.headers.get('HX-Request'):
        return render(request, 'documents/partials/documents_navigation_partial.html', context)
    return render(request, 'documents/library_history.html', context)


# ============== ENGAGEMENT HTMX ENDPOINTS ==============

@csrf_exempt
@require_POST
@login_required
def toggle_bookmark(request, document_id):
    """
    Toggle bookmark status for a document via HTMX.
    """
    try:
        document = Document.objects.get(id=document_id)
        bookmark, created = DocumentBookmark.objects.get_or_create(
            document=document,
            user=request.user
        )
        
        if not created:
            # Remove bookmark if it already exists
            bookmark.delete()
            is_bookmarked = False
        else:
            is_bookmarked = True
        
        # Trigger analytics update asynchronously
        from .tasks.processing import update_document_analytics
        update_document_analytics.delay(document_id)
        
        # Return partial HTML response
        context = {
            'document': document,
            'is_bookmarked': is_bookmarked,
            'bookmark_count': document.bookmarks.count(),
        }
        return render(request, 'documents/partials/bookmark_button.html', context)
        
    except Document.DoesNotExist:
        return JsonResponse({'error': 'Document not found'}, status=404)


@csrf_exempt
@require_POST
@login_required
def rate_document(request, document_id):
    """
    Rate a document with thumbs up/down via HTMX.
    """
    try:
        document = Document.objects.get(id=document_id)
        rating_value = int(request.POST.get('rating', 0))
        
        if rating_value not in [1, -1]:
            return JsonResponse({'error': 'Invalid rating value'}, status=400)
        
        # Get or create rating
        rating, created = DocumentRating.objects.get_or_create(
            document=document,
            user=request.user,
            defaults={'rating': rating_value}
        )
        
        if not created:
            # Update existing rating
            rating.rating = rating_value
            rating.save()
        
        # Trigger analytics update asynchronously
        from .tasks.processing import update_document_analytics
        update_document_analytics.delay(document_id)
        
        # Get updated analytics
        analytics, _ = DocumentAnalytics.objects.get_or_create(document=document)
        
        # Return partial HTML response
        context = {
            'document': document,
            'user_rating': rating_value,
            'analytics': analytics,
        }
        return render(request, 'documents/partials/rating_buttons.html', context)
        
    except Document.DoesNotExist:
        return JsonResponse({'error': 'Document not found'}, status=404)


@csrf_exempt
@require_POST
@login_required
def track_download(request, document_id):
    """
    HTMX endpoint for tracking document downloads.
    """
    try:
        document = Document.objects.get(id=document_id)
        file_id = request.POST.get('file_id')
        
        from .engagement.models import DocumentDownload
        from .models import DocumentFile
        
        document_file = DocumentFile.objects.get(id=file_id) if file_id else document.latest_version.files.first()
        
        # Create download record - signal handler will update analytics
        DocumentDownload.objects.create(
            document=document,
            document_file=document_file,
            user=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
        )
        
        # Invalidate download count cache
        from django.core.cache import cache
        download_count_cache_key = f'doc_download_count_{document_id}'
        cache.delete(download_count_cache_key)
        
        # Get updated analytics (signal handler should have updated it)
        from .engagement.models import DocumentAnalytics
        analytics, created = DocumentAnalytics.objects.get_or_create(document=document)
        
        # Trigger analytics update asynchronously for full recalculation
        from .tasks.processing import update_document_analytics
        update_document_analytics.delay(document_id)
        
        return JsonResponse({
            'success': True,
            'download_count': analytics.download_count
        })
        
    except Document.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Document not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_POST
@login_required
def share_document(request, document_id):
    """
    Share a document to profile or group via HTMX.
    """
    try:
        document = Document.objects.get(id=document_id)
        share_type = request.POST.get('share_type')  # 'profile', 'group', or 'copy_link'
        
        if share_type == 'copy_link':
            # Track the copy link share
            DocumentShare.objects.create(
                document=document,
                user=request.user,
                platform='copy_link'
            )
            
            # Trigger analytics update asynchronously
            from .tasks.processing import update_document_analytics
            update_document_analytics.delay(document_id)
            
            return JsonResponse({
                'success': True,
                'message': 'Link copied to clipboard',
                'url': request.build_absolute_uri(f"/documents/document/{document_id}/")
            })
        
        elif share_type == 'profile':
            # Share to user's profile feed
            from posts.models import Post
            
            course = getattr(request.user, 'course', None)
            doc_thumbnail = None
            if document.latest_version:
                first_file = document.latest_version.files.first()
                if first_file and (first_file.thumbnail_path or first_file.preview_path):
                    doc_thumbnail = first_file.thumbnail_path or first_file.preview_path
            
            post = Post.objects.create(
                author=request.user,
                course=course,
                gradient_class='none',
                thumbnail=doc_thumbnail,
                content=f"Shared a document: {document.title}",
                shared_document=document
            )
            
            # Track the share
            DocumentShare.objects.create(
                document=document,
                user=request.user,
                platform='profile'
            )
            
            # Trigger analytics update asynchronously
            from .tasks.processing import update_document_analytics
            update_document_analytics.delay(document_id)
            
            return JsonResponse({
                'success': True,
                'message': 'Document shared to your profile'
            })
        
        elif share_type == 'group':
            # Share to a group
            group_id = request.POST.get('group_id')
            if not group_id:
                return JsonResponse({'error': 'Group ID required'}, status=400)
            
            from groups.models import Group, Membership, MembershipStatus
            from posts.models import Post
            
            try:
                group = Group.objects.get(id=group_id)
            except Group.DoesNotExist:
                return JsonResponse({'error': 'Group not found'}, status=404)
            
            # Check if user is an approved member of the group, group creator, or staff
            is_member = Membership.objects.filter(
                group=group,
                user=request.user,
                status=MembershipStatus.APPROVED
            ).exists()
            
            if not is_member and group.created_by != request.user and not request.user.is_staff:
                return JsonResponse({'error': 'Not an approved member of this group'}, status=403)
            
            doc_thumbnail = None
            if document.latest_version:
                first_file = document.latest_version.files.first()
                if first_file and (first_file.thumbnail_path or first_file.preview_path):
                    doc_thumbnail = first_file.thumbnail_path or first_file.preview_path
            
            # Create post in group
            post = Post.objects.create(
                author=request.user,
                group=group,
                course=group.course,
                gradient_class='none',
                thumbnail=doc_thumbnail,
                content=f"Shared a document: {document.title}",
                shared_document=document
            )
            
            # Track the share
            DocumentShare.objects.create(
                document=document,
                user=request.user,
                platform='group'
            )
            
            # Trigger analytics update asynchronously
            from .tasks.processing import update_document_analytics
            update_document_analytics.delay(document_id)
            
            return JsonResponse({
                'success': True,
                'message': f'Document shared to {group.name}'
            })
        
        else:
            return JsonResponse({'error': 'Invalid share type'}, status=400)
        
    except Document.DoesNotExist:
        return JsonResponse({'error': 'Document not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def user_groups_for_sharing(request):
    """
    Return JSON list of groups the authenticated user is an approved member of.
    """
    from groups.models import Membership, MembershipStatus
    memberships = Membership.objects.filter(
        user=request.user,
        status=MembershipStatus.APPROVED
    ).select_related('group').order_by('group__name')
    
    groups_data = [
        {
            'id': m.group.id,
            'name': m.group.name,
            'description': m.group.description or '',
        }
        for m in memberships
    ]
    return JsonResponse({'groups': groups_data})


@csrf_exempt
@login_required
def document_stats(request, document_id):
    """
    Get cached document statistics via HTMX.
    """
    try:
        document = Document.objects.get(id=document_id)
        
        # Get or create analytics
        analytics, _ = DocumentAnalytics.objects.get_or_create(document=document)
        
        # If analytics are stale (older than 5 minutes), trigger update
        from django.utils import timezone
        from datetime import timedelta
        if analytics.last_updated < timezone.now() - timedelta(minutes=5):
            from .tasks.processing import update_document_analytics
            update_document_analytics.delay(document_id)
        
        return JsonResponse({
            'view_count': analytics.view_count,
            'download_count': analytics.download_count,
            'bookmark_count': analytics.bookmark_count,
            'share_count': analytics.share_count,
            'rating_count': analytics.rating_count,
            'positive_rating_count': analytics.positive_rating_count,
            'negative_rating_count': analytics.negative_rating_count,
        })
        
    except Document.DoesNotExist:
        return JsonResponse({'error': 'Document not found'}, status=404)
