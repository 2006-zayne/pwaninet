# Pwanimate app

## Purpose

`pwanimate` is the assistant and AI-context experience inside PwaniNet. It stores assistant conversations and messages, manages attachments and chunks, and contains retrieval, provider, and orchestration services.

## Main data

Models include `PwanimateConversation`, `PwanimateMessage`, `PwanimateAttachment`, `PwanimateAttachmentChunk`, `DocumentChunk`, and user preferences such as tone and response style.

## Main journeys and routes

The UI is mounted at `/pwanimate/`; API routes are mounted at `/api/pwanimate/`. The app includes conversation history, settings/personalization, usage/about screens, retrieval, ingestion, task modules, and service integrations.

## External services

Settings expose optional Gemini, Groq, OpenRouter, Jina, Voyage, and Cloudflare embedding/model configuration. Only providers configured and called in the deployed environment receive data. Confirm exact provider use and data sent before describing the feature publicly.

## Developer notes

- User prompts, conversation history, and uploaded attachments may contain personal or sensitive content. Preserve ownership, access controls, retention, and provider-routing safeguards.
- Private generated documents have dedicated storage configuration; do not route them through the public media CDN by mistake.
- Keep provider credentials in environment variables and never log them or commit them.
