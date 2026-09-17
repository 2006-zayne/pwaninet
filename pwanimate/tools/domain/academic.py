"""
Academic Lookup Tool for Pwanimate.

Allows deterministic, read-only querying of Pwani University academic hierarchy:
Schools, Departments, Programmes, and Courses.
"""

from typing import Any, Dict, List, Optional
from django.db.models import Q

from pwanimate.tools.base import BaseDomainTool, ToolResult
from pwanimate.tools.exceptions import ToolValidationError
from courses.models import School, Department, Programme, Course


class AcademicLookupTool(BaseDomainTool):
    """
    Look up schools, departments, programmes, or courses within Pwani University.
    """
    name = "academic_lookup"
    description = (
        "Look up Pwani University academic structural metadata including "
        "Schools, Departments, Programmes, and Courses."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "entity_type": {
                "type": "string",
                "enum": ["school", "department", "programme", "course", "all"],
                "description": "The tier of academic hierarchy to query (default: all)",
                "default": "all",
            },
            "query": {
                "type": "string",
                "description": "Search term matching code or title",
            },
            "code": {
                "type": "string",
                "description": "Exact code match (e.g. 'SPAS', 'COMP', 'BSC-CS')",
            },
            "parent_id": {
                "type": "integer",
                "description": "Optional parent ID filter (e.g. school_id for departments, department_id for programmes)",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results to return (max 20)",
                "default": 10,
            },
        },
        "required": [],
    }

    def execute(
        self,
        user: Any,
        entity_type: str = "all",
        query: Optional[str] = None,
        code: Optional[str] = None,
        parent_id: Optional[int] = None,
        limit: int = 10,
        **kwargs,
    ) -> ToolResult:
        limit = min(max(1, int(limit)), 20)
        entity_type = (entity_type or "all").lower().strip()

        results: List[Dict[str, Any]] = []

        # 1. Schools
        if entity_type in ("school", "all"):
            qs = School.objects.filter(is_active=True)
            if code:
                qs = qs.filter(code__iexact=code)
            if query:
                qs = qs.filter(Q(name__icontains=query) | Q(code__icontains=query))
            for item in qs[:limit]:
                results.append({
                    "entity_type": "school",
                    "id": item.id,
                    "code": item.code,
                    "name": item.name,
                    "slug": item.slug,
                    "description": item.description or "",
                })
                if len(results) >= limit:
                    break

        # 2. Departments
        if len(results) < limit and entity_type in ("department", "all"):
            qs = Department.objects.filter(is_active=True).select_related("school")
            if code:
                qs = qs.filter(code__iexact=code)
            if parent_id:
                qs = qs.filter(school_id=parent_id)
            if query:
                qs = qs.filter(Q(name__icontains=query) | Q(code__icontains=query))
            for item in qs[: limit - len(results)]:
                results.append({
                    "entity_type": "department",
                    "id": item.id,
                    "code": item.code,
                    "name": item.name,
                    "slug": item.slug,
                    "school_code": item.school.code if item.school else None,
                    "school_name": item.school.name if item.school else None,
                    "description": item.description or "",
                })
                if len(results) >= limit:
                    break

        # 3. Programmes
        if len(results) < limit and entity_type in ("programme", "all"):
            qs = Programme.objects.filter(is_active=True).select_related("school", "department")
            if code:
                qs = qs.filter(code__iexact=code)
            if parent_id:
                qs = qs.filter(Q(department_id=parent_id) | Q(school_id=parent_id))
            if query:
                qs = qs.filter(Q(name__icontains=query) | Q(code__icontains=query))
            for item in qs[: limit - len(results)]:
                results.append({
                    "entity_type": "programme",
                    "id": item.id,
                    "code": item.code,
                    "name": item.name,
                    "slug": item.slug,
                    "academic_level": item.academic_level,
                    "duration_years": item.duration_years,
                    "school_code": item.school.code if item.school else None,
                    "department_name": item.department.name if item.department else None,
                    "description": item.description or "",
                })
                if len(results) >= limit:
                    break

        # 4. Courses
        if len(results) < limit and entity_type in ("course", "all"):
            qs = Course.objects.filter(is_active=True).select_related("programme", "department", "school")
            if code:
                qs = qs.filter(code__iexact=code)
            if parent_id:
                qs = qs.filter(Q(programme_id=parent_id) | Q(department_id=parent_id) | Q(school_id=parent_id))
            if query:
                qs = qs.filter(Q(name__icontains=query) | Q(code__icontains=query))
            for item in qs[: limit - len(results)]:
                results.append({
                    "entity_type": "course",
                    "id": item.id,
                    "code": item.code or "",
                    "name": item.name,
                    "slug": item.slug or "",
                    "degree_type": item.degree_type or "",
                    "programme_code": item.programme.code if item.programme else None,
                    "school_code": item.school.code if item.school else None,
                    "department_name": item.department.name if item.department else None,
                    "description": item.description or "",
                })
                if len(results) >= limit:
                    break

        return ToolResult.ok(
            results,
            count=len(results),
            query=query,
            entity_type=entity_type,
        )
