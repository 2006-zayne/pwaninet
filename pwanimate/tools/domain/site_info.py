"""
Site Info Domain Tool for Pwanimate.

Allows Pwanimate to answer questions about vasto and itself
by loading curated site content from markdown files.
"""

from pwanimate.tools.base import BaseDomainTool, ToolResult
from pwanimate.tools.exceptions import ToolValidationError
from pwanimate.services.site_content import SiteContentService


class SiteInfoTool(BaseDomainTool):
    name = "site_info"
    description = "Get information about vasto or Pwanimate features and capabilities."
    parameters_schema = {
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "The topic to get information about (e.g., 'about', 'pwanimate', 'features', 'privacy')",
            },
        },
        "required": ["topic"],
    }

    def execute(self, user, topic, **kwargs):
        topic = str(topic).strip().lower()
        if not topic:
            raise ToolValidationError("Topic is required.", tool_name=self.name)

        content = SiteContentService.get_content(topic)
        if content:
            return ToolResult.ok({
                "topic": topic,
                "content": content,
                "source": "site_content",
            })

        available = SiteContentService.get_available_topics()
        return ToolResult.ok({
            "topic": topic,
            "content": None,
            "available_topics": available,
            "source": "site_content",
        })
