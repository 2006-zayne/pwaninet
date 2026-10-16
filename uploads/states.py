"""Upload lifecycle state machine contract (Phase 1).

Single source of truth for legal status transitions. Both the Django models
and (later) the shared JS client enforce this map: no transition may create a
second post, and retries always re-enter at the earliest unverified step.
"""

QUEUED = "queued"
PREPARING = "preparing"
UPLOADING = "uploading"
VERIFYING = "verifying"
PROCESSING = "processing"
PUBLISHING = "publishing"
COMPLETED = "completed"
PAUSED = "paused"
FAILED = "failed"
CANCELLED = "cancelled"

TERMINAL_STATES = frozenset({COMPLETED, CANCELLED})

# Resume targets: a paused/failed record may re-enter at any of these,
# chosen by the retry logic based on verified server state.
RESUMABLE_STATES = frozenset({PREPARING, UPLOADING, VERIFYING, PROCESSING, PUBLISHING})

TRANSITIONS = {
    QUEUED: {PREPARING, CANCELLED},
    PREPARING: {UPLOADING, FAILED, CANCELLED},
    UPLOADING: {VERIFYING, PAUSED, FAILED, CANCELLED},
    VERIFYING: {PROCESSING, UPLOADING, FAILED, CANCELLED},
    PROCESSING: {PUBLISHING, PAUSED, FAILED, CANCELLED},
    PUBLISHING: {COMPLETED, FAILED, CANCELLED},
    PAUSED: {PREPARING, UPLOADING, VERIFYING, PROCESSING, PUBLISHING, CANCELLED},
    FAILED: {PREPARING, UPLOADING, VERIFYING, PROCESSING, PUBLISHING, CANCELLED},
    COMPLETED: set(),
    CANCELLED: set(),
}

# 8 MiB parts: S3 multipart range is 5 MiB–5 GiB, max 10k parts.
PART_SIZE_BYTES = 8 * 1024 * 1024
# Files at or under this size use a single presigned PUT, no multipart.
SINGLE_PUT_MAX_BYTES = 10 * 1024 * 1024


def can_transition(from_state, to_state):
    return to_state in TRANSITIONS.get(from_state, set())
