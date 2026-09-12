from __future__ import annotations

import os
from datetime import datetime, timedelta
from html import escape
from pathlib import Path
from textwrap import dedent

import altair as alt
import pandas as pd
import pydeck as pdk
import streamlit as st

from gemini_intelligence import (
    MODEL_NAME,
    build_evidence_payload,
    fallback_brief,
    generate_gemini_brief,
)
from pipeline import Review, classify_many, recency_weight, safe_quote, switching_pressure_score
from regional_signals import regional_hotspots

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "sample_reviews.csv"

BRAND_PURPLE = "#3B2A70"
BRAND_LIME = "#B7E33D"
BG = "#0B0D12"
PANEL = "#121620"
PANEL_2 = "#171C27"
TEXT = "#F6F7FB"
MUTED = "#A8B0C0"
BORDER = "#283142"
DANGER = "#FF6B6B"

st.set_page_config(
    page_title="Signal | PayFwds",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    f"""
    <style>
      :root {{ color-scheme: dark; }}
      .stApp {{ background: {BG}; color: {TEXT}; }}
      [data-testid="stSidebar"] {{ background: #10131B; border-right: 1px solid {BORDER}; }}
      [data-testid="stHeader"] {{ background: rgba(11,13,18,.72); }}
      .block-container {{ padding-top: 1.15rem; padding-bottom: 3rem; max-width: 1550px; }}
      h1, h2, h3 {{ letter-spacing: -.025em; }}
      .signal-hero {{
        border: 1px solid {BORDER};
        border-radius: 24px;
        padding: 2rem 2.15rem;
        background:
          radial-gradient(circle at 92% 15%, rgba(183,227,61,.14), transparent 24%),
          linear-gradient(135deg, rgba(59,42,112,.52), rgba(18,22,32,.92) 52%, rgba(11,13,18,1));
        box-shadow: 0 18px 55px rgba(0,0,0,.28);
        margin-bottom: 1rem;
      }}
      .signal-kicker {{ letter-spacing: .18em; font-size: .72rem; font-weight: 800; color: {BRAND_LIME}; }}
      .signal-title {{ margin: .35rem 0 .4rem; font-size: clamp(2.4rem, 5vw, 4.5rem); line-height: .95; font-weight: 850; }}
      .signal-sub {{ color: #D7DCE7; max-width: 900px; font-size: 1.05rem; line-height: 1.55; }}
      .signal-chip {{
        display:inline-block; margin:.75rem .45rem 0 0; padding:.38rem .62rem;
        border:1px solid #354157; border-radius:999px; color:#DCE2EF; font-size:.78rem; background:rgba(14,18,26,.55);
      }}
      .live-badge {{
        display:inline-flex; align-items:center; gap:.42rem; margin-top:.8rem; padding:.45rem .7rem;
        border:1px solid rgba(183,227,61,.38); border-radius:999px; color:{BRAND_LIME};
        background:rgba(183,227,61,.08); font-size:.76rem; font-weight:800; letter-spacing:.04em;
      }}
      .live-dot {{ width:7px; height:7px; border-radius:50%; background:{BRAND_LIME}; box-shadow:0 0 12px {BRAND_LIME}; }}
      .metric-card {{
        min-height: 142px; border:1px solid {BORDER}; border-radius:18px; padding:1rem 1.05rem;
        background: linear-gradient(180deg, {PANEL_2}, {PANEL});
      }}
      .metric-label {{ color:{MUTED}; font-size:.76rem; font-weight:700; letter-spacing:.06em; text-transform:uppercase; }}
      .metric-value {{ color:{TEXT}; font-size:1.55rem; font-weight:800; margin-top:.45rem; line-height:1.15; }}
      .metric-detail {{ color:{MUTED}; font-size:.86rem; margin-top:.45rem; line-height:1.35; }}
      .accent {{ color:{BRAND_LIME}; }}
      .section-card {{ border:1px solid {BORDER}; border-radius:18px; background:{PANEL}; padding:1rem 1.1rem; }}
      .quote-card {{
        border-left:3px solid {BRAND_LIME}; border-top:1px solid {BORDER}; border-right:1px solid {BORDER}; border-bottom:1px solid {BORDER};
        border-radius:12px; padding:.9rem 1rem; margin:.55rem 0; background:#111620;
      }}
      .quote-meta {{ color:{MUTED}; font-size:.75rem; margin-bottom:.32rem; }}
      .quote-text {{ color:#EEF1F7; font-size:.95rem; line-height:1.45; }}
      .demo-step {{ border:1px solid {BORDER}; border-radius:14px; padding:.85rem 1rem; background:#10151E; min-height:110px; }}
      .demo-num {{ color:{BRAND_LIME}; font-weight:900; font-size:.72rem; letter-spacing:.12em; }}
      .demo-title {{ font-weight:800; margin:.28rem 0; }}
      .demo-copy {{ color:{MUTED}; font-size:.85rem; line-height:1.35; }}
      .battle-title {{ color:{BRAND_LIME}; font-size:.8rem; font-weight:800; text-transform:uppercase; letter-spacing:.08em; }}
      .brief-hero {{
        border:1px solid rgba(183,227,61,.3); border-radius:18px; padding:1.25rem 1.35rem;
        background:linear-gradient(135deg,rgba(59,42,112,.42),rgba(18,22,32,.96));
        margin:.8rem 0 1rem;
      }}
      .brief-kicker {{ color:{BRAND_LIME}; font-size:.7rem; letter-spacing:.14em; font-weight:850; }}
      .brief-headline {{ color:{TEXT}; font-size:1.6rem; line-height:1.15; font-weight:850; margin:.35rem 0; }}
      .brief-copy {{ color:#D7DCE7; line-height:1.55; }}
      .proof-row {{ border-bottom:1px solid {BORDER}; padding:.68rem 0; color:#E9ECF3; }}
      .proof-row:last-child {{ border-bottom:0; }}
      .eyebrow {{ color:{MUTED}; font-size:.72rem; font-weight:800; letter-spacing:.1em; text-transform:uppercase; }}
      .small-muted {{ color:{MUTED}; font-size:.82rem; }}
      div[data-testid="stDataFrame"] {{ border:1px solid {BORDER}; border-radius:14px; overflow:hidden; }}
      div[data-testid="stMetric"] {{ border:1px solid {BORDER}; padding:.75rem; border-radius:14px; background:{PANEL}; }}
      .stTabs [data-baseweb="tab-list"] {{ gap:.35rem; }}
      .stTabs [data-baseweb="tab"] {{ background:#121620; border-radius:10px; padding:.45rem .8rem; }}
      .stTabs [aria-selected="true"] {{ color:{BRAND_LIME} !important; border-bottom-color:{BRAND_LIME} !important; }}
      .footer-note {{ color:#7F899B; font-size:.76rem; border-top:1px solid {BORDER}; padding-top:1rem; margin-top:1.2rem; }}
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# Data + scoring helpers
# -----------------------------

def theme_label(value: str) -> str:
    return value.replace("_", " ").title()


def configured_gemini_key() -> str:
    if os.getenv("GEMINI_API_KEY"):
        return os.environ["GEMINI_API_KEY"]
    try:
        return str(st.secrets.get("GEMINI_API_KEY", ""))
    except Exception:
        return ""


@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, parse_dates=["review_date"])
    reviews = [
        Review(
            provider=row.provider,
            text=row.text,
            rating=float(row.rating),
            review_date=row.review_date.to_pydatetime(),
            source=row.source,
            company_size=row.company_size,
            industry=row.industry,
            region=row.region,
        )
        for row in df.itertuples(index=False)
    ]

    rows: list[dict] = []
    as_of = max(r.review_date for r in reviews) if reviews else datetime.utcnow()
    for item in classify_many(reviews):
        r = item.review
        rows.append(
            {
                "provider": r.provider,
                "text": r.text,
                "rating": r.rating,
                "review_date": r.review_date,
                "source": r.source,
                "company_size": r.company_size,
                "industry": r.industry,
                "region": r.region,
                "category": item.category,
                "theme": theme_label(item.category),
                "severity": item.severity,
                "confidence": item.confidence,
                "recency": recency_weight(r.review_date, as_of),
            }
        )
    out = pd.DataFrame(rows)
    if not out.empty:
        out["month"] = out["review_date"].dt.to_period("M").dt.to_timestamp()
        out["quarter"] = out["review_date"].dt.to_period("Q").astype(str)
    return out


def pressure_summary(frame: pd.DataFrame) -> pd.DataFrame:
    summary = (
        frame.groupby(["provider", "category", "theme"], as_index=False)
        .agg(
            complaint_count=("text", "count"),
            avg_severity=("severity", "mean"),
            avg_recency=("recency", "mean"),
            avg_rating=("rating", "mean"),
            latest_review=("review_date", "max"),
        )
    )
    if summary.empty:
        summary["switching_pressure"] = []
        return summary

    max_count = max(int(summary["complaint_count"].max()), 1)
    summary["switching_pressure"] = summary.apply(
        lambda row: switching_pressure_score(
            int(row.complaint_count),
            float(row.avg_severity),
            float(row.avg_recency),
            max_count,
        ),
        axis=1,
    )
    return summary


def provider_rollup(summary: pd.DataFrame) -> pd.DataFrame:
    if summary.empty:
        return pd.DataFrame(columns=["provider", "pressure_index", "top_theme", "top_score", "complaints"])
    rows = []
    for provider, group in summary.groupby("provider"):
        ranked = group.sort_values("switching_pressure", ascending=False)
        max_score = float(ranked.iloc[0]["switching_pressure"])
        mean_score = float(group["switching_pressure"].mean())
        rows.append(
            {
                "provider": provider,
                "pressure_index": round((0.65 * max_score) + (0.35 * mean_score), 1),
                "top_theme": ranked.iloc[0]["theme"],
                "top_score": max_score,
                "complaints": int(group["complaint_count"].sum()),
            }
        )
    return pd.DataFrame(rows).sort_values("pressure_index", ascending=False)


def fastest_rising_theme(frame: pd.DataFrame) -> dict:
    if frame.empty:
        return {"theme": "N/A", "latest": 0, "prior": 0, "delta": 0}
    as_of = frame["review_date"].max()
    latest_start = as_of - timedelta(days=44)
    prior_start = latest_start - timedelta(days=45)

    latest = frame[frame["review_date"] >= latest_start].groupby("theme").size()
    prior = frame[(frame["review_date"] >= prior_start) & (frame["review_date"] < latest_start)].groupby("theme").size()
    themes = sorted(set(frame["theme"]))
    rows = []
    for theme in themes:
        l = int(latest.get(theme, 0))
        p = int(prior.get(theme, 0))
        rows.append({"theme": theme, "latest": l, "prior": p, "delta": l - p})
    return sorted(rows, key=lambda x: (x["delta"], x["latest"]), reverse=True)[0]


def top_segment(frame: pd.DataFrame) -> dict:
    if frame.empty:
        return {"company_size": "N/A", "industry": "N/A", "complaints": 0, "avg_severity": 0}
    seg = (
        frame.groupby(["company_size", "industry"], as_index=False)
        .agg(complaints=("text", "count"), avg_severity=("severity", "mean"))
    )
    seg["opportunity_score"] = seg["complaints"] * seg["avg_severity"]
    row = seg.sort_values(["opportunity_score", "avg_severity", "complaints"], ascending=False).iloc[0]
    return row.to_dict()


def complaint_card(row) -> str:
    quote = escape(safe_quote(row.text, 260))
    provider = escape(str(row.provider))
    theme = escape(theme_label(row.category))
    source = escape(str(row.source))
    company_size = escape(str(row.company_size))
    industry = escape(str(row.industry))
    region = escape(str(row.region))
    return f"""
    <div class="quote-card">
      <div class="quote-meta">{provider} · {theme} · Severity {row.severity} · {row.review_date.date()}</div>
      <div class="quote-text">“{quote}”</div>
      <div class="quote-meta" style="margin-top:.45rem;">{source} · {company_size} employees · {industry} · {region}</div>
    </div>
    """


DISCOVERY_QUESTIONS = {
    "Implementation": [
        "How closely did your implementation timeline match the original plan?",
        "Who owned training, migration, and go-live issues when something slipped?",
        "What would you change about onboarding if you switched providers today?",
    ],
    "Tax Filing": [
        "How confident are you that filings and corrections are handled before penalties appear?",
        "What happens when a tax notice or filing issue needs escalation?",
        "How much time does your team spend checking payroll tax work manually?",
    ],
    "Support Response": [
        "When payroll is at risk, how quickly can you reach someone who owns the issue?",
        "How many handoffs does a typical support problem require?",
        "Which payroll problems tend to remain open the longest?",
    ],
    "Surprise Billing": [
        "How predictable are invoices, renewals, and add-on charges?",
        "Which fees have been hardest to forecast or explain internally?",
        "How easy is it to verify that contracted features match what is billed?",
    ],
    "Reporting": [
        "Which reports still require manual cleanup or spreadsheet work?",
        "How quickly can managers get the data they need without payroll expertise?",
        "What reporting request is most painful during month-end or year-end?",
    ],
    "Integrations": [
        "Which integrations create the most reconciliation work when they fail?",
        "How visible is the cause when data stops syncing?",
        "How often does your team manually repair data between payroll and other systems?",
    ],
    "Other": [
        "What part of payroll operations creates the most avoidable work today?",
        "Where do issues usually get stuck when something goes wrong?",
        "What would make a provider change worth the disruption?",
    ],
}


def battlecard_markdown(provider: str, frame: pd.DataFrame, summary: pd.DataFrame, brief=None) -> str:
    p_summary = summary[summary["provider"] == provider].sort_values("switching_pressure", ascending=False)
    p_reviews = frame[frame["provider"] == provider].sort_values(["severity", "review_date"], ascending=False)
    top_themes = p_summary.head(2)["theme"].tolist()
    if not top_themes:
        top_themes = ["Other"]
    questions = []
    for theme in top_themes:
        for q in DISCOVERY_QUESTIONS.get(theme, DISCOVERY_QUESTIONS["Other"]):
            if q not in questions:
                questions.append(q)
    quotes = [safe_quote(x, 180) for x in p_reviews["text"].head(3).tolist()]
    evidence = "\n".join([f"- \"{q}\"" for q in quotes]) or "- No matching review excerpts."
    theme_line = ", ".join(top_themes)
    ai_section = ""
    if brief is not None:
        ai_section = dedent(
            f"""
            ## Call point of view
            **{brief.headline}**

            {brief.executive_summary}

            **Open with:** {brief.opening_question}

            **Recommended next step:** {brief.recommended_next_step}

            **Guardrail:** {brief.watch_out}
            """
        ).strip()

    return dedent(
        f"""
        # PayFwds Signal Battlecard: {provider}

        ## Competitive signal
        The strongest public-review pressure themes in the current view are **{theme_line}**.

        {ai_section}

        ## Discovery angle
        Do not attack the competitor. Use the themes to ask whether the prospect experiences the same operational friction, then validate whether PayFwds can demonstrate a better workflow before making a claim.

        ## Questions to ask
        {chr(10).join(f'- {q}' for q in questions[:5])}

        ## Representative public-review evidence
        {evidence}

        ## Rep checklist
        - Confirm the prospect's current provider and pain before positioning.
        - Use aggregate patterns, not reviewer identities.
        - Cite the public-review source when using a quote.
        - Validate every PayFwds capability before presenting it as a differentiator.
        """
    ).strip()


# -----------------------------
# Header + filters
# -----------------------------

df = load_data()
if df.empty:
    st.error("No review data is available.")
    st.stop()

st.markdown(
    """
    <div class="signal-hero">
      <div class="signal-kicker">PAYFWDS SIGNAL // THE PROOF BEFORE THE PITCH</div>
      <div class="signal-title">Know the risk.<br><span class="accent">Earn the call.</span></div>
      <div class="signal-sub">Signal turns thousands of payroll complaints into one credible pre-call advantage: where a provider breaks down, which teams feel it most, and the questions that uncover a reason to switch.</div>
      <span class="signal-chip">Market pressure map</span>
      <span class="signal-chip">Segment-level evidence</span>
      <span class="signal-chip">AI call briefs</span>
      <span class="signal-chip">Privacy by design</span><br>
      <span class="live-badge"><span class="live-dot"></span> GEMINI-POWERED SALES INTELLIGENCE</span>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### Build the signal")
    st.caption("Define the market slice. Every insight and call brief updates together.")
    providers = st.multiselect("Provider", sorted(df.provider.unique()), default=sorted(df.provider.unique()))
    categories = st.multiselect("Failure category", sorted(df.theme.unique()), default=sorted(df.theme.unique()))
    sizes = st.multiselect("Company size", sorted(df.company_size.dropna().unique()), default=sorted(df.company_size.dropna().unique()))
    industries = st.multiselect("Industry", sorted(df.industry.dropna().unique()), default=sorted(df.industry.dropna().unique()))
    regions = st.multiselect("Region", sorted(df.region.dropna().unique()), default=sorted(df.region.dropna().unique()))
    st.divider()
    st.markdown("**Gemini copilot**")
    saved_gemini_key = configured_gemini_key()
    if saved_gemini_key:
        gemini_api_key = saved_gemini_key
        st.success(f"Connected · {MODEL_NAME}")
    else:
        gemini_api_key = st.text_input(
            "Gemini API key",
            type="password",
            help="Used only for this session. Set GEMINI_API_KEY in the environment for deployment.",
        )
        st.caption("Add a key for live AI briefs. Without one, Signal shows a deterministic grounded preview.")
    st.divider()
    st.markdown("**Demo data status**")
    st.caption("Synthetic, clearly labeled review data keeps the demo safe and repeatable. Production ingestion is limited to permitted APIs and published datasets.")

filtered = df[
    df.provider.isin(providers)
    & df.theme.isin(categories)
    & df.company_size.isin(sizes)
    & df.industry.isin(industries)
    & df.region.isin(regions)
].copy()

if filtered.empty:
    st.warning("No reviews match the current filters. Add at least one value back to a filter.")
    st.stop()

summary = pressure_summary(filtered)
rollup = provider_rollup(summary)
rising = fastest_rising_theme(filtered)
segment = top_segment(filtered)
highest_row = summary.sort_values("switching_pressure", ascending=False).iloc[0]
weakest = rollup.iloc[0]

# Executive signal cards
card_cols = st.columns(4)
card_payloads = [
    (
        "Highest switching pressure",
        f"{highest_row.provider} · {highest_row.theme}",
        f"Score {highest_row.switching_pressure:.1f}/100 · {int(highest_row.complaint_count)} complaint(s)",
    ),
    (
        "Weakest provider signal",
        str(weakest.provider),
        f"Pressure index {weakest.pressure_index:.1f}/100 · strongest theme: {weakest.top_theme}",
    ),
    (
        "Fastest-rising complaint",
        str(rising["theme"]),
        f"Latest 45 days: {rising['latest']} · prior 45 days: {rising['prior']} · change {rising['delta']:+d}",
    ),
    (
        "Most exposed segment",
        f"{segment['company_size']} · {segment['industry']}",
        f"{int(segment['complaints'])} complaint(s) · average severity {float(segment['avg_severity']):.1f}/3",
    ),
]
for col, (label, value, detail) in zip(card_cols, card_payloads):
    with col:
        st.markdown(
            f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="metric-detail">{detail}</div></div>',
            unsafe_allow_html=True,
        )

st.write("")

with st.expander("▶ 5-minute judge demo path", expanded=False):
    d1, d2, d3 = st.columns(3)
    with d1:
        st.markdown('<div class="demo-step"><div class="demo-num">STEP 01</div><div class="demo-title">Find the pressure</div><div class="demo-copy">Start on Overview. Show which provider + failure theme has the highest switching pressure.</div></div>', unsafe_allow_html=True)
    with d2:
        st.markdown('<div class="demo-step"><div class="demo-num">STEP 02</div><div class="demo-title">Explain who feels it</div><div class="demo-copy">Open Provider Intel. Drill into industry, company size, severity, trend, and representative reviews.</div></div>', unsafe_allow_html=True)
    with d3:
        st.markdown('<div class="demo-step"><div class="demo-num">STEP 03</div><div class="demo-title">Earn the next conversation</div><div class="demo-copy">Open AI Call Brief. Let Gemini turn the evidence into a grounded opening, discovery path, and next step.</div></div>', unsafe_allow_html=True)

# -----------------------------
# Tabs
# -----------------------------

overview_tab, provider_tab, battle_tab, methodology_tab = st.tabs(
    ["01 · Market map", "02 · Provider dossier", "03 · AI call brief", "04 · Trust & method"]
)

with overview_tab:
    st.markdown("### See the market break before the prospect says it")
    st.caption("Higher pressure means a complaint pattern is more frequent, more severe, and more recent in the selected evidence.")

    left, right = st.columns([1.05, 1])
    with left:
        chart_data = rollup.sort_values("pressure_index", ascending=True)
        pressure_chart = (
            alt.Chart(chart_data)
            .mark_bar(cornerRadiusEnd=6)
            .encode(
                y=alt.Y("provider:N", sort=None, title=None),
                x=alt.X("pressure_index:Q", title="Pressure index", scale=alt.Scale(domain=[0, 100])),
                tooltip=[
                    alt.Tooltip("provider:N", title="Provider"),
                    alt.Tooltip("pressure_index:Q", title="Pressure index", format=".1f"),
                    alt.Tooltip("top_theme:N", title="Strongest theme"),
                    alt.Tooltip("complaints:Q", title="Complaints"),
                ],
            )
            .properties(height=max(250, len(chart_data) * 46))
        )
        st.altair_chart(pressure_chart, use_container_width=True)

    with right:
        heat = summary.copy()
        heat_chart = (
            alt.Chart(heat)
            .mark_rect()
            .encode(
                x=alt.X("theme:N", title=None, axis=alt.Axis(labelAngle=-32)),
                y=alt.Y("provider:N", title=None),
                color=alt.Color(
                    "switching_pressure:Q",
                    title="Pressure",
                    scale=alt.Scale(scheme="purplered", domain=[0, 100]),
                ),
                tooltip=[
                    alt.Tooltip("provider:N", title="Provider"),
                    alt.Tooltip("theme:N", title="Theme"),
                    alt.Tooltip("switching_pressure:Q", title="Pressure", format=".1f"),
                    alt.Tooltip("complaint_count:Q", title="Complaints"),
                    alt.Tooltip("avg_severity:Q", title="Avg severity", format=".2f"),
                ],
            )
            .properties(height=max(250, filtered.provider.nunique() * 46))
        )
        st.altair_chart(heat_chart, use_container_width=True)

    st.markdown("### Where payroll pain is concentrated")
    st.caption(
        "The same pressure formula is rolled up geographically. Bubble size represents pressure; hover to reveal each region's dominant failure theme."
    )
    regional = regional_hotspots(filtered)
    map_col, region_col = st.columns([1.45, 0.75])
    with map_col:
        region_layer = pdk.Layer(
            "ScatterplotLayer",
            data=regional,
            get_position="[longitude, latitude]",
            get_radius="radius",
            get_fill_color="color",
            get_line_color=[246, 247, 251, 160],
            line_width_min_pixels=1,
            stroked=True,
            pickable=True,
            opacity=0.72,
        )
        region_deck = pdk.Deck(
            map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
            initial_view_state=pdk.ViewState(
                latitude=39.5,
                longitude=-98.35,
                zoom=2.75,
                pitch=18,
            ),
            layers=[region_layer],
            tooltip={
                "html": (
                    "<b>{region}</b><br/>Pressure: {pressure}/100<br/>"
                    "Leading theme: {dominant_theme}<br/>{complaints} complaints · {providers} providers"
                ),
                "style": {"backgroundColor": "#121620", "color": "#F6F7FB"},
            },
        )
        st.pydeck_chart(region_deck, use_container_width=True, height=390)

    with region_col:
        hotspot = regional.iloc[0]
        st.markdown('<div class="eyebrow">Highest-pressure region</div>', unsafe_allow_html=True)
        st.markdown(f"## {hotspot.region}")
        st.markdown(
            f"**{hotspot.dominant_theme}** is the dominant signal, with a regional pressure score of "
            f"**{hotspot.pressure:.1f}/100** across **{int(hotspot.complaints)}** complaints."
        )
        st.caption(
            "This is a directional view of the selected evidence—not a population-adjusted market estimate."
        )
        regional_table = regional[["region", "dominant_theme", "complaints", "pressure"]].copy()
        regional_table.columns = ["Region", "Leading theme", "Complaints", "Pressure"]
        st.dataframe(
            regional_table,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Pressure": st.column_config.ProgressColumn(
                    "Pressure",
                    min_value=0,
                    max_value=100,
                    format="%.1f",
                )
            },
        )

    st.markdown("### Complaint movement")
    trend = (
        filtered.groupby(["month", "theme"], as_index=False)
        .size()
        .rename(columns={"size": "complaints"})
    )
    trend_chart = (
        alt.Chart(trend)
        .mark_line(point=True, strokeWidth=2.4)
        .encode(
            x=alt.X("month:T", title="Month", axis=alt.Axis(format="%b %Y")),
            y=alt.Y("complaints:Q", title="Complaints", axis=alt.Axis(tickMinStep=1)),
            color=alt.Color("theme:N", title="Failure theme"),
            tooltip=[
                alt.Tooltip("month:T", title="Month", format="%b %Y"),
                alt.Tooltip("theme:N", title="Theme"),
                alt.Tooltip("complaints:Q", title="Complaints"),
            ],
        )
        .properties(height=320)
    )
    st.altair_chart(trend_chart, use_container_width=True)

    st.markdown("### Ranked signals")
    leaderboard = summary.sort_values("switching_pressure", ascending=False).copy()
    leaderboard["avg_severity"] = leaderboard["avg_severity"].round(2)
    leaderboard["avg_rating"] = leaderboard["avg_rating"].round(2)
    st.dataframe(
        leaderboard[["provider", "theme", "complaint_count", "avg_severity", "avg_rating", "switching_pressure", "latest_review"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "provider": "Provider",
            "theme": "Failure theme",
            "complaint_count": "Complaints",
            "avg_severity": st.column_config.NumberColumn("Avg severity", format="%.2f"),
            "avg_rating": st.column_config.NumberColumn("Avg rating", format="%.2f"),
            "switching_pressure": st.column_config.ProgressColumn("Switching pressure", min_value=0, max_value=100, format="%.1f"),
            "latest_review": st.column_config.DatetimeColumn("Latest review", format="MMM D, YYYY"),
        },
    )

with provider_tab:
    st.markdown("### Build a provider point of view")
    selected_provider = st.selectbox("Choose a provider", sorted(filtered.provider.unique()), key="provider_intel")
    p_reviews = filtered[filtered.provider == selected_provider].copy()
    p_summary = summary[summary.provider == selected_provider].sort_values("switching_pressure", ascending=False)

    if p_summary.empty:
        st.info("No provider data matches the current filters.")
    else:
        top = p_summary.iloc[0]
        p_rising = fastest_rising_theme(p_reviews)
        p_segment = top_segment(p_reviews)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Top pain", top.theme, f"{top.switching_pressure:.1f}/100 pressure")
        m2.metric("Complaints in view", len(p_reviews))
        m3.metric("Average severity", f"{p_reviews.severity.mean():.1f}/3")
        m4.metric("Rising theme", p_rising["theme"], f"{p_rising['delta']:+d} vs prior 45d")

        a, b = st.columns([1.12, 1])
        with a:
            provider_bars = (
                alt.Chart(p_summary.sort_values("switching_pressure", ascending=True))
                .mark_bar(cornerRadiusEnd=6)
                .encode(
                    y=alt.Y("theme:N", sort=None, title=None),
                    x=alt.X("switching_pressure:Q", title="Switching pressure", scale=alt.Scale(domain=[0, 100])),
                    tooltip=[
                        alt.Tooltip("theme:N", title="Theme"),
                        alt.Tooltip("switching_pressure:Q", title="Pressure", format=".1f"),
                        alt.Tooltip("complaint_count:Q", title="Complaints"),
                        alt.Tooltip("avg_severity:Q", title="Avg severity", format=".2f"),
                    ],
                )
                .properties(height=max(270, len(p_summary) * 48))
            )
            st.altair_chart(provider_bars, use_container_width=True)

        with b:
            seg = (
                p_reviews.groupby(["company_size", "industry"], as_index=False)
                .agg(complaints=("text", "count"), avg_severity=("severity", "mean"))
                .sort_values(["avg_severity", "complaints"], ascending=False)
            )
            st.markdown("#### Most exposed customer segments")
            st.dataframe(
                seg,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "company_size": "Company size",
                    "industry": "Industry",
                    "complaints": "Complaints",
                    "avg_severity": st.column_config.NumberColumn("Avg severity", format="%.1f"),
                },
            )
            st.caption(
                f"Current signal: {p_segment['company_size']} employee companies in {p_segment['industry']} show the strongest combined complaint/severity pattern in this filtered sample."
            )

        st.markdown("#### Representative complaints")
        st.caption("Quotes are short excerpts. They are displayed with the source, never attached to an individual reviewer identity.")
        for row in p_reviews.sort_values(["severity", "review_date"], ascending=False).head(8).itertuples(index=False):
            st.markdown(complaint_card(row), unsafe_allow_html=True)

