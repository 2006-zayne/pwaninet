"""Query selectors for efficient document data access.

These selectors provide optimized queries for common access patterns,
avoiding N+1 query problems and ensuring efficient database usage.
"""

from typing import List, Optional
from django.db.models import Q, Prefetch, Count, Avg
from django.db import models

from documents.models import Document, DocumentVersion, DocumentFile, DocumentAcademicUnit, DocumentTag, DocumentAuthor
from documents.academic.models import AcademicUnit, Semester
from documents.engagement.models import DocumentView, DocumentDownload, DocumentBookmark, DocumentAnalytics


class DocumentSelector:
    """Selector for optimized document queries."""
    
    @staticmethod
    def get_document_with_relations(document_id: int) -> Optional[Document]:
        """Get a document with all related data in a single query."""
        return Document.objects.select_related(
            'category',
            'uploaded_by',
            'moderation__status',
            'analytics',
        ).prefetch_related(
            Prefetch(
                'versions',
                queryset=DocumentVersion.objects.select_related('created_by').prefetch_related(
                    Prefetch('files', queryset=DocumentFile.objects.all())
                )
            ),
            Prefetch(
                'academic_units',
                queryset=DocumentAcademicUnit.objects.select_related(
                    'academic_unit',
                    'academic_level',
                    'semester',
                    'academic_year'
                ).only(
                    'academic_unit__code',
                    'academic_unit__name',
                    'academic_level__level',
                    'academic_level__name',
                    'semester__number',
                    'semester__academic_year__code',
                    'academic_year__code'
                )
            ),
            Prefetch(
                'document_tags',
                queryset=DocumentTag.objects.select_related('tag').only('tag__name', 'tag__slug')
            ),
            Prefetch(
                'authors',
                queryset=DocumentAuthor.objects.only('name', 'author_type')
            ),
        ).filter(id=document_id).first()
    
    @staticmethod
    def list_documents_for_home(
        limit: int = 20,
        category: Optional[str] = None,
        academic_unit: Optional[str] = None,
        user=None,
    ) -> List[Document]:
        """List documents for home page with personalization."""
        queryset = Document.objects.filter(
            status='ready',
            visibility='public',
        ).select_related(
            'category',
            'uploaded_by',
            'analytics',
        ).prefetch_related(
            Prefetch(
                'academic_units',
                queryset=DocumentAcademicUnit.objects.select_related(
                    'academic_unit'
                ).only('academic_unit__code', 'academic_unit__name')
            ),
        )
        
        if category:
            queryset = queryset.filter(category__code=category)
        
        if academic_unit:
            queryset = queryset.filter(
                academic_units__academic_unit__code=academic_unit
            )
        
        documents = list(queryset.order_by('-created_at')[:limit])
        
        # Apply student interest prioritization if user is provided
        if user and user.is_authenticated:
            documents = DocumentSelector._apply_student_relevance_sorting(documents, user)
        
        return documents
    
    @staticmethod
    def get_popular_documents(limit: int = 10, user=None) -> List[Document]:
        """Get popular documents based on long-term popularity score."""
        from ..search.models import DocumentSearchIndex
        
        queryset = DocumentSearchIndex.objects.filter(
            document__status='ready',
            document__visibility='public',
        ).select_related('document__analytics').order_by('-popularity_score')[:limit]
        
        documents = [index.document for index in queryset]
        
        # Apply student interest prioritization if user is provided
        if user and user.is_authenticated:
            documents = DocumentSelector._apply_student_relevance_sorting(documents, user)
        
        return documents
    
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
    def get_trending_documents(limit: int = 10, days: int = 7, user=None) -> List[Document]:
        """Get trending documents based on recent engagement using search index."""
        from ..search.models import DocumentSearchIndex
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Use search index for trending score
        queryset = DocumentSearchIndex.objects.filter(
            document__status='ready',
            document__visibility='public',
            document__created_at__gte=cutoff_date,
        ).select_related('document').order_by('-trending_score')[:limit]
        
        documents = [index.document for index in queryset]
        
        # Apply student interest prioritization if user is provided
        if user and user.is_authenticated:
            documents = DocumentSelector._apply_student_relevance_sorting(documents, user)
        
        return documents
    
    @staticmethod
    def _apply_student_relevance_sorting(documents: List[Document], user) -> List[Document]:
        """Sort documents by student's academic relevance."""
        try:
            # Use new User model fields directly
            if not user or not user.programme:
                return documents
            
            # Get user's academic units with optimized query
            from ..academic.models import ProgrammeUnit
            programme_units = ProgrammeUnit.objects.filter(
                programme=user.programme
            ).select_related('academic_unit').only('academic_unit__code')
            user_unit_codes = {pu.academic_unit.code for pu in programme_units}
            
            if not user_unit_codes:
                return documents
            
            # Score documents based on relevance
            def relevance_score(doc):
                score = 0
                doc_units = set(
                    au.academic_unit.code 
                    for au in doc.academic_units.all().only('academic_unit__code')
                )
                
                # High boost for matching academic units
                if doc_units & user_unit_codes:
                    score += 10
                
                # Medium boost for matching academic level
                if user.academic_level:
                    doc_levels = set(
                        au.academic_level.level 
                        for au in doc.academic_units.all().only('academic_level__level')
                    )
                    if user.academic_level.level in doc_levels:
                        score += 5
                
                # Medium boost for matching semester
                if user.semester:
                    doc_semesters = set(
                        au.semester.id 
                        for au in doc.academic_units.all().only('semester__id')
                    )
                    if user.semester.id in doc_semesters:
                        score += 3
                
                return score
            
            # Sort by relevance score
            documents.sort(key=relevance_score, reverse=True)
            
            return documents
            
        except Exception:
            return documents
    
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
        user=None,
    ) -> List[Document]:
        """Search documents with advanced full-text search."""
        from ..services.search_service import SearchService
        
        search_service = SearchService()
        documents, total_count = search_service.search(
            query=query,
            filters=filters,
            sort_by='relevance',
            page=1,
            per_page=limit,
            user=user,
        )
        
        return documents
    
    @staticmethod
    def get_document_statistics(document_id: int) -> dict:
        """Get engagement statistics for a document using cached analytics."""
        from ..engagement.models import DocumentAnalytics
        
        document = Document.objects.filter(id=document_id).first()
        if not document:
            return {}
        
        # Try to get cached analytics first
        analytics = DocumentAnalytics.objects.filter(document=document).first()
        
        if analytics:
            return {
                'view_count': analytics.view_count,
                'download_count': analytics.download_count,
                'bookmark_count': analytics.bookmark_count,
                'share_count': analytics.share_count,
                'rating_count': analytics.rating_count,
                'positive_rating_count': analytics.positive_rating_count,
                'negative_rating_count': analytics.negative_rating_count,
                'trending_score': analytics.trending_score,
                'popularity_score': analytics.popularity_score,
                'version_count': document.versions.count(),
            }
        else:
            # Fallback to COUNT queries if analytics not available
            return {
                'view_count': document.views.count(),
                'download_count': document.downloads.count(),
                'bookmark_count': document.bookmarks.count(),
                'share_count': document.shares.count(),
                'rating_count': document.ratings.count(),
                'positive_rating_count': document.ratings.filter(rating=1).count(),
                'negative_rating_count': document.ratings.filter(rating=-1).count(),
                'trending_score': 0,
                'popularity_score': 0,
                'version_count': document.versions.count(),
            }
    
    @staticmethod
    def get_related_documents(document: Document, limit: int = 6) -> List[Document]:
        """Get related documents based on multiple relevance factors."""
        from ..search.models import DocumentSearchIndex
        
        # Get document's academic units, tags, and category
        doc_units = set(
            au.academic_unit.code 
            for au in document.academic_units.all()
        )
        doc_tags = set(
            dt.tag.slug 
            for dt in document.document_tags.all()
        )
        doc_category = document.category.code
        
        # Start with base queryset
        queryset = Document.objects.filter(
            status='ready',
            visibility='public',
        ).exclude(id=document.id).select_related(
            'category',
        ).prefetch_related(
            'academic_units__academic_unit',
            'document_tags__tag',
        )
        
        # Score documents based on relevance
        def relevance_score(doc):
            score = 0
            
            # Shared academic units (high relevance)
            doc_doc_units = set(
                au.academic_unit.code 
                for au in doc.academic_units.all()
            )
            if doc_units & doc_doc_units:
                score += 10 * len(doc_units & doc_doc_units)
            
            # Shared category (medium relevance)
            if doc.category.code == doc_category:
                score += 5
            
            # Shared tags (medium relevance)
            doc_doc_tags = set(
                dt.tag.slug 
                for dt in doc.document_tags.all()
            )
            if doc_tags & doc_doc_tags:
                score += 3 * len(doc_tags & doc_doc_tags)
            
            # Similar title (lower relevance)
            if document.title.lower() in doc.title.lower() or doc.title.lower() in document.title.lower():
                score += 2
            
            return score
        
        # Get all candidate documents and score them
        candidates = list(queryset[:50])  # Limit to 50 candidates for performance
        candidates.sort(key=relevance_score, reverse=True)
        
        return candidates[:limit]


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
