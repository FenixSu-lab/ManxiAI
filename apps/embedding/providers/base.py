"""Base classes for embedding providers."""

from abc import ABC, abstractmethod


class BaseEmbeddingProvider(ABC):
    """Define the interface used by embedding services."""

    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        """Embed a single text input and return its vector."""

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple text inputs and return vectors in input order."""

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the stable provider identifier used in persistence."""

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the configured embedding model name."""
