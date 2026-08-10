"""Search service for document search operations.

This service provides a search-agnostic interface, allowing migration
between different search backends (PostgreSQL FTS, Meilisearch, ElasticSearch).
"""

import logging
from typing import List, Dict, Optional, Tuple
from django.db.models import Q, F, Value, FloatField, Case, When
from django.contrib.postgres.search import (
    SearchVector, SearchQuery, SearchRank, TrigramSimilarity,
    TrigramWordSimilarity
)
from django.db.models.functions import Concat

from ..documents.models import Document
from ..search.models import DocumentSearchIndex
from ..academic.models import AcademicUnit

logger = logging.getLogger(__name__)


class SearchService:
    """Service for handling document search operations."""
    
    def __init__(self):
        self.use_postgres_fts = True  # Can be switched to Meilisearch/ElasticSearch
        self.enable_fuzzy_search = True  # Enable pg_trgm fuzzy matching
    
    def search(
        self,
        query: str,
        filters: Dict = None,
        sort_by: str = 'relevance',
        page: int = 1,
        per_page: int = 20,
        user=None,
    ) -> tuple[List[Document], int]:
        """Search for documents with advanced ranking."""
        if not query or not query.strip():
            return [], 0
        
        if self.use_postgres_fts:
            return self._search_postgres(query, filters, sort_by, page, per_page, user)
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
        user=None,
    ) -> tuple[List[Document], int]:
        """Search using PostgreSQL Full Text Search with weighted ranking."""
        from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
        
        # Clean and normalize query
        query = query.strip()
        
        # Create search query with proper configuration for stemming
        search_query = SearchQuery(query, config='english', search_type='websearch')
        
        # Build weighted search vectors
        # Title: A weight (highest)
        # Tags, Academic Units: B weight (high)
        # Category, Description, Authors: C weight (medium)
        # OCR text, Filename: D weight (lower)
        title_vector = SearchVector('title', weight='A', config='english')
        tags_vector = SearchVector('tag_names', weight='B', config='english')
        academic_units_vector = SearchVector('academic_unit_names', weight='B', config='english')
        category_vector = SearchVector('category_name', weight='C', config='english')
        description_vector = SearchVector('description', weight='C', config='english')
        authors_vector = SearchVector('author_names', weight='C', config='english')
        ocr_vector = SearchVector('ocr_text', weight='D', config='english')
        filename_vector = SearchVector('primary_filename', weight='D', config='english')
        
        # Combine all weighted vectors
        combined_vector = (
            title_vector + tags_vector + academic_units_vector +
            category_vector + description_vector + authors_vector +
            ocr_vector + filename_vector
        )
        
        # Start with search index query
        queryset = DocumentSearchIndex.objects.annotate(
            search=combined_vector,
            rank=SearchRank(combined_vector, search_query)
        ).filter(search=search_query)
        
        # Add student interest prioritization if user is provided
        if user and user.is_authenticated:
            queryset = self._apply_student_interest_boost(queryset, user)
        
        # Apply filters
        if filters:
            queryset = self._apply_filters(queryset, filters)
        
        # Apply sorting
        queryset = self._apply_sorting(queryset, sort_by)
        
        # Get total count
        total_count = queryset.count()
        
        # If FTS returns no results, fall back to fuzzy search
        if total_count == 0 and self.enable_fuzzy_search:
            logger.info(f"FTS returned no results for '{query}', falling back to fuzzy search")
            return self._search_with_fuzzy(query, filters, sort_by, page, per_page)
        
        # Paginate
        offset = (page - 1) * per_page
        queryset = queryset[offset:offset + per_page]
        
        # Get actual documents with optimized queries
        document_ids = [index.document_id for index in queryset]
        documents = Document.objects.filter(
            id__in=document_ids
        ).select_related(
            'category', 'uploaded_by'
        ).prefetch_related(
            'academic_units__academic_unit',
            'document_tags__tag'
        )
        
        # Preserve the search ranking order
        documents = sorted(
            documents,
            key=lambda doc: document_ids.index(doc.id)
        )
        
        logger.info(f"PostgreSQL FTS search for '{query}' returned {total_count} results")
        return documents, total_count
    
    def _apply_student_interest_boost(self, queryset, user):
        """Apply ranking boost based on student's academic context."""
        try:
            # Get user's academic context
            from users.models import UserProfile
            profile = getattr(user, 'profile', None)
            
            if not profile:
                return queryset
            
            # Get user's programme, academic units, semester
            user_units = []
            if profile.programme:
                # Get units for user's programme
                from ..academic.models import ProgrammeUnit
                programme_units = ProgrammeUnit.objects.filter(
                    programme=profile.programme
                ).select_related('academic_unit')
                user_units = [pu.academic_unit.code for pu in programme_units]
            
            if user_units:
                # Add annotation for academic relevance boost
                queryset = queryset.annotate(
                    academic_relevance=Case(
                        When(academic_unit_codes__overlap=user_units, then=Value(1.0)),
                        default=Value(0.0),
                        output_field=FloatField()
                    )
                )
                
                # Boost the rank for academically relevant documents
                queryset = queryset.annotate(
                    boosted_rank=F('rank') + F('academic_relevance') * 0.5
                )
            
            return queryset
            
        except Exception as e:
            logger.warning(f"Error applying student interest boost: {e}")
            return queryset
    
    def _search_with_fuzzy(
        self,
        query: str,
        filters: Dict,
        sort_by: str,
        page: int,
        per_page: int,
    ) -> tuple[List[Document], int]:
        """Search with fuzzy matching using pg_trgm."""
        from django.contrib.postgres.search import TrigramSimilarity
        
        queryset = DocumentSearchIndex.objects.annotate(
            similarity=TrigramSimilarity('searchable_text', query)
        ).filter(similarity__gte=0.3)  # Reasonable threshold
        
        # Apply filters
        if filters:
            queryset = self._apply_filters(queryset, filters)
        
        # Sort by similarity
        queryset = queryset.order_by('-similarity')
        
        # Get total count
        total_count = queryset.count()
        
        # Paginate
        offset = (page - 1) * per_page
        queryset = queryset[offset:offset + per_page]
        
        # Get actual documents
        document_ids = [index.document_id for index in queryset]
        documents = Document.objects.filter(id__in=document_ids)
        
        logger.info(f"Fuzzy search for '{query}' returned {total_count} results")
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
        
        if filters.get('academic_level'):
            queryset = queryset.filter(academic_level_code=filters['academic_level'])
        
        if filters.get('semester'):
            queryset = queryset.filter(semester_code=filters['semester'])
        
        if filters.get('academic_year'):
            queryset = queryset.filter(academic_year_code=filters['academic_year'])
        
        if filters.get('programme'):
            queryset = queryset.filter(programme_code=filters['programme'])
        
        if filters.get('school'):
            queryset = queryset.filter(school_code=filters['school'])
        
        if filters.get('department'):
            queryset = queryset.filter(department_code=filters['department'])
        
        if filters.get('academic_units'):
            # Filter by multiple academic units (for personalized "my units" filter)
            queryset = queryset.filter(academic_unit_codes__overlap=filters['academic_units'])
        
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
        
        if filters.get('academic_level'):
            queryset = queryset.filter(
                academic_units__academic_level__level=filters['academic_level']
            )
        
        if filters.get('semester'):
            queryset = queryset.filter(
                academic_units__semester__id=filters['semester']
            )
        
        if filters.get('academic_year'):
            queryset = queryset.filter(
                academic_units__academic_year__id=filters['academic_year']
            )
        
        if filters.get('programme'):
            # Filter by programme through curriculum mapping
            from ..academic.models import ProgrammeUnit
            programme_units = ProgrammeUnit.objects.filter(
                programme_id=filters['programme']
            ).values_list('academic_unit_id', flat=True)
            queryset = queryset.filter(
                academic_units__academic_unit_id__in=programme_units
            )
        
        if filters.get('academic_units'):
            # Filter by multiple academic units
            queryset = queryset.filter(
                academic_units__academic_unit_id__in=filters['academic_units']
            )
        
        return queryset
    
    def _apply_sorting(self, queryset, sort_by: str):
        """Apply sorting to search index query."""
        sort_options = {
            'relevance': '-rank',
            'newest': '-created_at',
            'oldest': 'created_at',
            'downloads': '-download_count',
            'rating': '-rating_average',
            'trending': '-trending_score',
            'popular': '-popularity_score',
        }
        
        # Check if we have boosted_rank from student interest
        if hasattr(queryset, 'model') and hasattr(queryset.model, 'boosted_rank'):
            sort_options['relevance'] = '-boosted_rank'
        
        order_field = sort_options.get(sort_by, '-rank')
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
    
    def get_search_suggestions(self, query: str, limit: int = 10) -> List[str]:
        """Get autocomplete suggestions based on query."""
        if not query or len(query) < 2:
            return []
        
        from django.contrib.postgres.search import TrigramWordSimilarity
        
        # Search in titles for suggestions
        suggestions = DocumentSearchIndex.objects.annotate(
            similarity=TrigramWordSimilarity('title', query)
        ).filter(similarity__gte=0.3).order_by('-similarity')[:limit]
        
        return [suggestion.title for suggestion in suggestions]
    
    def get_did_you_mean(self, query: str) -> Optional[str]:
        """Get spelling correction suggestion using fuzzy matching."""
        if not query or len(query) < 3:
            return None
        
        from django.contrib.postgres.search import TrigramSimilarity
        
        # Find similar titles with high similarity
        similar = DocumentSearchIndex.objects.annotate(
            similarity=TrigramSimilarity('title', query)
        ).filter(similarity__gte=0.6).order_by('-similarity').first()
        
        if similar and similar.similarity >= 0.7:
            return similar.title
        
        return None
    
    def index_document(self, document: Document):
        """Index a document for search with weighted vectors."""
        # Get all related data
        academic_units = document.academic_units.select_related('academic_unit', 'semester', 'academic_year')
        tags = document.document_tags.select_related('tag')
        authors = document.authors.all()
        latest_version = document.latest_version
        
        # Build combined searchable text for trigram search
        searchable_text_parts = [
            document.title,
            document.description,
            document.category.name,
        ]
        
        # Add academic unit names
        searchable_text_parts.extend([au.academic_unit.name for au in academic_units])
        
        # Add tag names
        searchable_text_parts.extend([dt.tag.name for dt in tags])
        
        # Add author names
        searchable_text_parts.extend([a.name or (a.user.get_full_name() if a.user else '') for a in authors])
        
        # Get primary filename
        primary_filename = ''
        if latest_version:
            files = latest_version.files.all()
            if files.exists():
                primary_filename = files.first().original_filename
                searchable_text_parts.append(primary_filename)
        
        searchable_text = ' '.join(filter(None, searchable_text_parts))
        
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
            'author_names': [a.name or (a.user.get_full_name() if a.user else '') for a in authors],
            'author_usernames': [a.user.username for a in authors if a.user],
            'file_types': [],
            'file_count': 0,
            'primary_filename': primary_filename,
            'searchable_text': searchable_text,
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
        try:
            from documents.engagement.models import DocumentView, DocumentDownload, DocumentBookmark, DocumentRating
            index_data['view_count'] = document.views.count()
            index_data['download_count'] = document.downloads.count()
            index_data['bookmark_count'] = document.bookmarks.count()
            index_data['share_count'] = document.shares.count()
            
            ratings = document.ratings.all()
            if ratings.exists():
                index_data['rating_average'] = sum(r.rating for r in ratings) / len(ratings)
                index_data['rating_count'] = len(ratings)
        except Exception as e:
            # Fallback if engagement models not available
            logger.warning(f"Engagement models not available, skipping engagement metrics: {e}")
            index_data['view_count'] = 0
            index_data['download_count'] = 0
            index_data['bookmark_count'] = 0
            index_data['share_count'] = 0
        
        # Create or update index
        index, created = DocumentSearchIndex.objects.update_or_create(
            document=document,
            defaults=index_data
        )
        
        # Update weighted search vectors if using PostgreSQL FTS
        if self.use_postgres_fts:
            from django.contrib.postgres.search import SearchVector
            
            # Update individual weighted vectors
            index.title_vector = SearchVector('title', weight='A', config='english')
            index.tags_vector = SearchVector('tag_names', weight='B', config='english')
            index.academic_units_vector = SearchVector('academic_unit_names', weight='B', config='english')
            index.category_vector = SearchVector('category_name', weight='C', config='english')
            index.description_vector = SearchVector('description', weight='C', config='english')
            index.authors_vector = SearchVector('author_names', weight='C', config='english')
            index.ocr_text_vector = SearchVector('ocr_text', weight='D', config='english')
            index.filename_vector = SearchVector('primary_filename', weight='D', config='english')
            
            # Update combined search vector
            index.search_vector = (
                SearchVector('title', weight='A', config='english') +
                SearchVector('tag_names', weight='B', config='english') +
                SearchVector('academic_unit_names', weight='B', config='english') +
                SearchVector('category_name', weight='C', config='english') +
                SearchVector('description', weight='C', config='english') +
                SearchVector('author_names', weight='C', config='english') +
                SearchVector('ocr_text', weight='D', config='english') +
                SearchVector('primary_filename', weight='D', config='english')
            )
            
            index.save(
                update_fields=[
                    'title_vector', 'tags_vector', 'academic_units_vector',
                    'category_vector', 'description_vector', 'authors_vector',
                    'ocr_text_vector', 'filename_vector', 'search_vector'
                ]
            )
        
        # Update popularity and trending scores
        index.update_popularity_score()
        index.update_trending_score()
        
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
