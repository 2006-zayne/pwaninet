"""
Periodic Celery tasks for automatic Pwanimate document ingestion reconciliation.
"""

import logging
from typing import Dict, Any
from celery import shared_task

from ..services.reconciliation import DocumentReconciliationService

logger = logging.getLogger("pwanimate.reconciliation")


@shared_task(
    bind=True,
    max_retries=1,
    default_retry_delay=60,
    name="pwanimate.tasks.reconciliation.reconcile_document_ingestion",
)
def reconcile_document_ingestion(self, dry_run: bool = False) -> Dict[str, Any]:
    """
    Periodic reconciliation task.

    Inspects document versions across PwaniNet, detects ingestion gaps or incomplete
    embeddings, and safely dispatches existing worker tasks with distributed locking.
    """
    logger.info("[PWANIMATE-RECONCILER] Starting periodic reconciliation task.")
    try:
        service = DocumentReconciliationService()
        return service.reconcile(dry_run=dry_run)
    except Exception as exc:
        logger.error("[PWANIMATE-RECONCILER] Unexpected reconciliation error: %s", exc, exc_info=True)
        raise self.retry(exc=exc)
