"""
HAES HVAC - HAEL Extractor Base Class

Abstract base class for intent and entity extraction.
"""

from abc import ABC, abstractmethod

from src.hael.schema import HaelExtractionResult


class BaseExtractor(ABC):
    """
    Abstract base class for HAEL extractors.

    Extractors are responsible for:
    1. Classifying the intent from user input
    2. Extracting relevant entities
    3. Providing a confidence score
    """

    @abstractmethod
    def extract(self, text: str) -> HaelExtractionResult:
        """
        Extract intent and entities from text.

        Args:
            text: Raw user input text

        Returns:
            HaelExtractionResult with intent, entities, and confidence
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get the extractor name for logging/debugging."""
        pass

