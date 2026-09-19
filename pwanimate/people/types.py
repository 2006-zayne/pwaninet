"""
Types and Data Structures for Pwanimate People Discovery.

Defines structured query requests and grounded candidate representations
for discovering real PwaniNet users based on skills, interests, academic
alignment, and collaboration readiness.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PeopleQuery:
    """
    Structured query representation for discovering PwaniNet users.

    Attributes:
        raw_query: Original user input string.
        target_skills: List of skill names/keywords to search for (e.g. ['Python', 'Django']).
        target_interests: List of interest keywords to search for (e.g. ['AI', 'Robotics']).
        required_collaboration_status: Optional required status (e.g. 'open_to_projects').
        academic_scope: Optional academic filter ('programme', 'department', 'school', or specific code/name).
        limit: Maximum number of results to return (default 10).
    """
    raw_query: str = ""
    target_skills: List[str] = field(default_factory=list)
    target_interests: List[str] = field(default_factory=list)
    required_collaboration_status: Optional[str] = None
    academic_scope: Optional[str] = None
    limit: int = 10


@dataclass
class PersonResult:
    """
    Structured, factual representation of a discoverable PwaniNet user.

    Strictly excludes sensitive authentication and contact attributes
    (email, phone, password, tokens, session IDs).
    """
    user_id: int
    username: str
    display_name: str
    headline: str = ""
    avatar_url: str = ""
    profile_url: str = ""
    programme_name: Optional[str] = None
    academic_level: Optional[str] = None
    collaboration_status: str = ""
    matched_skills: List[str] = field(default_factory=list)
    matched_interests: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)
    recommendation_score: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert person result to a JSON-serializable dictionary."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "display_name": self.display_name,
            "headline": self.headline,
            "avatar_url": self.avatar_url,
            "profile_url": self.profile_url,
            "programme_name": self.programme_name,
            "academic_level": self.academic_level,
            "collaboration_status": self.collaboration_status,
            "matched_skills": self.matched_skills,
            "matched_interests": self.matched_interests,
            "evidence": self.evidence,
            "recommendation_score": self.recommendation_score,
        }
