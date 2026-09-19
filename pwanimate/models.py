"""Pwanimate Domain Models.

Phase 2C: MVP DocumentChunk Persistence.
Establishes a reliable, version-aware database representation for
structured document chunks produced by extraction and chunking pipelines.
"""

import hashlib
import uuid
from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from pgvector.django import VectorField


class DocumentChunk(models.Model):
    """
    Represents an atomic, ordered, version-aware structural chunk of a document.

    Each chunk belongs authoritatively to a specific DocumentVersion and inherits
    its relationship to the root Document. Chunks preserve structural provenance
    (page numbers, slide numbers, section headings, element types) without duplicating
    the full academic hierarchy, keeping retrieval grounded and citation-ready.
    """

    CHUNK_TYPE_CHOICES = [
        ('heading', 'Heading'),
        ('paragraph', 'Paragraph'),
        ('table', 'Table'),
        ('slide', 'Slide'),
        ('notes', 'Notes'),
        ('code', 'Code'),
        ('text', 'Text'),
    ]

    EMBEDDING_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    # Identity & Relationships
    id = models.BigAutoField(primary_key=True)
    document = models.ForeignKey(
        'documents.Document',
        on_delete=models.CASCADE,
        related_name='chunks',
        help_text="Source document"
    )
    document_version = models.ForeignKey(
        'documents.DocumentVersion',
        on_delete=models.CASCADE,
        related_name='chunks',
        help_text="Specific document version that produced this chunk"
    )

    # Deterministic Ordering
    chunk_index = models.PositiveIntegerField(
        validators=[MinValueValidator(0)],
        help_text="Zero-based sequence index within the document version"
    )

    # Content & Integrity
    content = models.TextField(
        help_text="Extracted text content of the chunk"
    )
    content_hash = models.CharField(
        max_length=64,
        db_index=True,
        help_text="SHA-256 hash of content for change and duplicate detection"
    )

    # Structural Provenance
    chunk_type = models.CharField(
        max_length=30,
        choices=CHUNK_TYPE_CHOICES,
        default='paragraph',
        db_index=True,
        help_text="Semantic structural element type"
    )
    page_number = models.PositiveIntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Starting page number (1-indexed, for paginated formats like PDF)"
    )
    page_end = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Ending page number if chunk spans multiple pages"
    )
    slide_number = models.PositiveIntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Slide number (1-indexed, for presentations like PPTX)"
    )
    section_heading = models.CharField(
        max_length=300,
        blank=True,
        default='',
        help_text="Active section or chapter heading context"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional location provenance (bbox coordinates, table row count, notes flags)"
    )

    # Lifecycle State
    is_active = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this chunk is active and eligible for retrieval"
    )

    # Embedding Metadata & Vector Storage (Phase 2F)
    embedding = VectorField(
        dimensions=768,
        null=True,
        blank=True,
        help_text="Vector embedding of chunk content (768 dimensions for text-embedding-004)"
    )
    embedding_status = models.CharField(
        max_length=20,
        choices=EMBEDDING_STATUS_CHOICES,
        default='pending',
        db_index=True,
        help_text="Lifecycle status of vector embedding generation"
    )
    embedding_model = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text="Model identifier used to produce vector embeddings"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['document_version', 'chunk_index']
        verbose_name = "Document Chunk"
        verbose_name_plural = "Document Chunks"
        constraints = [
            models.UniqueConstraint(
                fields=['document_version', 'chunk_index'],
                name='pwanimate_chunk_version_index_uniq'
            ),
            models.CheckConstraint(
                check=models.Q(chunk_index__gte=0),
                name='pwanimate_chunk_index_non_negative'
            ),
            models.CheckConstraint(
                check=~models.Q(content=''),
                name='pwanimate_chunk_content_not_empty'
            ),
        ]
        indexes = [
            models.Index(fields=['document_version', 'chunk_index']),
            models.Index(fields=['document_version', 'is_active']),
            models.Index(fields=['document', 'is_active']),
            models.Index(fields=['page_number']),
            models.Index(fields=['slide_number']),
        ]

    def __str__(self):
        return f"{self.document.title} [v{self.document_version.version_number}:{self.chunk_index}]"

    def clean(self):
        super().clean()
        if self.document_version_id and self.document_id:
            if self.document_id != self.document_version.document_id:
                raise ValidationError({
                    'document_version': 'Document version must belong to the referenced document.'
                })

    def save(self, *args, **kwargs):
        # Auto-fill document from document_version if omitted
        if self.document_version_id and not self.document_id:
            self.document_id = self.document_version.document_id

        # Auto-compute SHA-256 content hash if not set
        if not self.content_hash and self.content:
            self.content_hash = hashlib.sha256(self.content.encode('utf-8')).hexdigest()

        self.clean()
        super().save(*args, **kwargs)

    @property
    def char_count(self) -> int:
        """Character count of chunk content."""
        return len(self.content) if self.content else 0

    def activate(self):
        """Activate chunk for retrieval."""
        self.is_active = True
        self.save(update_fields=['is_active', 'updated_at'])

    def deactivate(self):
        """Deactivate chunk from retrieval."""
        self.is_active = False
        self.save(update_fields=['is_active', 'updated_at'])


