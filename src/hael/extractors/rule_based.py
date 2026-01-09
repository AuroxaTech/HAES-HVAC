"""
HAES HVAC - Rule-Based HAEL Extractor

Deterministic extraction using keyword matching and regex patterns.
This is the default extractor for Module 3, providing predictable
and testable behavior.
"""

import re
from typing import Any

from src.hael.extractors.base import BaseExtractor
from src.hael.schema import Entity, HaelExtractionResult, Intent, UrgencyLevel


# =============================================================================
# Intent Keywords (deterministic mapping)
# =============================================================================

INTENT_KEYWORDS: dict[Intent, list[str]] = {
    # PEOPLE-BRAIN intents (check first - more specific)
    Intent.HIRING_INQUIRY: [
        "are you hiring", "hiring", "job opening", "position available",
        "career", "employment opportunity", "work for you",
        "apply for", "application", "looking for work", "job",
    ],
    Intent.ONBOARDING_INQUIRY: [
        "onboarding", "new hire", "first day", "orientation",
        "paperwork", "training schedule",
    ],
    Intent.PAYROLL_INQUIRY: [
        "payroll", "paycheck", "pay stub", "my commission",
        "direct deposit", "w-2", "tax form", "get paid", "my pay",
    ],

    # OPS-BRAIN intents
    Intent.CANCEL_APPOINTMENT: [
        "cancel my", "cancel the", "cancel appointment", "cancel service",
        "don't need service", "no longer need", "want to cancel",
    ],
    Intent.RESCHEDULE_APPOINTMENT: [
        "reschedule", "change appointment", "move appointment",
        "different time", "different day", "change the time",
    ],
    Intent.STATUS_UPDATE_REQUEST: [
        "status of my", "where is the technician", "eta",
        "technician coming", "update on my", "what's the status",
        "track my", "when is the tech",
    ],
    Intent.SCHEDULE_APPOINTMENT: [
        "schedule", "book", "set up appointment", "arrange",
        "available time", "next available", "earliest", "come by",
    ],
    Intent.SERVICE_REQUEST: [
        "need service", "need repair", "not working", "broken", "fix",
        "service call", "send technician", "tech out", "come out",
        "hvac problem", "ac problem", "heating problem", "furnace problem",
        "unit not working", "system down", "need help with",
        "my ac", "my hvac", "my furnace", "my heater",
        "service request", "heater", "furnace", "ac ", "a/c", "air conditioner",
        "not heating", "not cooling", "won't heat", "won't cool",
        "requesting service", "request service", "schedule service",
    ],

    # REVENUE-BRAIN intents
    Intent.QUOTE_REQUEST: [
        "quote", "estimate", "price for", "how much", "cost",
        "new system", "replacement", "install", "installation",
        "pricing", "bid", "proposal",
    ],

    # CORE-BRAIN intents
    Intent.BILLING_INQUIRY: [
        "bill", "billing", "charge", "charged", "statement",
        "amount due", "owe", "balance",
    ],
    Intent.PAYMENT_TERMS_INQUIRY: [
        "payment terms", "payment options", "financing",
        "when is payment", "payment due", "how to pay",
    ],
    Intent.INVOICE_REQUEST: [
        "invoice", "receipt", "send invoice", "email invoice",
        "copy of invoice", "invoice copy",
    ],
    Intent.INVENTORY_INQUIRY: [
        "parts", "part available", "in stock", "inventory",
        "have the part", "equipment available",
    ],
    Intent.PURCHASE_REQUEST: [
        "order parts", "order equipment", "purchase", "buy",
        "need to order",
    ],
}

# Emergency detection keywords (always trigger emergency urgency)
EMERGENCY_KEYWORDS = [
    "gas leak", "smell gas", "carbon monoxide", "co detector",
    "burning smell", "electrical smell", "smoke",
    "sparks", "sparking", "fire", "flames",
    "flooding", "water damage", "water leak",
    "no heat", "no heating", "furnace won't", "heater won't",
    "no ac", "no air", "no cooling", "ac won't", "air conditioner won't",
    "server room", "data center", "medical", "medication",
    "refrigeration", "freezer", "walk-in",
    "emergency", "urgent", "immediately", "asap",
]

# High urgency keywords (if not emergency)
HIGH_URGENCY_KEYWORDS = [
    "today", "right now", "as soon as possible",
    "very hot", "very cold", "uncomfortable",
    "elderly", "baby", "infant", "children",
    "health issue", "sick",
]

# =============================================================================
# Entity Extraction Patterns
# =============================================================================

PHONE_PATTERN = re.compile(
    r"(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})"
)

EMAIL_PATTERN = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
)

ZIP_CODE_PATTERN = re.compile(r"\b(\d{5})(?:-\d{4})?\b")

SQUARE_FOOTAGE_PATTERN = re.compile(
    r"(\d{1,5})\s*(?:sq\.?\s*ft\.?|square\s*feet|sqft)", re.IGNORECASE
)

SYSTEM_AGE_PATTERN = re.compile(
    r"(\d{1,2})\s*(?:year|yr)s?\s*old", re.IGNORECASE
)

TEMPERATURE_PATTERN = re.compile(
    r"(\d{2,3})\s*(?:degrees?|°|deg)", re.IGNORECASE
)


