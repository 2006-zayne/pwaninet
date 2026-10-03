# Pwanimate app

## Purpose

`pwanimate` is the assistant experience inside PwaniNet. It stores conversations, messages, user preferences, attachments, and searchable document chunks. Its current implementation is built in this repository; it does not use the separately vendored LangChain checkout as its runtime orchestration layer.

## Main data

Models include `PwanimateConversation`, `PwanimateMessage`, `PwanimateAttachment`, `PwanimateAttachmentChunk`, `DocumentChunk`, and preferences such as tone and response style. `DocumentChunk` stores vector embeddings through `pgvector` and links chunks to source documents/versions where applicable.

## Main journeys and routes

The UI is mounted at `/pwanimate/`; API routes are mounted at `/api/pwanimate/`. The API supports chat, conversation history, generated resources, attachment upload/status/media/download, context-document search, quota status, and voice transcription (sent to Groq when configured). The UI includes conversation history and personalization, usage, and about screens.

## How a response is assembled

`pwanimate/orchestrator/service.py` coordinates a request. The context engine and user-context service build relevant student context; retrieval searches document chunks; the tool router can call domain tools for academic data, people, groups, documents, notifications, profile data, and site search. The AI gateway normalizes provider requests and responses. It currently has Gemini, Groq, and OpenRouter LLM adapters, plus a mock adapter for development/tests. A quota tracker and configured fallback chain help handle provider rate limits and availability. Provider configuration is read from Django settings/environment variables.

Document ingestion uses local extractors for PDF, DOCX, PPTX, and text-like formats, then structure-aware chunking, embeddings, and PostgreSQL vector search. Background ingestion, embedding, attachment processing, and reconciliation tasks are registered with Celery. Generated downloadable resources are rendered in the app's services.

## External services

LLM providers are Gemini, Groq, and OpenRouter. Embedding providers are Gemini, Jina, Voyage, and Cloudflare; a mock embedding provider supports local/testing use. The active providers depend on settings and credentials. The implementation calls provider HTTP APIs with `requests`; it does not require a provider-specific Python SDK. Only providers configured and called in the deployed environment receive request or embedding data. Confirm exact provider use and data sent before describing the feature publicly.

Optional public web search uses one provider-neutral `web_search` tool backed by Tavily, Brave Search, and Serper adapters. The configured order determines fallback priority; blank keys do not prevent startup. See the [web-search developer guide](pwanimate-web-search.md) for configuration and tests.

## Developer notes

- User prompts, conversation history, and uploaded attachments may contain personal or sensitive content. Preserve ownership, access controls, retention, and provider-routing safeguards.
- Private generated documents have dedicated storage configuration; do not route them through the public media CDN by mistake.
- Keep provider credentials in environment variables and never log them or commit them.
- Read [the site owner guide](../site-owner-guide.md) for the end-to-end assistant flow and the role of its libraries.
- `pwanimate/repos/frameworks/langchain/` and `openai-quickstart-python/` are vendored study/reference material, not installed dependencies of the live assistant.
- Browser rendering uses locally served Marked, DOMPurify, KaTeX, and Prism assets for Markdown, sanitization, equations, and code highlighting.
