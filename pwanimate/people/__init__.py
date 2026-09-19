"""
Pwanimate People Discovery & Peer Recommendation Module.

Exports structured data types and discovery services for finding,
ranking, and recommending real PwaniNet users.
"""

from pwanimate.people.types import PeopleQuery, PersonResult
from pwanimate.people.service import PeopleDiscoveryService

__all__ = [
    "PeopleQuery",
    "PersonResult",
    "PeopleDiscoveryService",
]
