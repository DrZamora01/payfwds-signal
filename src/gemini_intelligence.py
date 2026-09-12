from __future__ import annotations

import json
from typing import Any, Callable

from google import genai
from pydantic import BaseModel, Field

MODEL_NAME = "gemini-2.5-flash"


class SalesBrief(BaseModel):
    """Structured, evidence-bound output used by the sales copilot."""

    headline: str = Field(description="A concise, specific call-preparation headline.")
    executive_summary: str = Field(description="Two sentences summarizing the evidence and opportunity.")
    opening_question: str = Field(description="A warm, non-leading question to open the discovery call.")
    discovery_questions: list[str] = Field(
        min_length=3,
        max_length=5,
        description="Questions that validate the observed pain and quantify business impact.",
    )
    proof_points: list[str] = Field(
        min_length=2,
        max_length=4,
        description="Short, numerical facts taken only from the supplied evidence.",
    )
    watch_out: str = Field(description="One overclaim or unsupported inference the salesperson must avoid.")
    recommended_next_step: str = Field(description="A concrete, low-pressure next action for the call.")


def build_prompt(provider: str, objective: str, evidence: dict[str, Any]) -> str:
    """Create a constrained prompt that keeps Gemini grounded in aggregate evidence."""

    return f"""
You are the evidence analyst for PayFwds, helping a salesperson prepare for a first call
with a company that currently uses {provider}.

CALL OBJECTIVE
{objective}

AGGREGATED PUBLIC-REVIEW EVIDENCE
{json.dumps(evidence, indent=2, default=str)}

Create a concise call brief. Treat every pattern as a hypothesis to validate, never as a
universal fact about {provider}. Use only the evidence above for numbers and claims.
Do not invent PayFwds product capabilities, customer details, ROI, or competitor facts.
Questions should sound curious and human, not accusatory. The opening question should not
name a complaint category before the prospect has described their experience.
""".strip()


def generate_gemini_brief(
    provider: str,
    objective: str,
    evidence: dict[str, Any],
    api_key: str,
    client_factory: Callable[..., Any] = genai.Client,
) -> SalesBrief:
    """Generate and validate a structured brief with the Gemini Interactions API."""

    if not api_key.strip():
        raise ValueError("A Gemini API key is required.")

    client = client_factory(api_key=api_key.strip())
    interaction = client.interactions.create(
        model=MODEL_NAME,
        input=build_prompt(provider, objective, evidence),
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": SalesBrief.model_json_schema(),
        },
    )
    output_text = getattr(interaction, "output_text", "")
    if not output_text:
        raise RuntimeError("Gemini returned an empty response.")
    return SalesBrief.model_validate_json(output_text)


def build_evidence_payload(provider_reviews, provider_summary) -> dict[str, Any]:
    """Convert filtered dataframes into a compact, non-identifying evidence package."""

    ranked = provider_summary.sort_values("switching_pressure", ascending=False)
    reviews = provider_reviews.sort_values(["severity", "review_date"], ascending=False)

    themes = [
        {
            "theme": row.theme,
            "switching_pressure": round(float(row.switching_pressure), 1),
            "complaints": int(row.complaint_count),
            "average_severity": round(float(row.avg_severity), 2),
            "average_rating": round(float(row.avg_rating), 2),
        }
        for row in ranked.head(4).itertuples(index=False)
    ]
    segments = (
        reviews.groupby(["company_size", "industry"], as_index=False)
        .agg(complaints=("text", "count"), average_severity=("severity", "mean"))
        .sort_values(["complaints", "average_severity"], ascending=False)
        .head(3)
    )
    segment_rows = [
        {
            "company_size": str(row.company_size),
            "industry": str(row.industry),
            "complaints": int(row.complaints),
            "average_severity": round(float(row.average_severity), 2),
        }
        for row in segments.itertuples(index=False)
    ]
    excerpts = [
        {
            "excerpt": str(row.text)[:240],
            "theme": str(row.theme),
            "source": str(row.source),
            "review_date": row.review_date.date().isoformat(),
        }
        for row in reviews.head(3).itertuples(index=False)
    ]
    return {
        "provider": provider_reviews["provider"].iloc[0] if not provider_reviews.empty else "Unknown",
        "review_count_in_view": int(len(provider_reviews)),
        "themes": themes,
        "most_exposed_segments": segment_rows,
        "representative_excerpts": excerpts,
        "data_note": "Synthetic demonstration data; patterns are hypotheses, not market-wide claims.",
    }


def fallback_brief(provider: str, objective: str, evidence: dict[str, Any], questions: list[str]) -> SalesBrief:
    """Return a deterministic demo brief when no API key is available."""

    themes = evidence.get("themes", [])
    primary = themes[0] if themes else {"theme": "operational friction", "switching_pressure": 0, "complaints": 0}
    secondary = themes[1] if len(themes) > 1 else None
    proof_points = [
        f"{primary['theme']} leads the current view at {primary['switching_pressure']}/100 pressure.",
        f"{primary['complaints']} review(s) in the current view mention the leading theme.",
    ]
    if secondary:
        proof_points.append(
            f"{secondary['theme']} is the secondary signal at {secondary['switching_pressure']}/100."
        )

    return SalesBrief(
        headline=f"Validate {primary['theme'].lower()} risk before positioning",
        executive_summary=(
            f"Public-review patterns suggest {primary['theme'].lower()} is the strongest discovery angle for "
            f"{provider}. Use it as a hypothesis, quantify the prospect's actual impact, and position only "
            "capabilities PayFwds can demonstrate."
        ),
        opening_question="Before we talk solutions, where does payroll create the most avoidable work for your team today?",
        discovery_questions=questions[:5],
        proof_points=proof_points,
        watch_out=f"Do not present the sample as proof that every {provider} customer experiences this issue.",
        recommended_next_step=(
            f"If the prospect confirms the pain, agree on one workflow to compare against the stated goal: {objective}"
        ),
    )
