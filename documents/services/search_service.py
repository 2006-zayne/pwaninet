"""Search service for document search operations.

This service provides a search-agnostic interface, allowing migration
between different search backends (PostgreSQL FTS, Meilisearch, ElasticSearch).
"""

import logging
from typing import List, Dict, Optional
from django.db.models import Q, F
from django.contrib.postgres.search import SearchVector

from ..documents.models import Document
from ..search.models import DocumentSearchIndex
from ..academic.models import AcademicUnit

logger = logging.getLogger(__name__)


class SearchService:
    """Service for handling document search operations."""
    
    def __init__(self):
        self.use_postgres_fts = True  # Can be switched to Meilisearch/ElasticSearch
    
    def search(
        self,
        query: str,
        filters: Dict = None,
        sort_by: str = 'relevance',
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[List[Document], int]:
        """Search for documents."""
        if self.use_postgres_fts:
            return self._search_postgres(query, filters, sort_by, page, per_page)
        else:
            # Fallback to basic search
            return self._search_basic(query, filters, sort_by, page, per_page)
    
    def _search_postgres(
        self,
        query: str,
        filters: Dict,
        sort_by: str,
        page: int,
        per_page: int,
    ) -> tuple[List[Document], int]:
        """Search using PostgreSQL Full Text Search."""
        # Build search vector query
        search_query = SearchVector('title', 'description', config='english')
        
        # Start with search index query
        queryset = DocumentSearchIndex.objects.annotate(
            search=search_query
        ).filter(search=query)
        
        # Apply filters
        if filters:
            queryset = self._apply_filters(queryset, filters)
        
        # Apply sorting
        queryset = self._apply_sorting(queryset, sort_by)
        
        # Get total count
        total_count = queryset.count()
        
        # Paginate
        offset = (page - 1) * per_page
        queryset = queryset[offset:offset + per_page]
        
        # Get actual documents
        document_ids = [index.document_id for index in queryset]
        documents = Document.objects.filter(id__in=document_ids)
        
        logger.info(f"PostgreSQL FTS search for '{query}' returned {total_count} results")
        return documents, total_count
    
    def _search_basic(
        self,
        query: str,
        filters: Dict,
        sort_by: str,
        page: int,
        per_page: int,
    ) -> tuple[List[Document], int]:
        """Basic search using Django ORM."""
        queryset = Document.objects.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )
        
        # Apply filters
        if filters:
            queryset = self._apply_document_filters(queryset, filters)
        
        # Apply sorting
        queryset = self._apply_document_sorting(queryset, sort_by)
        
        # Get total count
        total_count = queryset.count()
        
        # Paginate
        offset = (page - 1) * per_page
        documents = queryset[offset:offset + per_page]
        
        logger.info(f"Basic search for '{query}' returned {total_count} results")
        return documents, total_count
    
    def _apply_filters(self, queryset, filters: Dict):
        """Apply filters to search index query."""
        if filters.get('category'):
            queryset = queryset.filter(category_code=filters['category'])
        
        if filters.get('academic_unit'):
            queryset = queryset.filter(academic_unit_codes__contains=[filters['academic_unit']])
        
        if filters.get('semester'):
            queryset = queryset.filter(semester_code=filters['semester'])
        
        if filters.get('academic_year'):
            queryset = queryset.filter(academic_year_code=filters['academic_year'])
        
        if filters.get('file_type'):
            queryset = queryset.filter(file_types__contains=[filters['file_type']])
        
        if filters.get('tags'):
            queryset = queryset.filter(tag_slugs__contains=filters['tags'])
        
        return queryset
    
    def _apply_document_filters(self, queryset, filters: Dict):
        """Apply filters to document query."""
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
        
        return queryset
    
    def _apply_sorting(self, queryset, sort_by: str):
        """Apply sorting to search index query."""
        sort_options = {
            'relevance': '-popularity_score',
            'newest': '-created_at',
            'oldest': 'created_at',
            'downloads': '-download_count',
            'rating': '-rating_average',
        }
        
        order_field = sort_options.get(sort_by, '-popularity_score')
        return queryset.order_by(order_field)
    
    def _apply_document_sorting(self, queryset, sort_by: str):
        """Apply sorting to document query."""
        sort_options = {
            'relevance': '-created_at',  # Fallback for basic search
            'newest': '-created_at',
            'oldest': 'created_at',
        }
        
        order_field = sort_options.get(sort_by, '-created_at')
        return queryset.order_by(order_field)
    
    def index_document(self, document: Document):
        """Index a document for search."""
        # Get all related data
        academic_units = document.academic_units.select_related('academic_unit', 'semester', 'academic_year')
        tags = document.document_tags.select_related('tag')
        authors = document.authors.all()
        latest_version = document.latest_version
        
        # Build index data
        index_data = {
            'document': document,
            'title': document.title,
            'description': document.description,
            'category_code': document.category.code,
            'category_name': document.category.name,
            'academic_unit_codes': [au.academic_unit.code for au in academic_units],
            'academic_unit_names': [au.academic_unit.name for au in academic_units],
            'semester_code': f"{academic_units[0].semester.number}-{academic_units[0].semester.academic_year.code}" if academic_units else None,
            'academic_year_code': academic_units[0].academic_year.code if academic_units else None,
            'tag_names': [dt.tag.name for dt in tags],
            'tag_slugs': [dt.tag.slug for dt in tags],
            'author_names': [a.name or a.user.get_full_name() for a in authors if a.user],
            'author_usernames': [a.user.username for a in authors if a.user],
            'file_types': [],
            'file_count': 0,
            'created_at': document.created_at,
            'updated_at': document.updated_at,
            'published_at': document.published_at,
        }
        
        # Add file data if version exists
        if latest_version:
            files = latest_version.files.all()
            index_data['file_types'] = [f.extension for f in files]
            index_data['file_count'] = files.count()
        
        # Get engagement metrics
        from ..engagement.models import DocumentView, DocumentDownload, DocumentBookmark, DocumentRating
        index_data['view_count'] = document.views.count()
        index_data['download_count'] = document.downloads.count()
        index_data['bookmark_count'] = document.bookmarks.count()
        index_data['share_count'] = document.shares.count()
        
        ratings = document.ratings.all()
        if ratings.exists():
            index_data['rating_average'] = sum(r.rating for r in ratings) / len(ratings)
            index_data['rating_count'] = len(ratings)
        
        # Create or update index
        index, created = DocumentSearchIndex.objects.update_or_create(
            document=document,
            defaults=index_data
        )
        
        # Update search vector if using PostgreSQL FTS
        if self.use_postgres_fts:
            from django.contrib.postgres.search import SearchVector
            index.search_vector = SearchVector(
                'title', 'description', 'tag_names', 'author_names',
                config='english'
            )
            index.save(update_fields=['search_vector'])
        
        # Update popularity score
        index.update_popularity_score()
        
        logger.info(f"Indexed document {document.id}")
        return index
    
    def remove_from_index(self, document: Document):
        """Remove a document from the search index."""
        try:
            index = DocumentSearchIndex.objects.get(document=document)
            index.delete()
            logger.info(f"Removed document {document.id} from search index")
        except DocumentSearchIndex.DoesNotExist:
            logger.warning(f"Document {document.id} not in search index")
