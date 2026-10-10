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
                "enum": ["school", "department", "programme", "course", "unit", "my_units", "all"],
                "description": "The tier of academic hierarchy to query (default: all)",
                "default": "all",
            },
            "query": {
                "type": "string",
                "description": "Search term matching code or title",
            },
            "code": {
                "type": "string",
                "description": "Exact code match (e.g. 'SPAS', 'COMP', 'BSC-CS', 'CSC221')",
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

        # 0. Student's Active Enrolled Units (when entity_type is 'my_units' or 'unit' or 'all')
        if user and getattr(user, "is_authenticated", False) and entity_type in ("my_units", "unit", "all"):
            try:
                from documents.academic.services import StudentAcademicEnrollmentService
                enrollments = StudentAcademicEnrollmentService.get_active_enrollments(user)
                for enr in enrollments:
                    unit = enr.academic_unit
                    if code and unit.code.lower() != code.lower():
                        continue
                    if query and query.lower() not in unit.code.lower() and query.lower() not in unit.name.lower():
                        if entity_type != "my_units":
                            continue
                    results.append({
                        "entity_type": "enrolled_unit",
                        "id": unit.id,
                        "code": unit.code,
                        "name": unit.name,
                        "credit_hours": unit.credit_hours,
                        "enrollment_source": enr.source,
                        "academic_level": enr.academic_level.name if enr.academic_level else None,
                        "semester": str(enr.semester) if enr.semester else None,
                    })
                    if len(results) >= limit:
                        break
            except Exception:
                pass

        # 1. Schools
        if len(results) < limit and entity_type in ("school", "all"):
            qs = School.objects.filter(is_active=True)
            if code:
                qs = qs.filter(code__iexact=code)
            if query:
                qs = qs.filter(Q(name__icontains=query) | Q(code__icontains=query))
            for item in qs[: limit - len(results)]:
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

        # 4. Academic Units (from documents.academic.models)
        if len(results) < limit and entity_type in ("unit", "course", "all"):
            try:
                from documents.academic.models import AcademicUnit
                u_qs = AcademicUnit.objects.filter(is_active=True)
                if code:
                    u_qs = u_qs.filter(code__iexact=code)
                if query:
                    u_qs = u_qs.filter(Q(name__icontains=query) | Q(code__icontains=query))
                seen_codes = {r.get("code") for r in results if r.get("entity_type") == "enrolled_unit"}
                for u_item in u_qs[: limit - len(results)]:
                    if u_item.code in seen_codes:
                        continue
                    results.append({
                        "entity_type": "academic_unit",
                        "id": u_item.id,
                        "code": u_item.code,
                        "name": u_item.name,
                        "slug": u_item.slug,
                        "credit_hours": u_item.credit_hours,
                        "description": u_item.description or "",
                    })
                    if len(results) >= limit:
                        break
            except Exception:
                pass

        # 5. Courses (legacy courses.models)
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
