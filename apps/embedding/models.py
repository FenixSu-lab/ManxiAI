"""Database models for embedding storage and retrieval."""

from django.db import models
from pgvector.django import VectorField

from apps.core.models import BaseModel


class ParagraphEmbedding(BaseModel):
    """Persist the latest embedding vector for a paragraph."""

    paragraph = models.OneToOneField(
        'document.Paragraph',
        on_delete=models.CASCADE,
        related_name='embedding',
    )
    provider = models.CharField(max_length=100)
    model = models.CharField(max_length=200)
    dimensions = models.PositiveIntegerField()
    vector = VectorField()
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'paragraph_embeddings'
        ordering = ['-updated_at']

    def __str__(self) -> str:
        """Return a compact debug string for admin and logs."""
        return f'{self.provider}:{self.model}:{self.paragraph_id}'
