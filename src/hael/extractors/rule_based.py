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
        "career", "employment opportunity", "employment opportunities",
        "work for you", "apply for a position", "apply for", "application",
        "looking for work", "job", "positions open", "positions available",
        "join your team", "looking for employment", "technician positions",
        "need technicians", "do you need hvac", "need hvac technicians",
    ],
    Intent.ONBOARDING_INQUIRY: [
        "onboarding", "new hire", "first day", "orientation",
        "paperwork", "training schedule", "new employee",
        "employee setup", "report on my first day", "what do i need for my first day",
    ],
    Intent.PAYROLL_INQUIRY: [
        "payroll", "paycheck", "pay stub", "my commission",
        "direct deposit", "w-2", "w2", "tax form", "get paid", "my pay",
        "payday", "when do i get paid", "pay stubs", "commission calculated",
        "paycheck is wrong",
    ],

    # REVENUE-BRAIN intents (put before SERVICE_REQUEST so they win ties)
    Intent.QUOTE_REQUEST: [
        "need a quote", "want a quote", "get a quote", "quote for",
        "get an estimate", "give me an estimate", "estimate for replacing",
        "quote", "estimate", "price for", "how much for",
        "how much would", "how much does", "how much to",
        "cost to", "cost of", "what's the cost", "what's the price",
        "want to know the cost", "know the cost",
        "new system", "replacement system", "new installation",
        "install", "installation", "replacement",
        "pricing", "bid", "proposal", "free estimate",
        "price range", "interested in getting a quote", "pricing information",
        "ballpark estimate", "what would it run", "quote request",
    ],

    # CORE-BRAIN intents (before SERVICE_REQUEST)
    Intent.BILLING_INQUIRY: [
        "bill", "billing", "charge", "charged", "statement",
        "amount due", "owe", "balance", "overcharged", "double charged",
        "billing question", "explain the charge", "explain these charges",
        "why was i charged", "error on my bill", "mistake on my invoice",
        "verify a charge", "review my billing", "outstanding balance",
        "total amount due", "account balance", "why is my bill",
        "question about my account", "service fee",
    ],
    Intent.PAYMENT_TERMS_INQUIRY: [
        "payment terms", "payment options", "financing",
        "when is payment", "payment due", "how to pay", "how can i pay",
        "accept credit cards", "credit cards", "credit card",
        "installments", "pay in installments",
        "payment plans", "payment plan", "offer payment",
        "financing options", "what's your payment policy",
        "how long do i have to pay",
    ],
    Intent.INVOICE_REQUEST: [
        "invoice", "receipt", "send invoice", "email invoice",
        "copy of invoice", "invoice copy", "resend my invoice",
        "duplicate invoice", "itemized invoice", "need documentation",
        "need a receipt", "for taxes", "for my records",
    ],
    Intent.INVENTORY_INQUIRY: [
        "parts", "part available", "in stock", "inventory",
        "have the part", "equipment available", "parts availability",
        "do you have this", "do you have the", "check if you have",
        "do you have trane", "do you have carrier", "do you have lennox",
        "is this available", "do you carry", "what brands do you stock",
        "do you stock", "is this model", "check inventory",
        "filter available", "is the filter", "filters",
    ],
    Intent.PURCHASE_REQUEST: [
        "purchase a", "buy a", "order a new", "order a",
        "want to order", "want to buy", "want to purchase",
        "need to order", "need to purchase",
        "order parts", "order equipment", "purchase", "buy",
        "buy parts", "buy equipment", "place an order",
        "order replacement", "order supplies", "can i buy",
        "purchase order", "get shipped", "shipped",
        "get a new filter", "new filter shipped",
    ],

    # OPS-BRAIN intents
    Intent.CANCEL_APPOINTMENT: [
        "cancel my appointment", "cancel my service", "cancel my booking",
        "cancel the appointment", "cancel the service", "cancel appointment", 
        "cancel service", "cancel the technician", "want to cancel",
        "don't need service anymore", "don't need the service", 
        "no longer need service", "no longer need", "remove my appointment",
        "cancel tomorrow", "cancel scheduled", "i want to cancel",
        "cancel my scheduled", "cancel scheduled visit",
    ],
    Intent.RESCHEDULE_APPOINTMENT: [
        "reschedule my appointment", "reschedule my service", "reschedule",
        "change my appointment", "change the appointment", "change appointment",
        "move my appointment", "move appointment", "different time",
        "different day", "change the time", "can't make my appointment",
        "push back my appointment", "change my booking",
    ],
    Intent.STATUS_UPDATE_REQUEST: [
        "status of my", "where is the technician", "where's the tech",
        "eta", "technician coming", "update on my", "what's the status",
        "track my", "when is the tech", "when will the tech",
        "how long until", "is the technician on the way", "on the way",
        "status update", "is my appointment still on", "when can i expect",
        "someone arrives", "tech arrive",
    ],
    Intent.SCHEDULE_APPOINTMENT: [
        "schedule an appointment", "schedule appointment", "schedule a technician",
        "book an appointment", "book appointment", "book a service",
        "set up an appointment", "set up appointment", "make an appointment",
        "set up a time", "arrange a service", "arrange service", "available time",
        "next available", "earliest available", "earliest", "come by",
        "get on the schedule", "times are available", "schedule a tune-up",
        "schedule annual", "schedule maintenance", "book maintenance",
        "come out tomorrow", "come tomorrow", "come out next",
    ],
    
    # SERVICE_REQUEST last (most generic - should lose ties to specific intents)
    Intent.SERVICE_REQUEST: [
        "need service", "need repair", "not working", "broken", "fix",
        "service call", "send technician", "tech out", "come out",
        "hvac problem", "ac problem", "heating problem", "furnace problem",
        "unit not working", "system down", "system is down", "need help with",
        "my ac is", "my ac", "my hvac", "my furnace", "my heater",
        "service request", "heater", "furnace", "a/c", "air conditioner",
        "air conditioning unit", "air conditioning",
        "not heating", "not cooling", "won't heat", "won't cool",
        "requesting service", "request service",
        "heat pump", "heating system", "cooling system", "central air",
        "stopped working", "stopped", "broke down",
        "making noise", "making a noise", "strange noise", "popping sounds",
        "won't turn on", "won't start", "isn't working", "not turning on",
        "not coming on", "heat not", "fan not", "fan is not",
        "blowing cold", "blowing hot", "blowing warm", "not blowing",
        "compressor", "thermostat is", "thermostat not", "ductwork",
        "air handler", "condenser", "evaporator", "coil", "short cycling",
        "leaking water", "frozen", "technician needed", "need someone to look",
        "system keeps", "smells weird", "loud noise", "pilot light",
        "mini split", "window unit", "central heating",
        "need ac service", "heater service", "ac service",
        "high electric bills", "vents not blowing",
        "malfunctioning", "needs freon", "outdoor unit",
        # Emergency indicators that imply service needed
        "gas leak", "smell gas", "smell burning", "carbon monoxide", "co detector",
        "burning smell", "smoke", "sparks", "fire", "flooding", "water damage",
    ],
}

