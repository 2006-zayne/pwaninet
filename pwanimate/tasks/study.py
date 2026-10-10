"""
Celery background tasks for Pwanimate Study Mode.
"""

from __future__ import annotations

import logging
from typing import Optional

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="pwanimate.tasks.generate_study_checkpoint_task",
    max_retries=1,
    default_retry_delay=15,
    acks_late=True,
)
def generate_study_checkpoint_task(
    self,
    session_id: str,
    up_to_message_id: Optional[str] = None,
) -> dict:
    """
    Generate a structured learning checkpoint for a Study Mode session asynchronously.
    Safe against duplicate or out-of-order execution.
    """
    from pwanimate.services.study_session import StudySessionService

    try:
        checkpoint = StudySessionService.generate_checkpoint(
            session_id=session_id,
            up_to_message_id=up_to_message_id,
        )
        if checkpoint is None:
            return {"status": "skipped", "session_id": str(session_id)}
        return {
            "status": "ok",
            "session_id": str(session_id),
            "checkpoint_id": str(checkpoint.id),
            "up_to_message_id": str(checkpoint.up_to_message_id) if checkpoint.up_to_message_id else None,
        }
    except Exception as exc:
        logger.warning(
            "Study checkpoint task failed for session %s: %s",
            session_id,
            exc,
        )
        return {
            "status": "error",
            "session_id": str(session_id),
            "error": type(exc).__name__,
        }
