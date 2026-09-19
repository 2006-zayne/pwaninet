"""
People Discovery Service for Pwanimate.

Discovers and ranks real PwaniNet users based on skills, interests,
collaboration availability, and academic alignment. Strictly enforces
domain privacy boundaries (exclusions, blocks, hidden authors, profile
privacy levels) and reuses proven recommendation signals without N+1 queries.
"""

from typing import Any, Dict, List, Optional, Set
import logging
from django.db.models import Case, F, IntegerField, Q, Value, When
from django.urls import reverse

from users.models import User, CollaborationStatus, Follow
from users.services.privacy import apply_user_discovery_exclusions
from recommendations.services.user_recommender import (
    annotate_recommendation_scores,
    _determine_user_reason,
)
from pwanimate.people.types import PeopleQuery, PersonResult
from pwanimate.context.user_context import UserContext

logger = logging.getLogger(__name__)


class PeopleDiscoveryService:
    """
    Service responsible for querying, filtering, and scoring real PwaniNet
    users for peer discovery and collaboration requests.
    """

    def discover(
        self,
        query: PeopleQuery,
        viewer: Optional[Any] = None,
        viewer_context: Optional[UserContext] = None,
    ) -> List[PersonResult]:
        """
        Discover and rank users matching the provided PeopleQuery.

        Args:
            query: Structured search criteria (skills, interests, status, scope, limit).
            viewer: Authenticated or anonymous User instance requesting discovery.
            viewer_context: Optional structured UserContext of the viewer.

        Returns:
            List of PersonResult objects representing real PwaniNet users.
        """
        # Resolve following IDs and group IDs (from viewer_context if available)
        following_ids = None
        my_group_ids = None
        if viewer_context:
            following_ids = viewer_context.following_user_ids
            my_group_ids = viewer_context.approved_group_ids
        elif viewer and getattr(viewer, "is_authenticated", False):
            following_ids = list(Follow.objects.filter(follower_id=viewer.id).values_list('followed_id', flat=True))

        # 1. Base queryset with domain privacy boundary applied
        qs = apply_user_discovery_exclusions(User.objects.all(), viewer=viewer, following_ids=following_ids)

        # 2. Build skill filters
        skill_queries = Q()
        valid_skills: List[str] = []
        for s in query.target_skills:
            clean = s.strip()
            if clean:
                valid_skills.append(clean)
                skill_queries |= Q(skills__icontains=clean)

        # 3. Build interest filters
        interest_queries = Q()
        valid_interests: List[str] = []
        for i in query.target_interests:
            clean = i.strip()
            if clean:
                valid_interests.append(clean)
                interest_queries |= Q(interests__icontains=clean)

        # Apply skill and interest constraints
        if valid_skills and valid_interests:
            qs = qs.filter(skill_queries | interest_queries)
        elif valid_skills:
            qs = qs.filter(skill_queries)
        elif valid_interests:
            qs = qs.filter(interest_queries)

        # 4. Filter by collaboration status
        if query.required_collaboration_status:
            status = query.required_collaboration_status.strip().lower()
            if status in (
                CollaborationStatus.OPEN_TO_PROJECTS,
                CollaborationStatus.OPEN_TO_STUDY_GROUPS,
                CollaborationStatus.OPEN_TO_NETWORKING,
                CollaborationStatus.NOT_LOOKING,
            ):
                qs = qs.filter(collaboration_status=status)
            elif status in ("any_open", "open", "collaborate", "collaboration"):
                qs = qs.filter(
                    collaboration_status__in=[
                        CollaborationStatus.OPEN_TO_PROJECTS,
                        CollaborationStatus.OPEN_TO_STUDY_GROUPS,
                        CollaborationStatus.OPEN_TO_NETWORKING,
                    ]
                )

        # 5. Filter by academic scope
        if query.academic_scope:
            scope = query.academic_scope.strip().lower()
            if scope in ("programme", "program", "my_programme", "my_program"):
                prog_id = None
                if viewer_context and viewer_context.programme_id:
                    prog_id = viewer_context.programme_id
                elif viewer and getattr(viewer, "programme_id", None):
                    prog_id = viewer.programme_id
                if prog_id:
                    qs = qs.filter(programme_id=prog_id)
            elif scope in ("department", "dept", "my_department", "my_dept"):
                dept_id = None
                if viewer_context and viewer_context.department_id:
                    dept_id = viewer_context.department_id
                elif (
                    viewer
                    and getattr(viewer, "programme", None)
                    and getattr(viewer.programme, "department_id", None)
                ):
                    dept_id = viewer.programme.department_id
                if dept_id:
                    qs = qs.filter(programme__department_id=dept_id)
            elif scope in ("school", "my_school"):
                school_id = None
                if viewer_context and viewer_context.school_id:
                    school_id = viewer_context.school_id
                elif (
                    viewer
                    and getattr(viewer, "programme", None)
                    and getattr(viewer.programme, "department", None)
                    and getattr(viewer.programme.department, "school_id", None)
                ):
                    school_id = viewer.programme.department.school_id
                if school_id:
                    qs = qs.filter(programme__department__school_id=school_id)
            else:
                # Specific academic identifier (code or name)
                raw_scope = query.academic_scope.strip()
                qs = qs.filter(
                    Q(programme__code__iexact=raw_scope)
                    | Q(programme__name__icontains=raw_scope)
                    | Q(course__name__icontains=raw_scope)
                    | Q(course__code__iexact=raw_scope)
                )

        # 6. Recommendation scoring reuse (academic, groups, mutuals, avatar)
        qs = annotate_recommendation_scores(
            qs,
            user=viewer,
            already_following=set(following_ids) if following_ids is not None else None,
            my_group_ids=my_group_ids,
        )

        # 7. Match quality scoring
        match_clauses = []
        for s in valid_skills:
            match_clauses.append(When(skills__icontains=s, then=Value(50)))
        for i in valid_interests:
            match_clauses.append(When(interests__icontains=i, then=Value(30)))

        if match_clauses:
            match_score_expr = Case(
                *match_clauses,
                default=Value(0),
                output_field=IntegerField(),
            )
            qs = qs.annotate(match_score=match_score_expr)
            order_by_fields = ["-match_score", "-recommendation_score", "-date_joined"]
        else:
            order_by_fields = ["-recommendation_score", "-date_joined"]

        # 8. Single-query execution with joined relations
        qs = qs.select_related(
            "programme",
            "programme__department",
            "programme__department__school",
            "academic_level",
            "course",
            "year",
        ).order_by(*order_by_fields)

        limit = max(1, min(query.limit or 10, 50))
        candidates = list(qs[:limit])

        # 9. Format candidates into structured PersonResult objects
        results: List[PersonResult] = []
        for user in candidates:
            results.append(self._build_person_result(user, query, viewer))

        return results

    def _build_person_result(
        self,
        candidate: User,
        query: PeopleQuery,
        viewer: Optional[Any] = None,
    ) -> PersonResult:
        """
        Construct a PersonResult from an annotated candidate User model.
        Factual evidence is extracted strictly from database attributes.
        """
        display_name = (
            f"{candidate.first_name or ''} {candidate.last_name or ''}".strip()
            or candidate.username
        )

        avatar_url = ""
        if candidate.profile_pic:
            try:
                avatar_url = candidate.profile_pic.url
            except Exception:
                avatar_url = str(candidate.profile_pic)

        try:
            profile_url = reverse("users:profile", kwargs={"username": candidate.username})
        except Exception:
            profile_url = f"/users/user/{candidate.username}/"

        programme_name = (
            candidate.programme.name
            if candidate.programme
            else (candidate.course.name if candidate.course else None)
        )
        academic_level = (
            candidate.academic_level.name
            if candidate.academic_level
            else (f"Year {candidate.year.level}" if candidate.year else None)
        )

        # Determine matched skills
        user_skills = candidate.skills if isinstance(candidate.skills, list) else []
        matched_skills: List[str] = []
        target_skills_lower = [s.lower() for s in query.target_skills if s.strip()]
        for s in user_skills:
            s_str = str(s).strip()
            if any(t in s_str.lower() for t in target_skills_lower):
                matched_skills.append(s_str)

        # Determine matched interests
        raw_interests = [
            i.strip() for i in (candidate.interests or "").split(",") if i.strip()
        ]
        matched_interests: List[str] = []
        target_interests_lower = [i.lower() for i in query.target_interests if i.strip()]
        for i in raw_interests:
            if any(t in i.lower() for t in target_interests_lower):
                matched_interests.append(i)

        # Academic alignment reason
        academic_alignment = (
            _determine_user_reason(viewer, candidate)
            if viewer and getattr(viewer, "is_authenticated", False)
            else "Campus Peer"
        )

        evidence: Dict[str, Any] = {
            "matched_skills": matched_skills,
            "matched_interests": matched_interests,
            "collaboration_status": candidate.collaboration_status or "None specified",
            "academic_alignment": academic_alignment,
            "shared_groups_count": getattr(candidate, "shared_groups_count", 0),
            "mutual_connections_count": getattr(candidate, "fof_count", 0),
            "academic_score": getattr(candidate, "academic_score", 0),
        }

        return PersonResult(
            user_id=candidate.id,
            username=candidate.username,
            display_name=display_name,
            headline=candidate.headline or "",
            avatar_url=avatar_url,
            profile_url=profile_url,
            programme_name=programme_name,
            academic_level=academic_level,
            collaboration_status=candidate.collaboration_status or "",
            matched_skills=matched_skills,
            matched_interests=matched_interests,
            evidence=evidence,
            recommendation_score=int(getattr(candidate, "recommendation_score", 0)),
        )