with battle_tab:
    st.markdown("### Walk into the call with a point of view")
    st.caption(
        "Gemini converts the selected market evidence into a concise, human call plan. "
        "Every claim is constrained to the aggregate data in view."
    )

    battle_provider = st.selectbox("Competitor", sorted(filtered.provider.unique()), key="battle_provider")
    call_objective = st.text_input(
        "What should this call accomplish?",
        value="Understand the cost of payroll friction and earn a workflow comparison.",
        help="Gemini uses this goal to shape the questions and next step.",
    )
    battle_summary = summary[summary.provider == battle_provider].sort_values("switching_pressure", ascending=False)
    battle_reviews = filtered[filtered.provider == battle_provider].sort_values(["severity", "review_date"], ascending=False)

    if battle_summary.empty:
        st.info("No matching signal for this provider.")
    else:
        battle_top = battle_summary.iloc[0]
        battle_second = battle_summary.iloc[1] if len(battle_summary) > 1 else None
        top_themes = [battle_top.theme] + ([battle_second.theme] if battle_second is not None else [])
        questions: list[str] = []
        for theme in top_themes:
            for q in DISCOVERY_QUESTIONS.get(theme, DISCOVERY_QUESTIONS["Other"]):
                if q not in questions:
                    questions.append(q)
        evidence_payload = build_evidence_payload(battle_reviews, battle_summary)
        active_brief = fallback_brief(
            battle_provider,
            call_objective,
            evidence_payload,
            questions,
        )
        brief_source = "Grounded preview · connect Gemini for live generation"

        generate_label = "Generate live brief with Gemini" if gemini_api_key else "Preview grounded call brief"
        if st.button(generate_label, type="primary", use_container_width=True):
            if gemini_api_key:
                try:
                    with st.spinner("Gemini is turning evidence into a call plan…"):
                        active_brief = generate_gemini_brief(
                            battle_provider,
                            call_objective,
                            evidence_payload,
                            gemini_api_key,
                        )
                    brief_source = f"Generated live with {MODEL_NAME}"
                    st.session_state["gemini_brief"] = {
                        "provider": battle_provider,
                        "objective": call_objective,
                        "brief": active_brief,
                    }
                except Exception as exc:
                    st.warning(f"Gemini could not generate this brief, so the grounded preview is shown. {exc}")
            else:
                st.info("Preview mode is active. Add GEMINI_API_KEY in the sidebar to generate with Gemini.")

        cached_brief = st.session_state.get("gemini_brief")
        if (
            cached_brief
            and cached_brief["provider"] == battle_provider
            and cached_brief["objective"] == call_objective
        ):
            active_brief = cached_brief["brief"]
            brief_source = f"Generated live with {MODEL_NAME}"

        st.markdown(
            f"""
            <div class="brief-hero">
              <div class="brief-kicker">{escape(brief_source.upper())}</div>
              <div class="brief-headline">{escape(active_brief.headline)}</div>
              <div class="brief-copy">{escape(active_brief.executive_summary)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        q_col, proof_col = st.columns([1.15, 0.85])
        with q_col:
            st.markdown('<div class="eyebrow">Open with curiosity</div>', unsafe_allow_html=True)
            st.markdown(f"#### “{active_brief.opening_question}”")
            st.markdown('<div class="eyebrow">Then go one level deeper</div>', unsafe_allow_html=True)
            for i, question in enumerate(active_brief.discovery_questions, start=1):
                st.markdown(f"**{i:02d}** &nbsp; {question}")

        with proof_col:
            st.markdown('<div class="eyebrow">Evidence in the current view</div>', unsafe_allow_html=True)
            proof_html = "".join(
                f'<div class="proof-row"><span class="accent">↗</span>&nbsp; {escape(point)}</div>'
                for point in active_brief.proof_points
            )
            st.markdown(f'<div class="section-card">{proof_html}</div>', unsafe_allow_html=True)
            st.markdown('<div class="eyebrow" style="margin-top:1rem">Do not overclaim</div>', unsafe_allow_html=True)
            st.warning(active_brief.watch_out)
            st.markdown('<div class="eyebrow">Recommended next move</div>', unsafe_allow_html=True)
            st.success(active_brief.recommended_next_step)

        with st.expander("View the evidence Gemini received"):
            st.json(evidence_payload)
            st.caption(
                "Only aggregate metrics and de-identified excerpts are sent. Reviewer names and contact details are never included."
            )

        battle_md = battlecard_markdown(battle_provider, filtered, summary, active_brief)
        st.download_button(
            "Export rep-ready battlecard",
            data=battle_md,
            file_name=f"{battle_provider.lower().replace(' ', '_')}_battlecard.md",
            mime="text/markdown",
            use_container_width=False,
        )

with methodology_tab:
    st.markdown("### Trust every signal you take into a call")
    st.markdown(
        "Signal separates measurement from generation. The scoring layer stays deterministic and auditable; "
        "Gemini receives only the filtered evidence and turns it into questions—not unsupported claims."
    )

    s1, s2, s3, s4 = st.columns(4)
    method_cards = [
        ("01 · Collect", "Ingest only public-review sources whose terms allow automated access, or a permitted API/published dataset."),
        ("02 · Measure", "Classify complaints, then combine volume, severity, and recency into an explainable 0–100 pressure score."),
        ("03 · Ground", "Package only aggregate metrics and de-identified excerpts from the selected view—never reviewer identities."),
        ("04 · Activate", f"Use {MODEL_NAME} structured output to create a call brief that remains bounded by the supplied evidence."),
    ]
    for col, (title, copy) in zip([s1, s2, s3, s4], method_cards):
        with col:
            st.markdown(f'<div class="metric-card"><div class="metric-value" style="font-size:1.05rem">{title}</div><div class="metric-detail">{copy}</div></div>', unsafe_allow_html=True)

    st.markdown("#### Switching Pressure formula")
    st.code(
        "score = 100 × (0.45 × normalized_volume + 0.35 × severity + 0.20 × recency)",
        language="text",
    )
    st.markdown(
        "- **Volume** is log-normalized so a large provider does not win simply because it has more customers.\n"
        "- **Severity** converts the 1–3 severity level to a 0–1 signal.\n"
        "- **Recency** decays over time with a 180-day half-life.\n"
        "- The score is a prioritization aid, **not** a statistically representative market-share or churn prediction."
    )

    st.markdown("#### Ground rules baked into the product")
    st.markdown(
        "- Do not scrape sources that prohibit automated access.\n"
        "- Respect robots.txt, rate limits, and source-specific terms.\n"
        "- Analyze reviews in aggregate. Do not deanonymize reviewers or collect contact information.\n"
        "- Keep a citation/source field for every representative quote.\n"
        "- Do not convert competitor pain into an unsupported PayFwds product claim."
    )

    export_cols = [
        "provider", "theme", "rating", "review_date", "source", "company_size", "industry", "region", "severity", "confidence"
    ]
    st.download_button(
        "Download current aggregated view (.csv)",
        data=filtered[export_cols].to_csv(index=False).encode("utf-8"),
        file_name="payfwds_signal_filtered_view.csv",
        mime="text/csv",
    )

st.markdown(
    f"<div class='footer-note'>PayFwds Signal · The proof before the pitch · AI call briefs powered by {MODEL_NAME} · Synthetic data is clearly labeled · Public-review intelligence must follow source terms and privacy ground rules.</div>",
    unsafe_allow_html=True,
)