class PwanimateConversation(models.Model):
    """
    Persistent conversational thread between an authenticated student and Pwanimate.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pwanimate_conversations",
        db_index=True,
    )
    title = models.CharField(
        max_length=255,
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        db_index=True,
    )

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["user", "-updated_at"]),
        ]

    def __str__(self):
        return f"{self.title or 'Conversation'} ({self.id})"


class PwanimateMessage(models.Model):
    """
    Individual conversational turn within a Pwanimate conversation.
    """
    ROLE_CHOICES = [
        ("user", "User"),
        ("assistant", "Assistant"),
    ]

    id = models.BigAutoField(primary_key=True)
    conversation = models.ForeignKey(
        PwanimateConversation,
        on_delete=models.CASCADE,
        related_name="messages",
        db_index=True,
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        db_index=True,
    )
    content = models.TextField()
    citations = models.JSONField(
        default=list,
        blank=True,
    )
    sources = models.JSONField(
        default=list,
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
        ]

    def clean(self):
        super().clean()
        if self.role not in dict(self.ROLE_CHOICES):
            raise ValidationError(f"Invalid role '{self.role}'. Only 'user' and 'assistant' are allowed.")
        if not self.content or not self.content.strip():
            raise ValidationError("Message content cannot be empty.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.role.capitalize()} message in {self.conversation_id}"

    @property
    def people(self) -> list:
        """
        Extract structured person profiles from persisted sources if present.
        Returns empty list if no people discovery items were associated with this turn.
        """
        if not self.sources or not isinstance(self.sources, list):
            return []
        people_list = []
        for src in self.sources:
            if isinstance(src, dict) and src.get("source") == "user":
                person = src.get("person")
                if isinstance(person, dict) and person.get("username"):
                    people_list.append(person)
        return people_list


class PwanimateTone(models.TextChoices):
    """Controlled tone choices for Pwanimate assistant interactions."""
    NEUTRAL = "neutral", "Neutral"
    FRIENDLY = "friendly", "Friendly"
    PROFESSIONAL = "professional", "Professional"
    ACADEMIC = "academic", "Academic"


class PwanimateResponseStyle(models.TextChoices):
    """Controlled response style choices for Pwanimate assistant interactions."""
    CONCISE = "concise", "Concise"
    BALANCED = "balanced", "Balanced"
    DETAILED = "detailed", "Detailed"


class PwanimatePreferences(models.Model):
    """
    Dedicated AI assistant personalization preferences for an authenticated student.

    Strictly decoupled from PwaniNet platform account settings.
    Enforces a strict 1-to-1 relationship with the Django User model.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pwanimate_preferences",
        primary_key=True,
    )
    nickname = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Optional preferred name Pwanimate uses when addressing the student",
    )
    tone = models.CharField(
        max_length=20,
        choices=PwanimateTone.choices,
        default=PwanimateTone.NEUTRAL,
        db_index=True,
        help_text="Assistant conversational tone",
    )
    response_style = models.CharField(
        max_length=20,
        choices=PwanimateResponseStyle.choices,
        default=PwanimateResponseStyle.BALANCED,
        db_index=True,
        help_text="Assistant response formatting style",
    )
    personal_instructions = models.TextField(
        max_length=500,
        blank=True,
        default="",
        help_text="User-authored stylistic guidance for Pwanimate (maximum 500 characters)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Pwanimate Preferences"
        verbose_name_plural = "Pwanimate Preferences"

    def clean(self):
        super().clean()
        if self.nickname:
            self.nickname = self.nickname.strip()
            if len(self.nickname) > 50:
                raise ValidationError({"nickname": "Nickname cannot exceed 50 characters."})
        else:
            self.nickname = ""

        if self.tone not in dict(PwanimateTone.choices):
            raise ValidationError({"tone": f"Invalid tone '{self.tone}'. Allowed choices: {PwanimateTone.values}."})

        if self.response_style not in dict(PwanimateResponseStyle.choices):
            raise ValidationError(
                {"response_style": f"Invalid response style '{self.response_style}'. Allowed choices: {PwanimateResponseStyle.values}."}
            )

        if self.personal_instructions:
            self.personal_instructions = self.personal_instructions.strip()
            if len(self.personal_instructions) > 500:
                raise ValidationError({"personal_instructions": "Personal instructions cannot exceed 500 characters."})
        else:
            self.personal_instructions = ""

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        user_ident = getattr(self.user, "username", str(self.user_id)) if hasattr(self, "user") else str(self.pk)
        return f"PwanimatePreferences({user_ident}, tone={self.tone}, style={self.response_style})"

