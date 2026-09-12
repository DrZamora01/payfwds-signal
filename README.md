# PayFwds Signal

**PayFwds Signal** is an evidence-to-action platform for payroll sales teams. It turns permitted public payroll/HCM review data into a market pressure map, provider dossier, and grounded AI call brief.

Instead of asking a salesperson to read hundreds of complaints, Signal answers four questions quickly:

1. Where is each payroll provider failing?
2. Which failure theme creates the strongest switching pressure?
3. Which customer segments report the pain most often?
4. What evidence-backed questions should a salesperson ask next?

> This starter build uses synthetic demo reviews. Before using the product for real competitive analysis, replace the sample CSV with a source whose terms explicitly allow automated access, an official API, or a permitted published dataset.

## Why it earns the call

- **Find the break:** rank providers and failure themes by complaint volume, severity, and recency.
- **See where it happens:** map each region's switching pressure and dominant failure theme.
- **Find the buyer:** isolate the company sizes and industries feeling the strongest operational pain.
- **Bring the proof:** preserve source context with every representative excerpt.
- **Ask, don't attack:** use Gemini 2.5 Flash to create warm discovery questions bounded by the selected evidence.
- **Leave with action:** export a rep-ready battlecard in under five minutes.

Signal deliberately separates deterministic measurement from generative activation. Gemini never calculates the score and never receives reviewer identities.

## Run on Linux Mint

### Easiest

Open a terminal inside this folder and run:

```bash
./run_linux_mint.sh
```

Then open:

```text
http://localhost:8501
```

### Manual setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run src/app.py
```

For live AI call briefs, add a [Gemini API key](https://ai.google.dev/gemini-api/docs/api-key):

```bash
export GEMINI_API_KEY="your-key"
streamlit run src/app.py
```

You can also enter a key in the in-app sidebar for a single demo session. Without a key, the complete product remains usable and shows a deterministic grounded brief preview.

If Linux Mint says the `venv` module is missing:

```bash
sudo apt install python3-venv
```

## Project structure

```text
payfwds_signal_v2/
├── .streamlit/config.toml       # Dark PayFwds visual theme
├── data/sample_reviews.csv      # Synthetic demo input
├── docs/                        # Product + technical handoff
├── src/app.py                   # Streamlit product UI
├── src/gemini_intelligence.py   # Structured, evidence-bound Gemini call briefs
├── src/pipeline.py              # Classification + scoring logic
├── src/regional_signals.py      # Geographic pressure aggregation
├── tests/                       # Pipeline and Gemini contract tests
├── requirements.txt
├── run_linux_mint.sh            # One-command Linux Mint launcher
└── README.md
```

## Architecture in plain English

**Input → classify → score → aggregate → ground → activate**

- **Input:** Each row is one review with provider, text, rating, date, source, company size, industry, and region.
- **Classify:** `pipeline.py` looks for explainable keywords and assigns a failure category. It also estimates severity from language and star rating.
- **Score:** The Switching Pressure score combines complaint volume, severity, and recency.
- **Aggregate:** The app groups results by provider, theme, company size, industry, and time.
- **Ground:** Signal packages only the current aggregate metrics and de-identified excerpts.
- **Activate:** Gemini returns a schema-validated call plan: opening question, discovery path, proof points, guardrail, and next step.

The classifier remains intentionally explainable for the demo. The AI generation layer cannot silently alter source metrics, and its prompt explicitly prohibits invented PayFwds capabilities, ROI, or competitor facts.

## Switching Pressure score

```text
score = 100 × (
    0.45 × normalized_volume
  + 0.35 × normalized_severity
  + 0.20 × recency
)
```

This is a **prioritization score**, not a prediction of churn or market share.

## Ground rules

- Use only sources whose terms permit automated access, or an available API/published dataset.
- Respect robots.txt and rate limits.
- Keep analysis aggregated.
- Do not deanonymize reviewers or collect contact information.
- Keep source attribution with representative quotes.
- Never turn competitor complaints into unsupported claims about PayFwds.

## Five-minute demo

1. **Overview:** show the top switching-pressure signal and provider heatmap.
2. **Provider Intel:** choose one competitor and show its strongest pain, exposed segment, and representative complaints.
3. **AI Call Brief:** select a call goal and show Gemini turning only the evidence in view into a human discovery plan.
4. **Trust & Method:** reveal the exact evidence payload, explainable formula, structured output contract, and privacy guardrails.

## Production roadmap

A production version should add:

- permitted source connectors / API ingestion
- deduplication and source normalization
- PostgreSQL or warehouse storage
- LLM/embedding classification with evaluation sets
- scheduled ingestion and trend snapshots
- authentication and team workspaces
- CRM integration and account-specific battlecards
- source-level citation links
- alerting when a competitor/theme crosses a pressure threshold
- monitoring, tests, and data-quality checks

See the document in `docs/PayFwds_Signal_Product_Technical_Handoff.docx` for the detailed handoff.
