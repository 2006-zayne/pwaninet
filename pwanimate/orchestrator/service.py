"""
Pwanimate Orchestrator Service.

Central coordinator bridging user interactions, upstream retrieval, deterministic
domain tool routing, in-memory context bounding, application prompt policy,
and the AI Gateway.
"""

import logging
import re
import time
from typing import Dict, List, Optional

from pwanimate.ai.gateway import AIGateway, ChatMessage, LLMRequest, LLMResponse
from pwanimate.context import ContextEngine, ContextPackage, ContextRequest
from pwanimate.orchestrator.prompts import (
    SYSTEM_INSTRUCTION_CONVERSATIONAL,
    SYSTEM_INSTRUCTION_TUTOR,
)
from pwanimate.orchestrator.types import OrchestrationRequest, OrchestrationResponse
from pwanimate.retrieval import (
    RetrievalMode,
    RetrievalRequest,
    RetrievalResponse,
    SourceType,
    UnifiedRetrievalService,
)
from pwanimate.tools import (
    ToolRoute,
    ToolRouter,
    ToolRegistry,
    get_default_tool_registry,
    tool_result_to_context_items,
    build_tool_context_package,
)

logger = logging.getLogger(__name__)

# Patterns that indicate purely conversational pleasantries without substantive search intent
CONVERSATIONAL_PATTERNS = [
    r"^(hi|hello|hey|hiya|howdy)(\s+(there|pwanimate|friend))?[\s\.\!\?]*$",
    r"^(good\s+(morning|afternoon|evening|day))(\s+(pwanimate|there))?[\s\.\!\?]*$",
    r"^(habari|sasa|mambo|niaje|jambo)[\s\.\!\?]*$",
    r"^(thanks|thank\s+you|asante(\s+sana)?)[\s\.\!\?]*$",
    r"^(who\s+are\s+you|what\s+are\s+you|what\s+is\s+pwanimate)[\s\.\!\?]*$",
    r"^(what\s+can\s+you\s+do|how\s+can\s+you\s+help(\s+me)?)[\s\.\!\?]*$",
    r"^(help|start)[\s\.\!\?]*$",
]


