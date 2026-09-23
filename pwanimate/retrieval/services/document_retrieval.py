"""
Document Semantic Retrieval Service for Pwanimate.

Performs vector similarity search against DocumentChunk embeddings using pgvector,
with strict pre-retrieval authorization candidate filtering, version integrity,
and citation generation.
"""

import logging
import uuid
from typing import Any, List, Optional
from django.db.models import Q
from pgvector.django import CosineDistance

from pwanimate.models import DocumentChunk
from pwanimate.retrieval.types import RetrievalRequest, RetrievalResult, SourceType
from pwanimate.ai.embeddings.base import BaseEmbeddingProvider, EmbeddingProviderError
from pwanimate.ai.embeddings.factory import get_embedding_provider

logger = logging.getLogger(__name__)


class DocumentSemanticRetrievalService:
    """Service handling semantic retrieval over authorized DocumentChunks."""

    def __init__(self, embedding_provider: Optional[BaseEmbeddingProvider] = None):
        self._provider = embedding_provider

    @property
    def provider(self) -> BaseEmbeddingProvider:
        """Lazily resolve active embedding provider."""
        if self._provider is None:
            self._provider = get_embedding_provider()
        return self._provider

    def build_candidate_queryset(self, user: Optional[Any] = None, filters: Optional[dict] = None):
        """
        Build pre-retrieval candidate queryset enforcing strict authorization invariants.

        Invariants:
        1. DocumentChunk must be active (`is_active=True`).
        2. Embedding status must be 'completed' with non-null embedding.
        3. Embedding model must match current active provider model name.
        4. Parent Document status must be 'ready'.
        5. Parent Document must be available (`is_available=True`).
        6. Visibility rules:
           - Public: accessible to everyone.
           - Private: accessible only to uploader, staff, superuser, or student leadership.
           - Restricted: accessible to uploader, staff/superuser/leadership, or students
             enrolled in matching academic programme / course units.
        """
        model_name = self.provider.get_model_name()

        # Base candidate queryset
        qs = DocumentChunk.objects.filter(
            is_active=True,
            embedding_status='completed',
            embedding_model=model_name,
            embedding__isnull=False,
            document__status='ready',
            document__is_available=True,
        )

        # Authorization filter
        if user and getattr(user, 'is_authenticated', False):
            # Staff, superuser, and executive student leaders have administrative read access
            global_role = getattr(user, 'global_role', None)
            is_admin_or_leader = (
                user.is_staff or
                user.is_superuser or
                global_role in ['PRESIDENT', 'DELEGATE']
            )

            if not is_admin_or_leader:
                # Build student visibility query
                visibility_q = Q(document__visibility='public') | Q(document__uploaded_by=user)

                # Restricted visibility check
                restricted_q = Q(document__visibility='restricted')
                has_restricted_match = False

                # 1. Match student's enrolled programme units
                programme = getattr(user, 'programme', None)
                if programme:
                    visibility_q |= (
                        restricted_q &
                        Q(document__academic_units__academic_unit__programme_units__programme=programme)
                    )
                    has_restricted_match = True

                # 2. Legacy fallback to course
                course = getattr(user, 'course', None)
                if course and not has_restricted_match:
                    visibility_q |= (
                        restricted_q &
                        Q(document__academic_units__academic_unit__code__icontains=course.name)
                    )

                qs = qs.filter(visibility_q).distinct()
        else:
            # Anonymous users can only view public documents
            qs = qs.filter(document__visibility='public')

        # Domain metadata filters
        if filters:
            if filters.get('category'):
                cat = filters['category']
                qs = qs.filter(
                    Q(document__category__code=cat) |
                    Q(document__category__id=cat)
                )

            if filters.get('academic_unit'):
                unit = filters['academic_unit']
                qs = qs.filter(
                    Q(document__academic_units__academic_unit__code=unit) |
                    Q(document__academic_units__academic_unit__id=unit)
                )

            if filters.get('academic_units'):
                units = filters['academic_units']
                qs = qs.filter(
                    document__academic_units__academic_unit_id__in=units
                )

            if filters.get('document_id'):
                qs = qs.filter(document_id=filters['document_id'])

            if filters.get('file_type'):
                ft = str(filters['file_type']).lower().strip()
                qs = qs.filter(document__versions__files__extension=ft)

        return qs

    def retrieve(self, request: RetrievalRequest) -> List[RetrievalResult]:
        """
        Execute semantic retrieval for the given request.

        Args:
            request: RetrievalRequest containing query, user, limit, and filters.

        Returns:
            List of normalized RetrievalResult objects ranked by cosine similarity.
        """
        query = (request.query or "").strip()
        if not query:
            return []

        # 1. Generate query embedding vector
        try:
            query_vector = self.provider.embed_query(query)
        except EmbeddingProviderError as exc:
            logger.error("Failed to generate query embedding: %s", exc)
            raise

        expected_dim = self.provider.get_dimensions()
        if len(query_vector) != expected_dim:
            logger.error(
                "Query embedding dimension mismatch: got %d, expected %d",
                len(query_vector), expected_dim
            )
            return []

        # 2. Get authorized candidates
        candidate_qs = self.build_candidate_queryset(
            user=request.user,
            filters=request.filters
        )

        # 3. Annotate pgvector cosine distance and order by similarity
        ranked_qs = (
            candidate_qs
            .annotate(distance=CosineDistance('embedding', query_vector))
            .filter(distance__isnull=False)
            .select_related('document', 'document_version')
            .order_by('distance')
        )

        limit = max(1, int(request.limit or 10))
        chunks = list(ranked_qs[:limit])

        results = []
        for chunk in chunks:
            # CosineDistance returns 1.0 - cosine_similarity.
            # Similarity = 1.0 - distance, bounded to [0.0, 1.0]
            dist = float(chunk.distance) if chunk.distance is not None else 1.0
            similarity = max(0.0, min(1.0, 1.0 - dist))

            if request.min_score > 0.0 and similarity < request.min_score:
                continue

            results.append(self._format_chunk_result(chunk, similarity))

        return results

    def get_page_chunks(
        self,
        user: Any,
        document_share_id: Any,
        page_number: int,
        document_version_id: Optional[int] = None,
    ) -> List[RetrievalResult]:
        """
        Deterministic, authorized retrieval of chunks spanning a specific page.

        Enforces strict authorization invariants by anchoring to build_candidate_queryset(user).
        Handles multi-page spanning chunks where page_number <= P <= page_end.

        Args:
            user: Authenticated Django user instance.
            document_share_id: Public UUID or UUID string of the document.
            page_number: Positive 1-indexed page number (int).
            document_version_id: Optional specific DocumentVersion primary key.
                If omitted, defaults to the latest version (`document_version__is_latest=True`).

        Returns:
            List[RetrievalResult] ordered deterministically by chunk_index, or empty list
            if unauthorized, invalid input, or no matching content.
        """
        # 1. Validate user authentication
        if not user or not getattr(user, 'is_authenticated', False):
            return []

        # 2. Validate document_share_id
        if not document_share_id:
            return []
        if isinstance(document_share_id, uuid.UUID):
            share_uuid = document_share_id
        else:
            try:
                share_uuid = uuid.UUID(str(document_share_id).strip())
            except (ValueError, TypeError, AttributeError):
                return []

        # 3. Validate page_number (must be positive integer, not bool or float)
        if isinstance(page_number, bool) or isinstance(page_number, float):
            return []
        try:
            page_num = int(page_number)
            if page_num <= 0:
                return []
        except (ValueError, TypeError):
            return []

        # 4. Validate optional document_version_id
        version_id = None
        if document_version_id is not None:
            if isinstance(document_version_id, bool) or isinstance(document_version_id, float):
                return []
            try:
                version_id = int(document_version_id)
                if version_id <= 0:
                    return []
            except (ValueError, TypeError):
                return []

        # 5. Anchor to existing authorized candidate queryset
        candidate_qs = self.build_candidate_queryset(user=user)

        # 6. Scope strictly to the requested document share_id
        qs = candidate_qs.filter(document__share_id=share_uuid)

        # 7. Apply version filtering
        if version_id is not None:
            qs = qs.filter(document_version_id=version_id)
        else:
            qs = qs.filter(document_version__is_latest=True)

        # 8. Filter chunks spanning the requested page: page_number <= P <= page_end
        # Handles both explicit page_end and single-page chunks where page_end is NULL
        page_filter = (
            Q(page_number__lte=page_num, page_end__gte=page_num) |
            Q(page_number=page_num, page_end__isnull=True)
        )
        qs = qs.filter(page_filter)

        # 9. Deterministic ordering by chunk_index with relation prefetching
        chunks = list(
            qs.select_related('document', 'document_version')
            .prefetch_related('document_version__files')
            .order_by('chunk_index')
        )

        # 10. Format results using standard RetrievalResult
        results = []
        for chunk in chunks:
            res = self._format_chunk_result(chunk, similarity=1.0)
            res.metadata['retrieval_mode'] = 'explicit_page'
            res.metadata['match_type'] = 'exact_page'
            results.append(res)

        return results

    def _format_chunk_result(self, chunk: DocumentChunk, similarity: float) -> RetrievalResult:
        """Format DocumentChunk into a normalized RetrievalResult."""
        doc = chunk.document
        version = chunk.document_version

        # Generate deterministic citation string
        citation = self.generate_citation(chunk)

        # Canonical detail URL
        detail_url = f"/documents/document/{doc.share_id}/"

        # Resolve thumbnail, media file URL, and author
        thumbnail_url = getattr(doc, 'thumbnail_url', None) or ""
        first_file = None
        if version and hasattr(version, 'files'):
            first_file = version.files.first()
        elif hasattr(doc, 'latest_version') and doc.latest_version:
            first_file = doc.latest_version.files.first()

        media_url = ""
        file_type = ""
        if first_file:
            try:
                if getattr(first_file, 'file', None):
                    media_url = first_file.file.url
            except Exception:
                media_url = ""
            file_type = getattr(first_file, 'extension', '') or ""

        author_name = ""
        uploader = getattr(doc, 'uploaded_by', None)
        if uploader:
            full_name = f"{uploader.first_name or ''} {uploader.last_name or ''}".strip()
            author_name = full_name or getattr(uploader, "username", "") or ""

        metadata = {
            "document_id": doc.id,
            "document_share_id": str(doc.share_id),
            "document_version_id": version.id if version else None,
            "version_number": version.version_number if version else None,
            "chunk_id": chunk.id,
            "chunk_index": chunk.chunk_index,
            "chunk_type": chunk.chunk_type,
            "page_number": chunk.page_number,
            "page_end": chunk.page_end,
            "slide_number": chunk.slide_number,
            "section_heading": chunk.section_heading,
            "embedding_model": chunk.embedding_model,
            "thumbnail_url": thumbnail_url,
            "media_url": media_url,
            "file_type": file_type,
            "resource_type": "document",
            "author": author_name,
        }

        return RetrievalResult(
            source=SourceType.DOCUMENT,
            object_id=chunk.id,
            title=doc.title,
            snippet=chunk.content,
            score=round(similarity, 4),
            url=detail_url,
            citation=citation,
            metadata=metadata,
            raw_object=chunk,
        )

    @staticmethod
    def generate_citation(chunk: DocumentChunk) -> str:
        """
        Generate academic citation label from chunk location provenance.

        Format:
        [<Title>, v<N>, p. <page> - <Heading>]
        [<Title>, v<N>, Slide <slide>]
        [<Title>, v<N>, chunk <idx>]
        """
        parts = [chunk.document.title]
        version_str = f"v{chunk.document_version.version_number}"
        parts.append(version_str)

        loc_parts = []
        if chunk.chunk_type == 'slide' or (chunk.slide_number and not chunk.page_number):
            loc_parts.append(f"Slide {chunk.slide_number}")
        elif chunk.page_number:
            if chunk.page_end and chunk.page_end > chunk.page_number:
                loc_parts.append(f"pp. {chunk.page_number}–{chunk.page_end}")
            else:
                loc_parts.append(f"p. {chunk.page_number}")
        elif chunk.slide_number:
            loc_parts.append(f"Slide {chunk.slide_number}")
        else:
            loc_parts.append(f"Chunk {chunk.chunk_index + 1}")

        if chunk.section_heading:
            loc_parts.append(f'"{chunk.section_heading}"')

        citation_loc = ", ".join(loc_parts)
        return f"[{', '.join(parts)}: {citation_loc}]"
