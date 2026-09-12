import json
from types import SimpleNamespace

import pandas as pd
import pytest

from src.gemini_intelligence import (
    MODEL_NAME,
    build_evidence_payload,
    build_prompt,
    generate_gemini_brief,
)


def test_prompt_is_grounded_and_contains_guardrails():
    prompt = build_prompt(
        "ExampleCo",
        "Earn a workflow review.",
        {"themes": [{"theme": "Support Response", "complaints": 4}]},
    )

    assert "ExampleCo" in prompt
    assert "Support Response" in prompt
    assert "Do not invent PayFwds product capabilities" in prompt
    assert "hypothesis to validate" in prompt


def test_generate_brief_uses_structured_gemini_output():
    output = {
        "headline": "Validate support risk",
        "executive_summary": "Support is the leading signal. Confirm the prospect's actual experience.",
        "opening_question": "Where does payroll create avoidable work today?",
        "discovery_questions": ["Question one?", "Question two?", "Question three?"],
        "proof_points": ["Four complaints mention support.", "Pressure is 82/100."],
        "watch_out": "Do not generalize the sample.",
        "recommended_next_step": "Compare one confirmed workflow.",
    }
    captured = {}

    class FakeInteractions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(output_text=json.dumps(output))

    def fake_client_factory(**kwargs):
        captured["client_kwargs"] = kwargs
        return SimpleNamespace(interactions=FakeInteractions())

    brief = generate_gemini_brief(
        "ExampleCo",
        "Earn a workflow review.",
        {"themes": []},
        "secret-key",
        client_factory=fake_client_factory,
    )

    assert brief.headline == "Validate support risk"
    assert captured["model"] == MODEL_NAME
    assert captured["response_format"]["mime_type"] == "application/json"
    assert captured["client_kwargs"] == {"api_key": "secret-key"}


def test_generate_brief_rejects_missing_key():
    with pytest.raises(ValueError, match="API key"):
        generate_gemini_brief("ExampleCo", "Objective", {}, " ")


def test_evidence_payload_excludes_identity_fields():
    reviews = pd.DataFrame(
        [
            {
                "provider": "ExampleCo",
                "text": "Support took days to resolve a payroll issue.",
                "theme": "Support Response",
                "source": "Permitted dataset",
                "review_date": pd.Timestamp("2026-08-01"),
                "severity": 2,
                "company_size": "51-200",
                "industry": "Retail",
                "region": "Midwest",
            }
        ]
    )
    summary = pd.DataFrame(
        [
            {
                "provider": "ExampleCo",
                "theme": "Support Response",
                "switching_pressure": 78.4,
                "complaint_count": 1,
                "avg_severity": 2.0,
                "avg_rating": 2.0,
            }
        ]
    )

    payload = build_evidence_payload(reviews, summary)

    assert payload["provider"] == "ExampleCo"
    assert payload["themes"][0]["switching_pressure"] == 78.4
    assert set(payload["representative_excerpts"][0]) == {
        "excerpt",
        "theme",
        "source",
        "review_date",
    }