class RuleBasedExtractor(BaseExtractor):
    """
    Deterministic rule-based extractor.

    Uses keyword matching for intent classification and
    regex patterns for entity extraction.
    """

    def get_name(self) -> str:
        return "rule_based"

    def extract(self, text: str) -> HaelExtractionResult:
        """
        Extract intent and entities using rules.

        Args:
            text: Raw user input

        Returns:
            Extraction result with intent, entities, confidence
        """
        text_lower = text.lower()

        # Extract intent
        intent, intent_confidence, signals = self._extract_intent(text_lower)

        # Extract entities
        entities = self._extract_entities(text, text_lower)

        # Adjust urgency based on keywords
        entities.urgency_level = self._classify_urgency(text_lower, entities)

        return HaelExtractionResult(
            intent=intent,
            entities=entities,
            confidence=intent_confidence,
            raw_signals=signals,
        )

    def _extract_intent(self, text_lower: str) -> tuple[Intent, float, dict[str, Any]]:
        """
        Classify intent from text.

        Returns:
            Tuple of (intent, confidence, signals)
        """
        signals: dict[str, Any] = {"matched_keywords": [], "intent_scores": {}}

        # Score each intent based on keyword matches
        # Longer keyword matches get bonus points for specificity
        intent_scores: dict[Intent, float] = {}
        for intent, keywords in INTENT_KEYWORDS.items():
            score = 0.0
            matched = []
            for keyword in keywords:
                if keyword in text_lower:
                    # Bonus for longer/more specific keywords
                    specificity_bonus = len(keyword.split()) * 0.5
                    score += 1.0 + specificity_bonus
                    matched.append(keyword)
            if matched:
                intent_scores[intent] = score
                signals["matched_keywords"].extend(matched)

        signals["intent_scores"] = {k.value: v for k, v in intent_scores.items()}

        # Select highest scoring intent
        if intent_scores:
            best_intent = max(intent_scores, key=lambda k: intent_scores[k])
            max_score = intent_scores[best_intent]

            # Calculate confidence based on score and competition
            total_score = sum(intent_scores.values())
            if total_score > 0:
                confidence = min(0.9, 0.5 + (max_score / total_score) * 0.4)
            else:
                confidence = 0.5

            return best_intent, confidence, signals

        # No intent matched
        return Intent.UNKNOWN, 0.3, signals

    def _extract_entities(self, text: str, text_lower: str) -> Entity:
        """Extract entities using regex patterns."""
        entities = Entity()

        # Phone number
        phone_match = PHONE_PATTERN.search(text)
        if phone_match:
            entities.phone = f"{phone_match.group(1)}-{phone_match.group(2)}-{phone_match.group(3)}"

        # Email
        email_match = EMAIL_PATTERN.search(text_lower)
        if email_match:
            entities.email = email_match.group(0)

        # ZIP code
        zip_match = ZIP_CODE_PATTERN.search(text)
        if zip_match:
            entities.zip_code = zip_match.group(1)

        # Square footage
        sqft_match = SQUARE_FOOTAGE_PATTERN.search(text)
        if sqft_match:
            entities.square_footage = int(sqft_match.group(1))

        # System age
        age_match = SYSTEM_AGE_PATTERN.search(text_lower)
        if age_match:
            entities.system_age_years = int(age_match.group(1))

        # Temperature mentioned
        temp_match = TEMPERATURE_PATTERN.search(text)
        if temp_match:
            entities.temperature_mentioned = int(temp_match.group(1))

        # Property type inference
        if any(kw in text_lower for kw in ["commercial", "business", "office", "warehouse", "retail"]):
            entities.property_type = "commercial"
        elif any(kw in text_lower for kw in ["home", "house", "residential", "apartment", "condo"]):
            entities.property_type = "residential"

        # Problem description - use the full text as description if it looks like a service issue
        if any(kw in text_lower for kw in ["not working", "broken", "problem", "issue", "won't"]):
            entities.problem_description = text[:500]  # Limit length

        return entities

    def _classify_urgency(self, text_lower: str, entities: Entity) -> UrgencyLevel:
        """
        Classify urgency level.

        Emergency conditions (from RDD):
        - No heat + outside temp below 55°F
        - No AC + outside temp above 85°F
        - Gas leak / carbon monoxide
        - Electrical burning smell / main breaker tripping
        - Refrigerant leak
        - Flooding/water damage
        - Medical/refrigeration/server room failures
        """
        # Check for always-emergency keywords
        for keyword in EMERGENCY_KEYWORDS:
            if keyword in text_lower:
                return UrgencyLevel.EMERGENCY

        # Temperature-based emergency detection
        if entities.temperature_mentioned:
            temp = entities.temperature_mentioned
            if "no heat" in text_lower and temp < 55:
                return UrgencyLevel.EMERGENCY
            if ("no ac" in text_lower or "no cooling" in text_lower) and temp > 85:
                return UrgencyLevel.EMERGENCY

        # High urgency keywords
        for keyword in HIGH_URGENCY_KEYWORDS:
            if keyword in text_lower:
                return UrgencyLevel.HIGH

        # Default based on context
        if "repair" in text_lower or "fix" in text_lower:
            return UrgencyLevel.MEDIUM

        return UrgencyLevel.UNKNOWN

