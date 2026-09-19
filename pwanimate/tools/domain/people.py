"""
People Discovery Tool for Pwanimate.

Allows deterministic, read-only retrieval and recommendation of real
PwaniNet users based on skills, interests, collaboration readiness,
and academic alignment.
"""

from typing import Any, Dict, List, Optional, Union
import logging

from pwanimate.tools.base import BaseDomainTool, ToolResult
from pwanimate.people.types import PeopleQuery
from pwanimate.people.service import PeopleDiscoveryService

logger = logging.getLogger(__name__)


class PeopleDiscoveryTool(BaseDomainTool):
    """
    Search and discover real PwaniNet students and peers based on skills,
    interests, academic scope, and collaboration readiness.
    """
    name = "people_discovery"
    description = (
        "Discover real PwaniNet students and peers based on technical/creative skills, "
        "interests, collaboration status (open to projects/study groups), and academic programme."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Original natural language user query",
            },
            "skills": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of technical or domain skills to filter by (e.g. ['Python', 'Django'])",
            },
            "interests": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of academic or hobby interests to filter by (e.g. ['AI', 'Robotics'])",
            },
            "collaboration_status": {
                "type": "string",
                "description": "Collaboration availability ('open_to_projects', 'open_to_study_groups', 'open_to_networking', 'any_open')",
            },
            "academic_scope": {
                "type": "string",
                "description": "Academic scope filter ('programme', 'department', 'school', or specific programme/course code/name)",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of people to return (default 10)",
            },
        },
        "required": [],
    }

    def execute(
        self,
        user: Any,
        user_context: Optional[Any] = None,
        query: str = "",
        skills: Optional[Union[List[str], str]] = None,
        interests: Optional[Union[List[str], str]] = None,
        collaboration_status: Optional[str] = None,
        academic_scope: Optional[str] = None,
        limit: int = 10,
        **kwargs,
    ) -> ToolResult:
        # Normalize skills list
        target_skills: List[str] = []
        if isinstance(skills, list):
            target_skills = [str(s).strip() for s in skills if str(s).strip()]
        elif isinstance(skills, str) and skills.strip():
            target_skills = [s.strip() for s in skills.split(",") if s.strip()]

        # Normalize interests list
        target_interests: List[str] = []
        if isinstance(interests, list):
            target_interests = [str(i).strip() for i in interests if str(i).strip()]
        elif isinstance(interests, str) and interests.strip():
            target_interests = [i.strip() for i in interests.split(",") if i.strip()]

        people_query = PeopleQuery(
            raw_query=query or "",
            target_skills=target_skills,
            target_interests=target_interests,
            required_collaboration_status=collaboration_status,
            academic_scope=academic_scope,
            limit=limit or 10,
        )

        service = PeopleDiscoveryService()
        person_results = service.discover(
            query=people_query,
            viewer=user,
            viewer_context=user_context,
        )

        data = [p.to_dict() for p in person_results]

        return ToolResult.ok(
            data,
            count=len(data),
            skills_queried=target_skills,
            interests_queried=target_interests,
            scope=academic_scope,
        )
