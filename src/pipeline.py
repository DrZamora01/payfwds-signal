from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable
import math
import re

CATEGORIES = {
    "implementation": ["implementation", "onboarding", "setup", "migration", "go live", "launch", "training"],
    "tax_filing": ["tax", "filing", "w-2", "w2", "1099", "irs", "withholding", "quarterly"],
    "support_response": ["support", "ticket", "response", "hold", "callback", "customer service", "agent"],
    "surprise_billing": ["billing", "fee", "charged", "price", "cost", "invoice", "renewal", "contract"],
    "reporting": ["report", "analytics", "export", "dashboard", "custom report", "data"],
    "integrations": ["integration", "sync", "api", "connector", "quickbooks", "xero", "time clock"],
}

SEVERITY_WORDS = {
    3: ["penalty", "fine", "missed payroll", "failed payroll", "locked out", "incorrect tax", "legal"],
    2: ["weeks", "days", "unresolved", "broken", "incorrect", "duplicate charge", "frustrating"],
    1: ["slow", "confusing", "annoying", "difficult", "limited"],
}


@dataclass
class Review:
    provider: str
    text: str
    rating: float
    review_date: datetime
    source: str
    company_size: str | None = None
    industry: str | None = None
    region: str | None = None


@dataclass
class ClassifiedReview:
    review: Review
    category: str
    severity: int
    confidence: float


def classify_category(text: str) -> tuple[str, float]:
    """Simple, explainable keyword classifier used as a safe local fallback.

    A production version can swap this for a hosted LLM or embedding classifier,
    while keeping the same function contract.
    """
    clean = text.lower()
    scores: dict[str, int] = {}
    for category, keywords in CATEGORIES.items():
        scores[category] = sum(1 for kw in keywords if kw in clean)

    best = max(scores, key=scores.get)
    top = scores[best]
    if top == 0:
        return "other", 0.35

    total = sum(scores.values()) or 1
    confidence = min(0.97, 0.55 + (top / total) * 0.4)
    return best, confidence


def estimate_severity(text: str, rating: float) -> int:
    clean = text.lower()
    severity = 1
    for level, words in SEVERITY_WORDS.items():
        if any(word in clean for word in words):
            severity = max(severity, level)
    if rating <= 1.5:
        severity = max(severity, 3)
    elif rating <= 2.5:
        severity = max(severity, 2)
    return severity


def classify_review(review: Review) -> ClassifiedReview:
    category, confidence = classify_category(review.text)
    return ClassifiedReview(
        review=review,
        category=category,
        severity=estimate_severity(review.text, review.rating),
        confidence=confidence,
    )


def recency_weight(review_date: datetime, as_of: datetime | None = None) -> float:
    """Exponential decay with a 180-day half-life."""
    as_of = as_of or datetime.utcnow()
    days = max((as_of - review_date).days, 0)
    return math.exp(-math.log(2) * days / 180)


def switching_pressure_score(
    complaint_count: int,
    avg_severity: float,
    recency: float,
    max_count: int,
) -> float:
    """0-100 score combining volume, severity and recency.

    Volume is log-normalized so one giant provider does not dominate simply
    because it has more customers.
    """
    if complaint_count <= 0 or max_count <= 0:
        return 0.0
    volume = math.log1p(complaint_count) / math.log1p(max_count)
    severity = min(max((avg_severity - 1) / 2, 0), 1)
    score = (0.45 * volume) + (0.35 * severity) + (0.20 * min(max(recency, 0), 1))
    return round(score * 100, 1)


def safe_quote(text: str, max_chars: int = 220) -> str:
    """Return a short representative excerpt while avoiding person-level metadata."""
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 1].rstrip() + "…"


def classify_many(reviews: Iterable[Review]) -> list[ClassifiedReview]:
    return [classify_review(r) for r in reviews]