class PwanimateOrchestrator:
    """
    Main orchestration engine for Pwanimate assistant interactions.
    """

    def __init__(
        self,
        retrieval_service: Optional[UnifiedRetrievalService] = None,
        context_engine: Optional[ContextEngine] = None,
        gateway: Optional[AIGateway] = None,
        tool_router: Optional[ToolRouter] = None,
        tool_registry: Optional[ToolRegistry] = None,
    ):
        self.retrieval_service = retrieval_service or UnifiedRetrievalService()
        self.context_engine = context_engine or ContextEngine()
        self.gateway = gateway or AIGateway()
        self.tool_router = tool_router or ToolRouter()
        self.tool_registry = tool_registry or get_default_tool_registry()

    def is_conversational_intent(self, query: str) -> bool:
        """
        Check if query is purely conversational chitchat that does not
        require knowledge base retrieval or domain tools.
        """
        cleaned = query.strip().lower()
        if len(cleaned) > 60:
            # Substantive queries are longer
            return False

        for pattern in CONVERSATIONAL_PATTERNS:
            if re.match(pattern, cleaned, re.IGNORECASE):
                return True
        return False

    def run(self, request: OrchestrationRequest) -> OrchestrationResponse:
        """
        Execute an end-to-end orchestration turn.

        1. Inspects query intent for conversational pleasantries.
        2. Evaluates high-confidence deterministic domain tool routes.
           If matched: executes authorized tool and grounds response via ContextPackage.
        3. If broad academic/knowledge query:
           a. Performs authorized multi-source retrieval (respecting request.user).
           b. Binds and formats retrieved context into ContextPackage.
           c. Formulates LLMRequest with academic tutor system prompt.
           d. Generates normalized response via Gateway.
        4. Packages citations, sources, timing, and response.
        """
        t_start = time.perf_counter()
        query = request.query.strip()

        # 1. Check conversational intent
        is_conversational = request.task == "general" or self.is_conversational_intent(query)
        if is_conversational:
            return self._run_conversational(request, query, t_start)

        # 2. Check deterministic tool routing
        tool_route = self.tool_router.route(query, user=request.user)
        if tool_route:
            return self._run_tool(request, query, tool_route, t_start)

        # 3. Fallback to standard multi-source retrieval
        return self._run_rag(request, query, t_start)

    def _run_conversational(
        self,
        request: OrchestrationRequest,
        query: str,
        t_start: float,
    ) -> OrchestrationResponse:
        """Handle pure conversational dialogue turns without retrieval or tools."""
        messages = list(request.history) + [ChatMessage(role="user", content=query)]

        llm_request = LLMRequest(
            task="general",
            messages=messages,
            system_instruction=SYSTEM_INSTRUCTION_CONVERSATIONAL,
            provider=request.provider,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        t_gen = time.perf_counter()
        llm_response = self.gateway.generate(llm_request)
        gen_time_ms = round((time.perf_counter() - t_gen) * 1000.0, 2)
        total_time_ms = round((time.perf_counter() - t_start) * 1000.0, 2)

        quota_info = llm_response.metadata.get("quota_info")

        return OrchestrationResponse(
            answer=llm_response.content,
            citations=[],
            sources=[],
            provider=llm_response.provider,
            model=llm_response.model,
            prompt_tokens=llm_response.prompt_tokens,
            completion_tokens=llm_response.completion_tokens,
            total_tokens=llm_response.total_tokens,
            retrieval_time_ms=0.0,
            generation_time_ms=gen_time_ms,
            total_time_ms=total_time_ms,
            metadata={"intent": "conversational"},
            quota_info=quota_info,
        )

    def _run_tool(
        self,
        request: OrchestrationRequest,
        query: str,
        tool_route: ToolRoute,
        t_start: float,
    ) -> OrchestrationResponse:
        """Handle high-confidence deterministic domain tool execution."""
        t_tool = time.perf_counter()
        tool_result = self.tool_registry.execute(
            tool_route.tool_name,
            user=request.user,
            **tool_route.parameters,
        )
        tool_time_ms = round((time.perf_counter() - t_tool) * 1000.0, 2)

        # Convert tool result to grounded ContextPackage
        context_items = tool_result_to_context_items(tool_route.tool_name, tool_result)
        context_pkg = build_tool_context_package(query, context_items)

        sources_summary = [
            {
                "source": item.source.value if hasattr(item.source, "value") else str(item.source),
                "id": item.object_id,
                "title": item.title,
                "citation": item.citation,
                "url": item.url,
            }
            for item in context_pkg.items
        ]

        messages = list(request.history) + [ChatMessage(role="user", content=query)]

        llm_request = LLMRequest(
            task="tool",
            messages=messages,
            context=context_pkg,
            system_instruction=SYSTEM_INSTRUCTION_TUTOR,
            provider=request.provider,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        t_gen = time.perf_counter()
        llm_response = self.gateway.generate(llm_request)
        gen_time_ms = round((time.perf_counter() - t_gen) * 1000.0, 2)
        total_time_ms = round((time.perf_counter() - t_start) * 1000.0, 2)

        citations = llm_response.citations or list(context_pkg.citations)
        quota_info = llm_response.metadata.get("quota_info")

        return OrchestrationResponse(
            answer=llm_response.content,
            citations=citations,
            sources=sources_summary,
            provider=llm_response.provider,
            model=llm_response.model,
            prompt_tokens=llm_response.prompt_tokens,
            completion_tokens=llm_response.completion_tokens,
            total_tokens=llm_response.total_tokens,
            retrieval_time_ms=tool_time_ms,
            generation_time_ms=gen_time_ms,
            total_time_ms=total_time_ms,
            metadata={
                "intent": "tool",
                "tool_name": tool_route.tool_name,
                "tool_success": tool_result.success,
                "matched_intent": tool_route.matched_intent,
                "context_items_count": context_pkg.total_items,
            },
            quota_info=quota_info,
        )

    def _run_rag(
        self,
        request: OrchestrationRequest,
        query: str,
        t_start: float,
    ) -> OrchestrationResponse:
        """Handle knowledge/retrieval-augmented dialogue turns."""
        # 1. Upstream Authorized Retrieval
        t_ret = time.perf_counter()
        sources = request.sources or [SourceType.DOCUMENT, SourceType.POST]
        retrieval_req = RetrievalRequest(
            query=query,
            user=request.user,
            sources=sources,
            mode=RetrievalMode.HYBRID,
        )

        retrieval_resp: RetrievalResponse = self.retrieval_service.retrieve(retrieval_req)
        ret_time_ms = round((time.perf_counter() - t_ret) * 1000.0, 2)

        # 2. Context Engine Bounding
        context_req = ContextRequest(
            query=query,
            retrieval_response=retrieval_resp,
        )
        context_pkg: ContextPackage = self.context_engine.build_context(context_req)

        # Extract source summaries
        sources_summary = [
            {
                "source": item.source.value if hasattr(item.source, "value") else str(item.source),
                "id": item.object_id,
                "title": item.title,
                "citation": item.citation,
                "url": item.url,
            }
            for item in context_pkg.items
        ]

        # 3. LLM Generation
        messages = list(request.history) + [ChatMessage(role="user", content=query)]

        llm_request = LLMRequest(
            task="rag",
            messages=messages,
            context=context_pkg,
            system_instruction=SYSTEM_INSTRUCTION_TUTOR,
            provider=request.provider,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        t_gen = time.perf_counter()
        llm_response = self.gateway.generate(llm_request)
        gen_time_ms = round((time.perf_counter() - t_gen) * 1000.0, 2)
        total_time_ms = round((time.perf_counter() - t_start) * 1000.0, 2)

        # Citations are drawn from LLMResponse (or ContextPackage fallback)
        citations = llm_response.citations or list(context_pkg.citations)
        quota_info = llm_response.metadata.get("quota_info")

        return OrchestrationResponse(
            answer=llm_response.content,
            citations=citations,
            sources=sources_summary,
            provider=llm_response.provider,
            model=llm_response.model,
            prompt_tokens=llm_response.prompt_tokens,
            completion_tokens=llm_response.completion_tokens,
            total_tokens=llm_response.total_tokens,
            retrieval_time_ms=ret_time_ms,
            generation_time_ms=gen_time_ms,
            total_time_ms=total_time_ms,
            metadata={
                "intent": "rag",
                "retrieved_count": len(retrieval_resp.results),
                "context_items_count": context_pkg.total_items,
            },
            quota_info=quota_info,
        )