# Emergency detection keywords (always trigger emergency urgency - safety hazards)
EMERGENCY_KEYWORDS = [
    "gas leak", "smell gas", "i smell gas", "carbon monoxide", "co detector",
    "burning smell", "smell burning", "i smell burning",
    "electrical smell", "smoke", "fire smell",
    "sparks", "sparking", "fire", "flames", "caught fire",
    "flooding", "water damage", "water leak", "leaking everywhere",
    "server room", "data center", "medical equipment",
    "refrigeration", "freezer", "walk-in",
]

# High urgency keywords (if not emergency)
HIGH_URGENCY_KEYWORDS = [
    "today", "right now", "as soon as possible", "right away",
    "very hot", "very cold", "uncomfortable",
    "elderly", "senior", "senior citizen", "baby", "infant", "newborn", "children",
    "health issue", "sick", "urgent", "asap", "immediately", "emergency",
    "no heat", "no heating", "no ac", "no cooling", "no air",
]

# =============================================================================
# Entity Extraction Patterns
# =============================================================================

PHONE_PATTERN = re.compile(
    r"(?:\+?1[-.\s/]?)?\(?([0-9]{3})\)?[-.\s/]?([0-9]{3})[-.\s/]?([0-9]{4})"
)

EMAIL_PATTERN = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
)

ZIP_CODE_PATTERN = re.compile(r"\b(\d{5})(?:-\d{4})?\b")

SQUARE_FOOTAGE_PATTERN = re.compile(
    r"(\d[\d,]{0,4})\s*(?:sq\.?\s*ft\.?|square\s*(?:feet?|foot)|sqft|sf\b)", re.IGNORECASE
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
            # Remove commas from number before converting
            sqft_str = sqft_match.group(1).replace(",", "")
            entities.square_footage = int(sqft_str)

        # System age
        age_match = SYSTEM_AGE_PATTERN.search(text_lower)
        if age_match:
            entities.system_age_years = int(age_match.group(1))

        # Temperature mentioned
        temp_match = TEMPERATURE_PATTERN.search(text)
        if temp_match:
            entities.temperature_mentioned = int(temp_match.group(1))

        # Property type inference
        if any(kw in text_lower for kw in ["commercial", "business", "office", "warehouse", "retail", "restaurant", "store"]):
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
        # Check for always-emergency keywords (safety hazards)
        for keyword in EMERGENCY_KEYWORDS:
            if keyword in text_lower:
                return UrgencyLevel.EMERGENCY

        # Temperature-based emergency detection
        if entities.temperature_mentioned:
            temp = entities.temperature_mentioned
            # No heat with cold temperature is emergency
            no_heat_phrases = ["no heat", "no heating", "heat not working", "heater not working"]
            if any(phrase in text_lower for phrase in no_heat_phrases) and temp < 55:
                return UrgencyLevel.EMERGENCY
            # No AC with hot temperature is emergency
            no_ac_phrases = ["no ac", "no cooling", "ac not working", "ac broken", 
                           "air conditioner not working", "air conditioner broken",
                           "ac won't", "no air"]
            if any(phrase in text_lower for phrase in no_ac_phrases) and temp > 85:
                return UrgencyLevel.EMERGENCY

        # High urgency keywords
        for keyword in HIGH_URGENCY_KEYWORDS:
            if keyword in text_lower:
                return UrgencyLevel.HIGH

        # Default based on context
        if any(kw in text_lower for kw in ["repair", "fix", "service", "tune-up", "tune up", "maintenance"]):
            return UrgencyLevel.MEDIUM

        return UrgencyLevel.LOW

