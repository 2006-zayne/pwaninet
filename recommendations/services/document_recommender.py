"""
Document Recommendation Service.
Personalized "For You" document ranking based on student curriculum & semester units.
"""

import logging
from django.core.cache import cache
from django.db.models import Case, F, IntegerField, Q, Value, When
from django.db.models.functions import Coalesce
from documents.models import Document
from documents.academic.models import ProgrammeUnit

logger = logging.getLogger(__name__)


def get_for_you_documents(user, limit=8, use_cache=True):
    """
    Get personalized "For You" academic documents for a student.

    Ranking Tiers:
    - Tier 1: Documents mapped to student's current ProgrammeUnit for this exact level & semester (+100pts)
    - Tier 2: Documents mapped to student's academic level / year (+40pts)
    - Tier 3: Documents matching student's current semester (+25pts)
    - Tier 4: Documents in student's department (+20pts)
    - Engagement Factor: +1.5pts per download, +0.2pts per view

    Args:
        user: The User instance (student).
        limit: Max documents to return (default 8).
        use_cache: Whether to use caching (default True).

    Returns:
        List of Document instances annotated with matching unit badges.
    """
    if not user or not user.is_authenticated:
        # Return popular documents for guest users
        from documents.selectors.document_selectors import DocumentSelector
        return DocumentSelector.get_popular_documents(limit=limit)

    limit = max(1, min(limit, 30))
    cache_key = f'recommendations:docs:foryou:{user.id}:limit:{limit}'

    if use_cache:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    # 1. Identify student's active units for this exact academic level & semester
    user_unit_ids = []
    user_unit_map = {}  # id -> code
    programme_unit_ids = []
    department_unit_ids = []

    if getattr(user, 'programme_id', None):
        pu_qs = ProgrammeUnit.objects.filter(programme_id=user.programme_id)
        if getattr(user, 'academic_level_id', None):
            pu_qs = pu_qs.filter(academic_level_id=user.academic_level_id)
        if getattr(user, 'semester_id', None):
            pu_qs = pu_qs.filter(semester_id=user.semester_id)

        for pu in pu_qs.select_related('academic_unit'):
            user_unit_ids.append(pu.academic_unit_id)
            user_unit_map[pu.academic_unit_id] = pu.academic_unit.code

        # All units under this programme
        programme_unit_ids = list(
            ProgrammeUnit.objects.filter(programme_id=user.programme_id)
            .values_list('academic_unit_id', flat=True)
            .distinct()
        )

        # Related units in the same department
        if getattr(user.programme, 'department_id', None):
            department_unit_ids = list(
                ProgrammeUnit.objects.filter(programme__department_id=user.programme.department_id)
                .exclude(academic_unit_id__in=programme_unit_ids)
                .values_list('academic_unit_id', flat=True)
                .distinct()
            )

    # 2. Base public documents queryset
    candidates = Document.objects.filter(
        status='ready',
        is_available=True,
        visibility='public'
    )

    # 3. Academic Relevance Scoring
    academic_clauses = []

    if user_unit_ids:
        academic_clauses.append(
            When(academic_units__academic_unit_id__in=user_unit_ids, then=Value(100))
        )

    if programme_unit_ids:
        academic_clauses.append(
            When(academic_units__academic_unit_id__in=programme_unit_ids, then=Value(50))
        )

    if getattr(user, 'academic_level_id', None):
        academic_clauses.append(
            When(academic_units__academic_level_id=user.academic_level_id, then=Value(30))
        )

    if getattr(user, 'semester_id', None):
        academic_clauses.append(
            When(academic_units__semester_id=user.semester_id, then=Value(15))
        )

    if department_unit_ids:
        academic_clauses.append(
            When(academic_units__academic_unit_id__in=department_unit_ids, then=Value(10))
        )

    if academic_clauses:
        academic_score_expr = Case(
            *academic_clauses,
            default=Value(0),
            output_field=IntegerField()
        )
    else:
        academic_score_expr = Value(0, output_field=IntegerField())

    # 4. Engagement Scores
    download_score = Coalesce(F('analytics__download_count'), 0) * 1.5
    view_score = Coalesce(F('analytics__view_count'), 0) * 0.2

    annotated_qs = candidates.annotate(
        academic_score=academic_score_expr,
    ).annotate(
        recommendation_score=F('academic_score') + download_score + view_score
    ).select_related(
        'category',
        'uploaded_by',
        'analytics'
    ).prefetch_related(
        'academic_units__academic_unit',
        'academic_units__academic_level',
        'academic_units__semester'
    ).distinct().order_by('-recommendation_score', '-created_at')

    results = list(annotated_qs[:limit])

    # 5. Attach matching badge labels
    for doc in results:
        doc.matching_badge = _determine_doc_badge(user, doc, user_unit_map)

    if use_cache:
        cache.set(cache_key, results, timeout=600)

    return results


def _determine_doc_badge(user, doc, user_unit_map):
    """Generate display badge for recommended document."""
    # Check if any unit in doc matches user's current semester units
    for dau in doc.academic_units.all():
        if dau.academic_unit_id in user_unit_map:
            unit_code = user_unit_map[dau.academic_unit_id]
            return f"Matches {unit_code}"

    if user.academic_level_id:
        for dau in doc.academic_units.all():
            if dau.academic_level_id == user.academic_level_id:
                return f"For {user.academic_level.name}"

    if user.programme_id:
        return f"{user.programme.code} Resource"

    return "Recommended for You"


def invalidate_document_recommendations_cache(user_id):
    """Invalidate cached document recommendations for a user."""
    for limit in (5, 8, 10, 20):
        cache.delete(f'recommendations:docs:foryou:{user_id}:limit:{limit}')
