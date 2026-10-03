"""Provider-independent public web search tool."""

import re

from pwanimate.tools.base import BaseDomainTool, ToolResult
from pwanimate.tools.exceptions import ToolValidationError
from pwanimate.web_search import WebSearchError, WebSearchRouter, WebSearchUnavailable


class WebSearchTool(BaseDomainTool):
    name = "web_search"
    description = (
        "Search public websites whenever a public answer needs current, recent, or independently "
        "verified facts, even when the student did not explicitly request a search. Use for public web facts only; "
        "use PwaniNet tools for campus posts, documents, people, groups, or private account data. "
        "Returns source titles, URLs, snippets, dates, and relevance scores."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "minLength": 1, "maxLength": 600},
            "recency": {"type": ["string", "null"], "enum": ["day", "week", "month", "year", None]},
            "domains": {
                "type": ["array", "null"],
                "items": {"type": "string", "maxLength": 253},
                "maxItems": 10,
            },
        },
        "required": ["query"],
        "additionalProperties": False,
    }

    def execute(self, user, query, recency=None, domains=None, **kwargs):
        if not isinstance(query, str):
            raise ToolValidationError("Enter a text search query.", tool_name=self.name)
        query = " ".join(query.split())
        if not query or len(query) > 600:
            raise ToolValidationError("Enter a search query of 1 to 600 characters.", tool_name=self.name)
        if recency not in (None, "", "day", "week", "month", "year"):
            raise ToolValidationError("Recency must be day, week, month, or year.", tool_name=self.name)
        if domains is not None:
            if not isinstance(domains, list) or len(domains) > 10:
                raise ToolValidationError("Provide at most 10 search domains.", tool_name=self.name)
            for domain in domains:
                if not isinstance(domain, str) or not re.fullmatch(
                    r"(?=.{1,253}$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+"
                    r"[a-zA-Z]{2,63}",
                    domain.strip().rstrip("."),
                ):
                    raise ToolValidationError(
                        "Search domains must be host names without paths or URLs.",
                        tool_name=self.name,
                    )

        try:
            response = WebSearchRouter().search(
                query,
                recency=recency or None,
                domains=domains,
            )
        except WebSearchUnavailable:
            return ToolResult.fail(
                "Web search is not configured or is disabled. Do not claim to have searched the web.",
                error_type="web_search_unavailable",
            )
        except WebSearchError:
            return ToolResult.fail(
                "Web search is temporarily unavailable. Do not claim to have searched the web.",
                error_type="web_search_failed",
            )

        return ToolResult.ok(
            [result.to_dict() for result in response.results],
            provider=response.provider,
            result_count=len(response.results),
        )
