"""
Domain Tools Package for Pwanimate.

Exports the five standard read-only domain tools.
"""

from pwanimate.tools.domain.academic import AcademicLookupTool, StudentTimetableTool
from pwanimate.tools.domain.documents import DocumentDetailTool
from pwanimate.tools.domain.groups import GroupAnnouncementsTool
from pwanimate.tools.domain.users import UserProfileTool
from pwanimate.tools.domain.notifications import NotificationSummaryTool
from pwanimate.tools.domain.people import PeopleDiscoveryTool
from pwanimate.tools.domain.extra import LocalTimeTool, ContentSearchTool, SendNotificationTool
from pwanimate.tools.domain.web_search import WebSearchTool
from pwanimate.tools.domain.site_info import SiteInfoTool

__all__ = [
    "AcademicLookupTool",
    "StudentTimetableTool",
    "DocumentDetailTool",
    "GroupAnnouncementsTool",
    "UserProfileTool",
    "NotificationSummaryTool",
    "PeopleDiscoveryTool",
    "LocalTimeTool", "ContentSearchTool", "SendNotificationTool", "WebSearchTool",
    "SiteInfoTool",
]
