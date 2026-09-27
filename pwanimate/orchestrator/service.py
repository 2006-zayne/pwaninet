"""
Pwanimate Orchestrator Service.

Central coordinator bridging user interactions, upstream retrieval, deterministic
domain tool routing, in-memory context bounding, application prompt policy,
and the AI Gateway.
"""

import logging
import os
import re
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from pwanimate.ai.gateway import (
    AIGateway,
    ChatMessage,
    LLMRequest,
    LLMResponse,
    get_task_policy,
)
from pwanimate.ai.gateway.types import AttachmentData
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
    r"^(ok|okay|k|kk|alright|all\s+right|got\s+it|understood|makes\s+sense)[\s\.\!\?]*$",
    r"^(cool|great|nice|awesome|perfect|sweet|good|amazing|wonderful)[\s\.\!\?]*$",
    r"^(yes|yeah|yep|sure|yup|no|nope|nah)[\s\.\!\?]*$",
    r"^(how\s+are\s+you(\s+doing)?|how\s+r\s+u|what\'?s\s+up|wassup|sup)[\s\.\!\?]*$",
    r"^(bye|goodbye|see\s+ya|see\s+you(\s+later)?|cya|take\s+care)[\s\.\!\?]*$",
    r"^(test|testing|ping)[\s\.\!\?]*$",
]


def sanitize_llm_response(text: str) -> str:
    """
    Sanitize raw LLM response text, converting any accidental or synthetic tool-call tokens
    (e.g., <|tool_call_start|>[write(path='...', content='...')]<|tool_call_end|>)
    into standard Markdown fenced code blocks.
    """
    if not text:
        return ""

    if "tool_call" not in text and "[write(" not in text and "write(path=" not in text:
        return text

    def parse_tool_call_content(block: str) -> str:
        cleaned = block.strip()
        if cleaned.startswith("[") and cleaned.endswith("]"):
            cleaned = cleaned[1:-1].strip()

        m_func = re.match(r"([a-zA-Z0-9_]+)\s*\((.*)\)\s*$", cleaned, re.DOTALL)
        if not m_func:
            return block

        func_name = m_func.group(1)
        args_str = m_func.group(2).strip()

        if func_name == "write":
            m_path = re.search(r"path=([\'\"])(.*?)\1", args_str)
            path = m_path.group(2) if m_path else ""
            ext = path.split(".")[-1].lower() if "." in path else "python"
            lang_map = {
                "py": "python",
                "js": "javascript",
                "ts": "typescript",
                "sh": "bash",
                "sql": "sql",
                "json": "json",
                "html": "html",
                "css": "css",
            }
            lang = lang_map.get(ext, ext or "python")

            m_content = re.search(r"content=([\'\"])(.*)", args_str, re.DOTALL)
            if m_content:
                quote = m_content.group(1)
                content = m_content.group(2)
                content = re.sub(rf"{quote}\s*\)?\s*$", "", content)
            else:
                content = args_str

            try:
                content = content.encode("utf-8").decode("unicode_escape")
            except Exception:
                content = (
                    content.replace("\\n", "\n")
                    .replace("\\t", "\t")
                    .replace('\\"', '"')
                    .replace("\\'", "'")
                )

            filename_header = f"### `{path}`\n\n" if path else ""
            return f"{filename_header}```{lang}\n{content.strip()}\n```"

        return block

    # 1. Transform <|tool_call_start|> ... <|tool_call_end|> blocks
    def tool_call_replacer(match: re.Match) -> str:
        inner = match.group(1)
        return "\n\n" + parse_tool_call_content(inner) + "\n\n"

    result = re.sub(
        r"<\|tool_call_start\|>(.*?)<\|tool_call_end\|>",
        tool_call_replacer,
        text,
        flags=re.DOTALL,
    )

    # 2. Catch naked [write(path=..., content=...)]
    def naked_write_replacer(match: re.Match) -> str:
        return "\n\n" + parse_tool_call_content(match.group(0)) + "\n\n"

    result = re.sub(
        r"\[write\(\s*(?:path=[\'\"].*?[\'\"],\s*)?content=[\'\"].*?[\'\"]\s*\)\]",
        naked_write_replacer,
        result,
        flags=re.DOTALL,
    )

    # 3. Clean up any remaining special tags
    result = re.sub(r"<\/?(?:\|tool_call_start\||\|tool_call_end\||tool_call)>", "", result)
    return result.strip()


