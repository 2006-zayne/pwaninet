"""
Management command to backfill and recover Pwanimate DocumentChunks and embeddings.

Safely orchestrates historical document ingestion and pending/failed embedding recovery
using the existing Celery asynchronous pipeline.
"""

from typing import Any, Dict, List, Optional
from django.core.management.base import BaseCommand
from django.db import models
from django.db.models import Count, Q, Min, Max

from documents.models import Document, DocumentVersion, DocumentFile
from pwanimate.models import DocumentChunk
from pwanimate.tasks.ingestion import ingest_document_version
from pwanimate.tasks.embeddings import embed_document_version
from pwanimate.services.reconciliation import classify_version_health, DocumentReconciliationService


class Command(BaseCommand):
    help = "Backfill Pwanimate document chunks and recover incomplete embeddings."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate execution without modifying the database or dispatching tasks.",
        )
        parser.add_argument(
            "--document-id",
            type=int,
            default=None,
            help="Restrict operation to a specific document ID.",
        )
        parser.add_argument(
            "--version-id",
            type=int,
            default=None,
            help="Restrict operation to a specific document version ID.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Maximum number of versions to dispatch.",
        )
        parser.add_argument(
            "--retry-pending",
            "--retry-embeddings",
            dest="retry_embeddings",
            action="store_true",
            help="Resume embeddings for versions with pending or failed chunks without re-chunking.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force re-ingestion of versions that already have chunks (purges and recreates).",
        )
        parser.add_argument(
            "--report",
            action="store_true",
            help="Generate a read-only inventory and health report of documents and chunks.",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        retry_mode = options.get("retry_embeddings", False)
        report_mode = options.get("report", False)
        doc_id = options.get("document_id")
        version_id = options.get("version_id")
        limit = options.get("limit")
        force = options.get("force", False)

        if report_mode:
            self._handle_report(doc_id=doc_id, version_id=version_id, limit=limit)
            return

        if retry_mode:
            self._handle_retry_embeddings(
                doc_id=doc_id,
                version_id=version_id,
                limit=limit,
                dry_run=dry_run,
            )
            return

        # Default: Backfill 0-chunk documents
        self._handle_backfill(
            doc_id=doc_id,
            version_id=version_id,
            limit=limit,
            dry_run=dry_run,
            force=force,
        )

    def _get_base_queryset(
        self,
        doc_id: Optional[int] = None,
        version_id: Optional[int] = None,
    ):
        """Build base DocumentVersion queryset filtered by ID constraints."""
        qs = DocumentVersion.objects.select_related("document").prefetch_related("files")
        if doc_id is not None:
            qs = qs.filter(document_id=doc_id)
        if version_id is not None:
            qs = qs.filter(id=version_id)
        return qs.order_by("document_id", "version_number")

    def _classify_version_health(
        self,
        total_chunks: int,
        completed_chunks: int,
        pending_chunks: int,
        failed_chunks: int,
        has_file: bool,
    ) -> str:
        """Classify health state of a document version using shared service."""
        return classify_version_health(
            total_chunks=total_chunks,
            completed_chunks=completed_chunks,
            pending_chunks=pending_chunks,
            failed_chunks=failed_chunks,
            has_file=has_file,
        )

    def _handle_report(
        self,
        doc_id: Optional[int] = None,
        version_id: Optional[int] = None,
        limit: Optional[int] = None,
    ):
        """Generate a comprehensive read-only audit report of document chunk status."""
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== Pwanimate Document Ingestion & Chunk Audit Report ===\n"))

        versions = self._get_base_queryset(doc_id=doc_id, version_id=version_id)
        if limit is not None and limit > 0:
            versions = versions[:limit]

        version_list = list(versions)
        if not version_list:
            self.stdout.write("No matching document versions found.")
            return

        total_versions = len(version_list)
        status_counts: Dict[str, int] = {}
        total_chunks_all = 0
        completed_all = 0
        pending_all = 0
        failed_all = 0

        for v in version_list:
            doc = v.document
            first_file = v.files.first()
            file_type = getattr(first_file, "extension", "") or "unknown"
            file_status = getattr(first_file, "processing_status", "") or "n/a"
            has_file = first_file is not None

            chunk_qs = v.chunks.all()
            total_chunks = chunk_qs.count()
            completed = chunk_qs.filter(embedding_status="completed").count()
            pending = chunk_qs.filter(embedding_status="pending").count()
            failed = chunk_qs.filter(embedding_status="failed").count()
            active = chunk_qs.filter(is_active=True).count()

            total_chunks_all += total_chunks
            completed_all += completed
            pending_all += pending
            failed_all += failed

            health = self._classify_version_health(
                total_chunks, completed, pending, failed, has_file
            )
            status_counts[health] = status_counts.get(health, 0) + 1

            # Page coverage calculation for paginated formats (PDF)
            page_coverage_str = "n/a"
            if file_type.lower() == "pdf" and total_chunks > 0:
                agg = chunk_qs.aggregate(
                    min_p=Min("page_number"),
                    max_p=Max("page_end"),
                )
                min_p = agg["min_p"]
                max_p = agg["max_p"]
                distinct_pages = (
                    chunk_qs.filter(page_number__isnull=False)
                    .values("page_number")
                    .distinct()
                    .count()
                )
                if min_p is not None and max_p is not None:
                    page_coverage_str = f"pp. {min_p}–{max_p} ({distinct_pages} distinct pages covered)"
                elif min_p is not None:
                    page_coverage_str = f"p. {min_p}"

            # Format individual document card
            self.stdout.write(
                f"Document {doc.id:<3d} | Version {v.version_number:<2d} (id: {v.id:<3d}) | "
                f"[{health}] {doc.title[:45]}"
            )
            self.stdout.write(
                f"  Format: {file_type.upper():<5} | Doc Status: {doc.status:<8} | File Status: {file_status}"
            )
            self.stdout.write(
                f"  Chunks: total={total_chunks:<4} completed={completed:<4} "
                f"pending={pending:<4} failed={failed:<4} active={active:<4}"
            )
            if file_type.lower() == "pdf":
                self.stdout.write(f"  Page Coverage: {page_coverage_str}")
            self.stdout.write("")

        # Summary footer
        self.stdout.write(self.style.MIGRATE_HEADING("Report Summary"))
        self.stdout.write("-" * 40)
        self.stdout.write(f"Total Versions Inspected: {total_versions}")
        for st, cnt in sorted(status_counts.items()):
            self.stdout.write(f"  {st:<22}: {cnt}")
        self.stdout.write("-" * 40)
        self.stdout.write(f"Total Chunks:     {total_chunks_all}")
        self.stdout.write(f"Total Completed:  {completed_all}")
        self.stdout.write(f"Total Pending:    {pending_all}")
        self.stdout.write(f"Total Failed:     {failed_all}\n")

    def _handle_backfill(
        self,
        doc_id: Optional[int] = None,
        version_id: Optional[int] = None,
        limit: Optional[int] = None,
        dry_run: bool = False,
        force: bool = False,
    ):
        """Orchestrate ingestion for versions that have 0 chunks (or force rebuild)."""
        if dry_run:
            self.stdout.write(self.style.NOTICE("DRY RUN: No tasks will be dispatched.\n"))

        versions = self._get_base_queryset(doc_id=doc_id, version_id=version_id)
        version_list = list(versions)

        discovered = len(version_list)
        eligible_versions: List[DocumentVersion] = []
        skipped_healthy = 0
        skipped_invalid = 0

        for v in version_list:
            chunk_count = v.chunks.count()
            first_file = v.files.first()

            if not first_file:
                skipped_invalid += 1
                continue

            if chunk_count > 0 and not force:
                skipped_healthy += 1
                continue

            eligible_versions.append(v)

        if limit is not None and limit > 0:
            eligible_versions = eligible_versions[:limit]

        if dry_run:
            self.stdout.write(f"Found {len(eligible_versions)} eligible document versions.\n")
            for v in eligible_versions:
                doc = v.document
                first_file = v.files.first()
                ext = getattr(first_file, "extension", "") or "unknown"
                c_count = v.chunks.count()
                self.stdout.write(
                    f"Document {doc.id:<3d} | version {v.version_number:<2d} | "
                    f"{doc.title[:35]} | {ext.upper()} | chunks={c_count}"
                )
            self.stdout.write("")
        else:
            dispatched_count = 0
            for v in eligible_versions:
                doc = v.document
                first_file = v.files.first()
                ext = getattr(first_file, "extension", "") or "unknown"

                # Asynchronous Celery dispatch
                ingest_document_version.delay(v.id, force=force)
                dispatched_count += 1

                self.stdout.write(
                    f"Dispatched ingestion for Document {doc.id} (version {v.id}): '{doc.title[:40]}'"
                )

        # Print standard summary block
        self.stdout.write(self.style.MIGRATE_HEADING("\nBackfill Summary"))
        self.stdout.write("-" * 25)
        self.stdout.write(f"Versions discovered: {discovered}")
        if dry_run:
            self.stdout.write(f"Eligible to dispatch: {len(eligible_versions)}")
        else:
            self.stdout.write(f"Versions dispatched:  {len(eligible_versions)}")
        self.stdout.write(f"Skipped healthy:      {skipped_healthy}")
        self.stdout.write(f"Skipped invalid:      {skipped_invalid}\n")

    def _handle_retry_embeddings(
        self,
        doc_id: Optional[int] = None,
        version_id: Optional[int] = None,
        limit: Optional[int] = None,
        dry_run: bool = False,
    ):
        """Resume embedding generation for chunks stuck in pending or failed status."""
        if dry_run:
            self.stdout.write(self.style.NOTICE("DRY RUN: No embedding tasks will be dispatched.\n"))

        versions = self._get_base_queryset(doc_id=doc_id, version_id=version_id)
        version_list = list(versions)

        docs_checked = 0
        total_pending = 0
        total_failed = 0
        eligible_versions: List[Dict[str, Any]] = []

        for v in version_list:
            docs_checked += 1
            chunk_qs = v.chunks.all()
            pending_count = chunk_qs.filter(embedding_status="pending").count()
            failed_count = chunk_qs.filter(embedding_status="failed").count()

            if pending_count > 0 or failed_count > 0:
                total_pending += pending_count
                total_failed += failed_count
                eligible_versions.append({
                    "version": v,
                    "pending": pending_count,
                    "failed": failed_count,
                    "total": chunk_qs.count(),
                    "completed": chunk_qs.filter(embedding_status="completed").count(),
                    "active": chunk_qs.filter(is_active=True).count(),
                })

        if limit is not None and limit > 0:
            eligible_versions = eligible_versions[:limit]

        # Individual version details
        for item in eligible_versions:
            v = item["version"]
            doc = v.document
            self.stdout.write(f"Document: {doc.id}")
            self.stdout.write(f"Version:  {v.version_number} (id: {v.id})")
            self.stdout.write(f"Title:    {doc.title}\n")
            self.stdout.write("Chunks:")
            self.stdout.write(f"  Total:      {item['total']}")
            self.stdout.write(f"  Completed:  {item['completed']}")
            self.stdout.write(f"  Pending:    {item['pending']}")
            self.stdout.write(f"  Failed:     {item['failed']}")
            self.stdout.write(f"  Active:     {item['active']}")

            if dry_run:
                self.stdout.write("  Action:     would dispatch embed_document_version\n")
            else:
                embed_document_version.delay(version_id=v.id)
                self.stdout.write("  Action:     dispatched embed_document_version task to Celery\n")

        # Print embedding recovery summary
        self.stdout.write(self.style.MIGRATE_HEADING("Embedding Recovery"))
        self.stdout.write("-" * 25)
        self.stdout.write(f"Documents checked:    {docs_checked}")
        self.stdout.write(f"Pending chunks:       {total_pending}")
        self.stdout.write(f"Failed chunks:        {total_failed}")
        if dry_run:
            self.stdout.write(f"Versions to dispatch: {len(eligible_versions)}\n")
        else:
            self.stdout.write(f"Versions dispatched:  {len(eligible_versions)}\n")
