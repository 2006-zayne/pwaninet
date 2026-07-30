"""Query selectors for efficient document data access.

These selectors provide optimized queries for common access patterns,
avoiding N+1 query problems and ensuring efficient database usage.
"""

from typing import List, Optional
from django.db.models import Q, Prefetch, Count, Avg
from django.db import models

from ..documents.models import Document, DocumentVersion, DocumentFile
from ..academic.models import AcademicUnit, Semester
from ..engagement.models import DocumentView, DocumentDownload, DocumentBookmark


class DocumentSelector:
    """Selector for optimized document queries."""
    
    @staticmethod
    def get_document_with_relations(document_id: int) -> Optional[Document]:
        """Get a document with all related data in a single query."""
        return Document.objects.select_related(
            'category',
            'uploaded_by',
            'moderation__status',
        ).prefetch_related(
            Prefetch(
                'versions',
                queryset=DocumentVersion.objects.select_related('created_by').prefetch_related(
                    Prefetch('files', queryset=DocumentFile.objects.all())
                )
            ),
            'academic_units__academic_unit',
            'academic_units__semester',
            'academic_units__academic_year',
            'document_tags__tag',
            'authors',
        ).filter(id=document_id).first()
    
    @staticmethod
    def list_documents_for_home(
        limit: int = 20,
        category: Optional[str] = None,
        academic_unit: Optional[str] = None,
    ) -> List[Document]:
        """List documents for home page with optimized query."""
        queryset = Document.objects.filter(
            status='ready',
            visibility='public',
        ).select_related(
            'category',
            'uploaded_by',
        ).prefetch_related(
            'academic_units__academic_unit',
        )
        
        if category:
            queryset = queryset.filter(category__code=category)
        
        if academic_unit:
            queryset = queryset.filter(
                academic_units__academic_unit__code=academic_unit
            )
        
        return queryset.order_by('-created_at')[:limit]
    
    @staticmethod
    def list_documents_for_user(
        user_id: int,
        document_type: str = 'uploads',
        limit: int = 20,
    ) -> List[Document]:
        """List documents for a user's library."""
        if document_type == 'uploads':
            queryset = Document.objects.filter(uploaded_by_id=user_id)
        elif document_type == 'bookmarks':
            queryset = Document.objects.filter(
                bookmarks__user_id=user_id
            ).distinct()
        elif document_type == 'downloads':
            queryset = Document.objects.filter(
                downloads__user_id=user_id
            ).distinct()
        else:
            queryset = Document.objects.filter(
                views__user_id=user_id
            ).distinct()
        
        return queryset.select_related(
            'category',
        ).prefetch_related(
            'academic_units__academic_unit',
        ).order_by('-created_at')[:limit]
    
    @staticmethod
    def get_trending_documents(limit: int = 10, days: int = 7) -> List[Document]:
        """Get trending documents based on recent engagement."""
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        return Document.objects.filter(
            status='ready',
            visibility='public',
            created_at__gte=cutoff_date,
        ).annotate(
            recent_views=Count(
                'views',
                filter=Q(views__viewed_at__gte=cutoff_date)
            ),
            recent_downloads=Count(
                'downloads',
                filter=Q(downloads__downloaded_at__gte=cutoff_date)
            ),
            engagement_score=models.ExpressionWrapper(
                models.F('recent_views') * 1 + models.F('recent_downloads') * 3,
                output_field=models.IntegerField()
            )
        ).select_related(
            'category',
        ).order_by('-engagement_score')[:limit]
    
    @staticmethod
    def get_documents_by_category(
        category_code: str,
        limit: int = 20,
    ) -> List[Document]:
        """Get documents by category."""
        return Document.objects.filter(
            status='ready',
            visibility='public',
            category__code=category_code,
        ).select_related(
            'category',
            'uploaded_by',
        ).prefetch_related(
            'academic_units__academic_unit',
        ).order_by('-created_at')[:limit]
    
    @staticmethod
    def get_documents_by_academic_unit(
        unit_code: str,
        limit: int = 20,
    ) -> List[Document]:
        """Get documents by academic unit."""
        return Document.objects.filter(
            status='ready',
            visibility='public',
            academic_units__academic_unit__code=unit_code,
        ).select_related(
            'category',
        ).prefetch_related(
            'academic_units__academic_unit',
        ).order_by('-created_at')[:limit]
    
    @staticmethod
    def search_documents(
        query: str,
        filters: dict = None,
        limit: int = 20,
    ) -> List[Document]:
        """Search documents with filters."""
        queryset = Document.objects.filter(
            status='ready',
            visibility='public',
        ).filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )
        
        if filters:
            if filters.get('category'):
                queryset = queryset.filter(category__code=filters['category'])
            if filters.get('academic_unit'):
                queryset = queryset.filter(
                    academic_units__academic_unit__code=filters['academic_unit']
                )
            if filters.get('semester'):
                queryset = queryset.filter(
                    academic_units__semester__code=filters['semester']
                )
        
        return queryset.select_related(
            'category',
        ).prefetch_related(
            'academic_units__academic_unit',
        ).order_by('-created_at')[:limit]
    
    @staticmethod
    def get_document_statistics(document_id: int) -> dict:
        """Get engagement statistics for a document."""
        document = Document.objects.filter(id=document_id).first()
        if not document:
            return {}
        
        return {
            'view_count': document.views.count(),
            'download_count': document.downloads.count(),
            'bookmark_count': document.bookmarks.count(),
            'share_count': document.shares.count(),
            'rating_count': document.ratings.count(),
            'average_rating': document.ratings.aggregate(
                avg=Avg('rating')
            )['avg'] or 0,
            'version_count': document.versions.count(),
        }


class AcademicUnitSelector:
    """Selector for academic unit queries."""
    
    @staticmethod
    def get_units_for_programme(programme_id: int) -> List[AcademicUnit]:
        """Get all academic units for a programme."""
        from ..academic.models import ProgrammeUnit
        
        return AcademicUnit.objects.filter(
            programme_units__programme_id=programme_id
        ).distinct()
    
    @staticmethod
    def get_units_with_documents(
        semester_id: Optional[int] = None,
        limit: int = 50,
    ) -> List[AcademicUnit]:
        """Get academic units that have documents."""
        queryset = AcademicUnit.objects.filter(
            documents__isnull=False
        ).annotate(
            document_count=Count('documents')
        ).distinct()
        
        if semester_id:
            queryset = queryset.filter(
                documents__semester_id=semester_id
            )
        
        return queryset.order_by('-document_count')[:limit]