def extract_attachment_text(attachment: Any, max_chars: int = 15000) -> str:
    """
    Extract bounded textual content from an uploaded document attachment.
    Supports PDF, DOCX, PPTX, TXT, MD, CSV, etc. using Pwanimate extractors.
    """
    file_obj = getattr(attachment, "file", None)
    file_name = getattr(attachment, "file_name", getattr(attachment, "name", "document"))

    file_path = None
    if file_obj:
        try:
            # Try to get the file path - this will fail for cloud storage backends
            potential_path = file_obj.path
            if os.path.exists(potential_path):
                file_path = potential_path
        except (NotImplementedError, AttributeError):
            # Storage backend doesn't support absolute paths (e.g., S3)
            # or path attribute doesn't exist - fall back to direct file reading
            pass

    extracted_text = ""
    if file_path:
        try:
            from pwanimate.ingestion.extractors.factory import extract_document
            extracted_doc = extract_document(file_path, filename=file_name)
            if extracted_doc and extracted_doc.elements:
                extracted_text = "\n\n".join(el.text for el in extracted_doc.elements if el.text)
        except Exception as exc:
            logger.warning("Structural extraction failed for attachment %s: %s", file_name, exc)

    # Fallback to direct text reading if extraction is empty or file has no path
    if not extracted_text and file_obj:
        try:
            file_obj.seek(0)
            raw_bytes = file_obj.read(max_chars * 2)
            file_obj.seek(0)
            text_candidate = raw_bytes.decode("utf-8", errors="replace").replace("\x00", "")
            if text_candidate.strip():
                printable_ratio = sum(c.isprintable() or c in "\n\r\t" for c in text_candidate) / max(1, len(text_candidate))
                if printable_ratio > 0.80:
                    extracted_text = text_candidate
        except Exception as exc:
            logger.warning("Fallback raw read failed for attachment %s: %s", file_name, exc)

    cleaned = (extracted_text or "").strip()
    if not cleaned:
        return f"[No extractable text could be found in '{file_name}']"

    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars].rstrip() + "... [ATTACHMENT TRUNCATED]"
    return cleaned


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

    def _process_attachments(
        self, attachments: List[Any]
    ) -> Tuple[List[AttachmentData], Optional[str]]:
        """
        Process user attachments:
        - Image attachments become AttachmentData with raw bytes for multimodal models.
        - Document attachments have text extracted and bounded into an XML context block.
        """
        if not attachments:
            return [], None

        from django.conf import settings

        max_chars = getattr(settings, "PWANIMATE_MAX_EXTRACT_CHARS", 15000)
        image_attachments: List[AttachmentData] = []
        doc_blocks: List[str] = []

        for att in attachments:
            att_type = getattr(att, "attachment_type", None) or "document"
            att_id = str(getattr(att, "id", uuid.uuid4()))
            att_name = getattr(att, "file_name", getattr(att, "name", "attachment"))
            att_mime = getattr(att, "mime_type", "application/octet-stream")

            if att_type == "image":
                data_bytes = getattr(att, "data_bytes", None)
                if not data_bytes and hasattr(att, "file") and att.file:
                    try:
                        att.file.seek(0)
                        data_bytes = att.file.read()
                        att.file.seek(0)
                    except Exception as e:
                        logger.warning("Could not read bytes from image attachment %s: %s", att_id, e)

                image_attachments.append(
                    AttachmentData(
                        id=att_id,
                        name=att_name,
                        mime_type=att_mime,
                        attachment_type="image",
                        data_bytes=data_bytes,
                        url=getattr(att, "url", f"/api/pwanimate/attachments/{att_id}/view/"),
                    )
                )

            elif att_type == "document":
                extracted_text = extract_attachment_text(att, max_chars=max_chars)
                block = [
                    f'<attachment_context id="{att_id}" filename="{att_name}" type="{att_type}">',
                    f'  <title>{att_name}</title>',
                    '  <content>',
                    f'    {extracted_text}',
                    '  </content>',
                    '</attachment_context>',
                ]
                doc_blocks.append("\n".join(block))

        attachment_context_str = "\n\n".join(doc_blocks) if doc_blocks else None
        return image_attachments, attachment_context_str

    def _resolve_context_resources(
        self, user: Any, context_resources: List[Dict[str, Any]]
    ) -> Tuple[Optional[int], List[Any]]:
        """
        Authorize and resolve client context resources (documents and pages).
        Returns: (filter_document_id, page_chunks)
        """
        if not context_resources or not isinstance(context_resources, list):
            return None, []

        from documents.models import Document
        from pwanimate.retrieval.services.document_retrieval import DocumentSemanticRetrievalService

        doc_retrieval = DocumentSemanticRetrievalService()
        candidate_qs = doc_retrieval.build_candidate_queryset(user=user)

        filter_doc_id = None
        page_chunks: List[Any] = []

        for res in context_resources:
            if not isinstance(res, dict):
                continue
            res_type = str(res.get("type") or res.get("category") or "").lower()
            if res_type in ("document", "doc"):
                doc_id = res.get("id") or res.get("document_id")
                share_id = res.get("share_id") or res.get("document_share_id")
                page_raw = res.get("page") or res.get("page_number")

                doc_obj = None
                if doc_id:
                    try:
                        doc_obj = Document.objects.filter(id=int(doc_id)).first()
                    except (ValueError, TypeError):
                        pass
                elif share_id:
                    try:
                        doc_obj = Document.objects.filter(share_id=share_id).first()
                    except (ValueError, TypeError):
                        pass

                if not doc_obj:
                    continue

                # Verify authorized candidate queryset permits this document
                is_authorized = candidate_qs.filter(document_id=doc_obj.id).exists()
                if not is_authorized:
                    logger.warning(
                        "Context resource document %s not authorized for user %s",
                        doc_obj.id,
                        getattr(user, "id", None),
                    )
                    continue

                filter_doc_id = doc_obj.id

                # If page is specified, attempt page chunks retrieval
                if page_raw is not None:
                    try:
                        page_num = int(page_raw)
                        if page_num > 0 and doc_obj.share_id:
                            chunks = doc_retrieval.get_page_chunks(
                                user=user,
                                document_share_id=doc_obj.share_id,
                                page_number=page_num,
                            )
                            if chunks:
                                page_chunks.extend(chunks)
                    except (ValueError, TypeError):
                        pass

        return filter_doc_id, page_chunks

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

    def _resolve_effective_budget(self, request: OrchestrationRequest, task_category: str) -> int:
        """
        Resolve effective output token ceiling following strict precedence:
        1. Explicit request-level override (if provided)
        2. Task-aware GenerationPolicy (conversational=512, tool=1024, rag=4096)
        3. Fallback safe default (1024)
        """
        if request.max_tokens is not None and request.max_tokens > 0:
            return request.max_tokens
        policy = get_task_policy(task_category)
        return policy.max_output_tokens

    def run(self, request: OrchestrationRequest) -> OrchestrationResponse:
        """
        Execute an end-to-end orchestration turn.

        1. Inspects query intent for conversational pleasantries (bypassed if attachments/context present).
        2. Evaluates high-confidence deterministic domain tool routes.
           If matched: executes authorized tool and grounds response via ContextPackage.
        3. If broad academic/knowledge query or explicit attachment/context turn:
           a. Performs authorized multi-source retrieval (respecting request.user and context filters).
           b. Binds and formats retrieved context + attachment context into ContextPackage.
           c. Formulates LLMRequest with academic tutor system prompt.
           d. Generates normalized response via Gateway.
        4. Packages citations, sources, timing, and response.
        """
        t_start = time.perf_counter()
        query = request.query.strip()

        # Construct current-user context snapshot if not already provided
        if request.user and getattr(request.user, "is_authenticated", False) and request.user_context is None:
            try:
                from pwanimate.context.user_context import UserContextService
                request.user_context = UserContextService().build(request.user)
            except Exception as exc:
                logger.warning("Could not build UserContext for user %s: %s", getattr(request.user, "id", None), exc)

        # If attachments or context resources are present, we bypass purely conversational shortcuts
        has_attachments_or_context = bool(request.attachments or request.context_resources)

        # 1. Check conversational intent
        is_conversational = not has_attachments_or_context and (
            request.task == "general" or self.is_conversational_intent(query)
        )
        if is_conversational:
            return self._run_conversational(request, query, t_start)

        # 2. Check deterministic tool routing (only if no explicit attachments/context overriding intent)
        tool_route = None if has_attachments_or_context else self.tool_router.route(
            query, user=request.user, user_context=request.user_context
        )
        if tool_route:
            return self._run_tool(request, query, tool_route, t_start)

        # 3. Standard / Attachment / Context RAG
        return self._run_rag(request, query, t_start)

    def _run_conversational(
        self,
        request: OrchestrationRequest,
        query: str,
        t_start: float,
    ) -> OrchestrationResponse:
        """Handle pure conversational dialogue turns without retrieval or tools."""
        messages = list(request.history) + [ChatMessage(role="user", content=query)]

        context_pkg = None
        if request.user_context:
            context_pkg = ContextPackage(query=query, user_context=request.user_context)

        effective_max_tokens = self._resolve_effective_budget(request, "conversational")

        llm_request = LLMRequest(
            task="general",
            messages=messages,
            context=context_pkg,
            system_instruction=SYSTEM_INSTRUCTION_CONVERSATIONAL,
            provider=request.provider,
            model=request.model,
            temperature=request.temperature,
            max_tokens=effective_max_tokens,
        )

        t_gen = time.perf_counter()
        llm_response = self.gateway.generate(llm_request)
        gen_time_ms = round((time.perf_counter() - t_gen) * 1000.0, 2)
        total_time_ms = round((time.perf_counter() - t_start) * 1000.0, 2)

        quota_info = llm_response.metadata.get("quota_info")
        sanitized_ans = sanitize_llm_response(llm_response.content)
        if not sanitized_ans or not sanitized_ans.strip():
            logger.warning("Sanitized answer is empty for provider=%s model=%s; applying fallback response", llm_response.provider, llm_response.model)
            sanitized_ans = "I'm sorry, I was unable to generate a response. Please try asking again or rephrasing your question."

        thoughts_tokens = llm_response.metadata.get("thoughts_tokens")
        total_output_tokens = llm_response.metadata.get("total_output_tokens")
        max_output_tokens = llm_response.metadata.get("max_output_tokens", llm_request.max_tokens)

        logger.info(
            "Pwanimate Orchestrator [conversational]: provider=%s model=%s finish_reason=%s prompt_tokens=%s completion_tokens=%s thoughts_tokens=%s total_output_tokens=%s total_tokens=%s max_output_tokens=%s raw_len=%d ans_len=%d duration_ms=%.2f",
            llm_response.provider,
            llm_response.model,
            llm_response.finish_reason,
            llm_response.prompt_tokens,
            llm_response.completion_tokens,
            thoughts_tokens,
            total_output_tokens,
            llm_response.total_tokens,
            max_output_tokens,
            len(llm_response.content),
            len(sanitized_ans),
            total_time_ms,
        )

        return OrchestrationResponse(
            answer=sanitized_ans,
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
            metadata={
                "intent": "conversational",
                "thoughts_tokens": thoughts_tokens,
                "total_output_tokens": total_output_tokens,
                "max_output_tokens": max_output_tokens,
            },
            quota_info=quota_info,
            finish_reason=llm_response.finish_reason,
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
            user_context=request.user_context,
            **tool_route.parameters,
        )
        tool_time_ms = round((time.perf_counter() - t_tool) * 1000.0, 2)

        # Convert tool result to grounded ContextPackage
        context_items = tool_result_to_context_items(tool_route.tool_name, tool_result)
        context_pkg = build_tool_context_package(
            query,
            context_items,
            user_context=request.user_context,
        )

        # Extract people data if people_discovery or user_profile tool ran
        people_results: List[Dict[str, Any]] = []
        if (
            tool_route.tool_name == "people_discovery"
            and tool_result.success
            and isinstance(tool_result.data, list)
        ):
            people_results = list(tool_result.data)
        elif (
            tool_route.tool_name == "user_profile"
            and tool_result.success
            and isinstance(tool_result.data, dict)
        ):
            user_data = tool_result.data
            u_name = user_data.get("username", "")
            d_name = user_data.get("display_name", u_name)
            p_url = user_data.get("profile_url") or f"/users/user/{u_name}/"
            p_avatar = user_data.get("avatar_url") or user_data.get("profile_photo_url")
            p_skills = user_data.get("skills") if isinstance(user_data.get("skills"), list) else []
            p_interests = user_data.get("matched_interests") or [
                i.strip() for i in (user_data.get("interests") or "").split(",") if i.strip()
            ]
            prog_name = (
                user_data.get("programme_name")
                or user_data.get("programme")
                or user_data.get("course")
            )
            acad_level = user_data.get("academic_level") or (
                f"Year {user_data.get('year')}" if user_data.get("year") else None
            )
            people_results = [
                {
                    "user_id": user_data.get("id"),
                    "username": u_name,
                    "display_name": d_name,
                    "headline": user_data.get("headline", ""),
                    "avatar_url": p_avatar,
                    "profile_url": p_url,
                    "programme_name": prog_name,
                    "academic_level": acad_level,
                    "collaboration_status": user_data.get("collaboration_status", ""),
                    "matched_skills": p_skills,
                    "matched_interests": p_interests,
                    "evidence": {},
                    "recommendation_score": 0,
                }
            ]

        sources_summary = self._build_sources_summary(context_pkg.items)

        messages = list(request.history) + [ChatMessage(role="user", content=query)]

        effective_max_tokens = self._resolve_effective_budget(request, "tool")

        llm_request = LLMRequest(
            task="tool",
            messages=messages,
            context=context_pkg,
            system_instruction=SYSTEM_INSTRUCTION_TUTOR,
            provider=request.provider,
            model=request.model,
            temperature=request.temperature,
            max_tokens=effective_max_tokens,
        )

        t_gen = time.perf_counter()
        llm_response = self.gateway.generate(llm_request)
        gen_time_ms = round((time.perf_counter() - t_gen) * 1000.0, 2)
        total_time_ms = round((time.perf_counter() - t_start) * 1000.0, 2)

        citations = llm_response.citations or list(context_pkg.citations)
        quota_info = llm_response.metadata.get("quota_info")
        sanitized_ans = sanitize_llm_response(llm_response.content)
        if not sanitized_ans or not sanitized_ans.strip():
            logger.warning("Sanitized answer is empty for tool route provider=%s model=%s; applying fallback response", llm_response.provider, llm_response.model)
            sanitized_ans = "I'm sorry, I was unable to generate a response. Please try asking again or rephrasing your question."

        thoughts_tokens = llm_response.metadata.get("thoughts_tokens")
        total_output_tokens = llm_response.metadata.get("total_output_tokens")
        max_output_tokens = llm_response.metadata.get("max_output_tokens", llm_request.max_tokens)

        logger.info(
            "Pwanimate Orchestrator [tool:%s]: provider=%s model=%s finish_reason=%s prompt_tokens=%s completion_tokens=%s thoughts_tokens=%s total_output_tokens=%s total_tokens=%s max_output_tokens=%s raw_len=%d ans_len=%d duration_ms=%.2f",
            tool_route.tool_name,
            llm_response.provider,
            llm_response.model,
            llm_response.finish_reason,
            llm_response.prompt_tokens,
            llm_response.completion_tokens,
            thoughts_tokens,
            total_output_tokens,
            llm_response.total_tokens,
            max_output_tokens,
            len(llm_response.content),
            len(sanitized_ans),
            total_time_ms,
        )

        return OrchestrationResponse(
            answer=sanitized_ans,
            citations=citations,
            sources=sources_summary,
            people=people_results,
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
                "thoughts_tokens": thoughts_tokens,
                "total_output_tokens": total_output_tokens,
                "max_output_tokens": max_output_tokens,
            },
            quota_info=quota_info,
            finish_reason=llm_response.finish_reason,
        )

    def _run_rag(
        self,
        request: OrchestrationRequest,
        query: str,
        t_start: float,
    ) -> OrchestrationResponse:
        """Handle knowledge/retrieval-augmented dialogue turns."""
        # 0. Process attachments (images for vision, docs for prompt context)
        image_attachments, attachment_context = self._process_attachments(request.attachments)

        # 1. Resolve authorized context resources (active document / page filtering)
        filter_doc_id, page_chunks = self._resolve_context_resources(
            request.user, request.context_resources
        )

        # 2. Upstream Authorized Retrieval
        t_ret = time.perf_counter()
        if page_chunks:
            retrieval_resp = RetrievalResponse(
                query=query,
                results=page_chunks,
                total_count=len(page_chunks),
                execution_time_ms=0.0,
            )
        else:
            sources = request.sources or [SourceType.DOCUMENT, SourceType.POST]
            filters = {}
            if filter_doc_id:
                filters["document_id"] = filter_doc_id

            retrieval_req = RetrievalRequest(
                query=query,
                user=request.user,
                sources=sources,
                mode=RetrievalMode.HYBRID,
                filters=filters,
            )
            retrieval_resp = self.retrieval_service.retrieve(retrieval_req)
        ret_time_ms = round((time.perf_counter() - t_ret) * 1000.0, 2)

        # 3. Context Engine Bounding
        context_req = ContextRequest(
            query=query,
            retrieval_response=retrieval_resp,
            user_context=request.user_context,
        )
        context_pkg: ContextPackage = self.context_engine.build_context(context_req)
        if attachment_context:
            context_pkg.attachment_context = attachment_context

        # Extract source summaries (deduplicated & enriched)
        sources_summary = self._build_sources_summary(context_pkg.items)

        # 4. LLM Generation
        last_user_msg = ChatMessage(role="user", content=query, attachments=image_attachments)
        messages = list(request.history) + [last_user_msg]

        effective_max_tokens = self._resolve_effective_budget(request, "rag")

        llm_request = LLMRequest(
            task="rag",
            messages=messages,
            context=context_pkg,
            system_instruction=SYSTEM_INSTRUCTION_TUTOR,
            provider=request.provider,
            model=request.model,
            temperature=request.temperature,
            max_tokens=effective_max_tokens,
            attachments=image_attachments,
        )

        t_gen = time.perf_counter()
        llm_response = self.gateway.generate(llm_request)
        gen_time_ms = round((time.perf_counter() - t_gen) * 1000.0, 2)
        total_time_ms = round((time.perf_counter() - t_start) * 1000.0, 2)

        # Citations are drawn from LLMResponse (or ContextPackage fallback)
        citations = llm_response.citations or list(context_pkg.citations)
        quota_info = llm_response.metadata.get("quota_info")
        sanitized_ans = sanitize_llm_response(llm_response.content)
        if not sanitized_ans or not sanitized_ans.strip():
            logger.warning("Sanitized answer is empty for rag provider=%s model=%s; applying fallback response", llm_response.provider, llm_response.model)
            sanitized_ans = "I'm sorry, I was unable to generate a response. Please try asking again or rephrasing your question."

        thoughts_tokens = llm_response.metadata.get("thoughts_tokens")
        total_output_tokens = llm_response.metadata.get("total_output_tokens")
        max_output_tokens = llm_response.metadata.get("max_output_tokens", llm_request.max_tokens)

        logger.info(
            "Pwanimate Orchestrator [rag]: provider=%s model=%s finish_reason=%s prompt_tokens=%s completion_tokens=%s thoughts_tokens=%s total_output_tokens=%s total_tokens=%s max_output_tokens=%s raw_len=%d ans_len=%d duration_ms=%.2f",
            llm_response.provider,
            llm_response.model,
            llm_response.finish_reason,
            llm_response.prompt_tokens,
            llm_response.completion_tokens,
            thoughts_tokens,
            total_output_tokens,
            llm_response.total_tokens,
            max_output_tokens,
            len(llm_response.content),
            len(sanitized_ans),
            total_time_ms,
        )

        return OrchestrationResponse(
            answer=sanitized_ans,
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
                "thoughts_tokens": thoughts_tokens,
                "total_output_tokens": total_output_tokens,
                "max_output_tokens": max_output_tokens,
            },
            quota_info=quota_info,
            finish_reason=llm_response.finish_reason,
        )

    def _build_sources_summary(self, context_items: list) -> List[Dict[str, Any]]:
        """
        Build deduplicated, enriched source summaries from context items.
        Preserves canonical resource metadata (type, media, author, creation date)
        while avoiding redundant duplicate badges from the same document version.
        """
        seen_keys = set()
        summary: List[Dict[str, Any]] = []

        for item in context_items:
            src_val = item.source.value if hasattr(item.source, "value") else str(item.source)
            # Deduplicate by canonical URL or (source, id)
            dedup_key = (src_val, item.url) if item.url else (src_val, str(item.object_id))
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)

            meta = item.metadata if isinstance(item.metadata, dict) else {}
            res_type = meta.get("resource_type") or meta.get("chunk_type") or meta.get("file_type") or src_val
            file_ext = meta.get("file_type") or meta.get("extension") or ""
            author_val = meta.get("author") or meta.get("author_username") or meta.get("author_name") or ""
            created_val = meta.get("created_at") or ""

            summary_dict: Dict[str, Any] = {
                "source": src_val,
                "id": item.object_id,
                "title": item.title,
                "citation": item.citation,
                "url": item.url,
                "resource_type": res_type,
                "file_extension": file_ext,
                "media_url": meta.get("media_url") or "",
                "thumbnail_url": meta.get("thumbnail_url") or meta.get("thumbnail") or "",
                "hls_url": meta.get("hls_url") or "",
                "author": author_val,
                "created_at": str(created_val) if created_val else "",
                "page_number": meta.get("page_number"),
                "document_id": meta.get("document_id"),
                "document_share_id": meta.get("document_share_id") or "",
                "file_type": meta.get("file_type") or file_ext or "",
            }

            if (
                src_val == "user"
                and meta
                and item.object_id not in ("people_none", "user_none")
            ):
                summary_dict["person"] = meta

            summary.append(summary_dict)

        return summary
