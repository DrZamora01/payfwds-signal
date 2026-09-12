# PayFwds Signal

**PayFwds Signal** is a hackathon-ready competitive-intelligence dashboard that turns permitted public payroll/HCM review data into sales-ready insight.

Instead of asking a salesperson to read hundreds of complaints, Signal answers four questions quickly:

1. Where is each payroll provider failing?
2. Which failure theme creates the strongest switching pressure?
3. Which customer segments report the pain most often?
4. What evidence-backed questions should a salesperson ask next?

> This starter build uses synthetic demo reviews. Before using the product for real competitive analysis, replace the sample CSV with a source whose terms explicitly allow automated access, an official API, or a permitted published dataset.

## What is new in the polished V2

- Branded executive landing/header experience
- Executive signal cards for highest pressure, weakest provider signal, fastest-rising complaint, and most exposed segment
- Provider pressure ranking and provider × failure-theme heatmap
- Complaint movement trend chart
- Provider Intelligence drill-down
- Representative complaint cards with source context
- Sales Battlecard Builder with discovery questions and Markdown export
- Built-in methodology and ground-rules page
- CSV export for the current filtered view
- Linux Mint one-command launch helper
- Small automated test suite for the analytical pipeline

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
├── src/pipeline.py              # Classification + scoring logic
├── tests/test_pipeline.py       # Lightweight automated tests
├── requirements.txt
├── run_linux_mint.sh            # One-command Linux Mint launcher
└── README.md
```

## Architecture in plain English

**Input → classify → score → aggregate → activate**

- **Input:** Each row is one review with provider, text, rating, date, source, company size, industry, and region.
- **Classify:** `pipeline.py` looks for explainable keywords and assigns a failure category. It also estimates severity from language and star rating.
- **Score:** The Switching Pressure score combines complaint volume, severity, and recency.
- **Aggregate:** The app groups results by provider, theme, company size, industry, and time.
- **Activate:** The dashboard turns those patterns into charts, representative evidence, and pre-call battlecards.

The classifier is intentionally replaceable. A future team can swap the keyword classifier for an LLM or embedding model while keeping the same UI and scoring workflow.

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
3. **Battlecards:** generate questions a salesperson can use to validate whether a prospect experiences the same pain, then download the battlecard.
4. **Methodology:** show the explainable formula and source/privacy guardrails.

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
