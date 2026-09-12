from datetime import datetime, timedelta

from src.pipeline import Review, classify_category, classify_review, recency_weight, switching_pressure_score


def test_category_classification():
    category, confidence = classify_category("Support took days to respond to our payroll ticket")
    assert category == "support_response"
    assert 0.0 <= confidence <= 1.0


def test_severity_and_classification():
    review = Review(
        provider="Example",
        text="We received a filing penalty after an incorrect tax issue.",
        rating=1.0,
        review_date=datetime.utcnow(),
        source="Test",
    )
    classified = classify_review(review)
    assert classified.category == "tax_filing"
    assert classified.severity == 3


def test_recency_decreases_with_age():
    now = datetime.utcnow()
    recent = recency_weight(now - timedelta(days=10), now)
    old = recency_weight(now - timedelta(days=300), now)
    assert recent > old


def test_switching_pressure_range():
    score = switching_pressure_score(5, 2.4, 0.8, 10)
    assert 0 <= score <= 100
