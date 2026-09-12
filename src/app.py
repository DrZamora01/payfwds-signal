from __future__ import annotations

from datetime import datetime, timedelta
from html import escape
from pathlib import Path
from textwrap import dedent

import altair as alt
import pandas as pd
import streamlit as st

from pipeline import Review, classify_many, recency_weight, safe_quote, switching_pressure_score

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
    page_title="PayFwds Signal",
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


def battlecard_markdown(provider: str, frame: pd.DataFrame, summary: pd.DataFrame) -> str:
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

    return dedent(
        f"""
        # PayFwds Signal Battlecard: {provider}

        ## Competitive signal
        The strongest public-review pressure themes in the current view are **{theme_line}**.

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
      <div class="signal-kicker">PAYFWDS // COMPETITIVE INTELLIGENCE</div>
      <div class="signal-title">Signal</div>
      <div class="signal-sub">Turn public payroll complaints into a five-minute pre-call brief: where competitors fail, who feels the pain, and which issue creates the strongest switching pressure.</div>
      <span class="signal-chip">Aggregated public reviews</span>
      <span class="signal-chip">Explainable scoring</span>
      <span class="signal-chip">Sales battlecards</span>
      <span class="signal-chip">No reviewer de-anonymization</span>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### Signal controls")
    st.caption("Narrow the market view. Every tab updates together.")
    providers = st.multiselect("Provider", sorted(df.provider.unique()), default=sorted(df.provider.unique()))
    categories = st.multiselect("Failure category", sorted(df.theme.unique()), default=sorted(df.theme.unique()))
    sizes = st.multiselect("Company size", sorted(df.company_size.dropna().unique()), default=sorted(df.company_size.dropna().unique()))
    industries = st.multiselect("Industry", sorted(df.industry.dropna().unique()), default=sorted(df.industry.dropna().unique()))
    regions = st.multiselect("Region", sorted(df.region.dropna().unique()), default=sorted(df.region.dropna().unique()))
    st.divider()
    st.markdown("**Demo data status**")
    st.caption("This starter build uses synthetic sample reviews so the product can be demonstrated safely. Replace them with a permitted API or published dataset before a real competitive analysis.")

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
        st.markdown('<div class="demo-step"><div class="demo-num">STEP 03</div><div class="demo-title">Turn insight into action</div><div class="demo-copy">Open Battlecards. Generate discovery questions and an evidence-backed pre-call brief a rep can download.</div></div>', unsafe_allow_html=True)

# -----------------------------
# Tabs
# -----------------------------

overview_tab, provider_tab, battle_tab, methodology_tab = st.tabs(
    ["Overview", "Provider Intel", "Battlecards", "Methodology"]
)

with overview_tab:
    st.markdown("### Market pressure map")
    st.caption("A high score means the complaint pattern is more frequent, more severe, and more recent within the current filtered view.")

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
    st.markdown("### Provider intelligence")
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
    st.markdown("### Sales battlecard builder")
    st.caption("Convert market evidence into discovery questions. Signal helps a rep prepare; it does not invent product claims.")

    battle_provider = st.selectbox("Competitor", sorted(filtered.provider.unique()), key="battle_provider")
    battle_summary = summary[summary.provider == battle_provider].sort_values("switching_pressure", ascending=False)
    battle_reviews = filtered[filtered.provider == battle_provider].sort_values(["severity", "review_date"], ascending=False)

    if battle_summary.empty:
        st.info("No matching signal for this provider.")
    else:
        battle_top = battle_summary.iloc[0]
        battle_second = battle_summary.iloc[1] if len(battle_summary) > 1 else None
        top_themes = [battle_top.theme] + ([battle_second.theme] if battle_second is not None else [])

        c1, c2 = st.columns([1.1, 1])
        with c1:
            st.markdown('<div class="battle-title">What the signal says</div>', unsafe_allow_html=True)
            st.markdown(
                f"**{battle_provider}** shows its strongest current pressure around **{battle_top.theme}** "
                f"({battle_top.switching_pressure:.1f}/100)."
            )
            if battle_second is not None:
                st.markdown(
                    f"A secondary theme is **{battle_second.theme}** ({battle_second.switching_pressure:.1f}/100)."
                )
            st.info(
                "Position this as a discovery hypothesis, not a universal claim: ask whether the prospect experiences the same friction before you compare solutions."
            )

        with c2:
            st.markdown('<div class="battle-title">Call objective</div>', unsafe_allow_html=True)
            st.markdown(
                "1. Confirm whether the public-review pain exists for this prospect.\n"
                "2. Quantify the operational impact.\n"
                "3. Demonstrate only PayFwds capabilities that have been validated by the team."
            )

        st.markdown("#### Questions to ask")
        questions: list[str] = []
        for theme in top_themes:
            for q in DISCOVERY_QUESTIONS.get(theme, DISCOVERY_QUESTIONS["Other"]):
                if q not in questions:
                    questions.append(q)
        for i, q in enumerate(questions[:5], start=1):
            st.markdown(f"**{i}.** {q}")

        st.markdown("#### Evidence to cite")
        for row in battle_reviews.head(3).itertuples(index=False):
            st.markdown(complaint_card(row), unsafe_allow_html=True)

        battle_md = battlecard_markdown(battle_provider, filtered, summary)
        st.download_button(
            "Download battlecard (.md)",
            data=battle_md,
            file_name=f"{battle_provider.lower().replace(' ', '_')}_battlecard.md",
            mime="text/markdown",
            use_container_width=False,
        )

with methodology_tab:
    st.markdown("### How Signal works")
    st.markdown(
        "Signal intentionally keeps the analytical pipeline simple and explainable for a hackathon build. "
        "A future team can replace each stage independently without redesigning the product."
    )

    s1, s2, s3, s4 = st.columns(4)
    method_cards = [
        ("01 · Collect", "Ingest only public-review sources whose terms allow automated access, or a permitted API/published dataset."),
        ("02 · Classify", "Map each negative review to a failure category such as implementation, tax filing, support, billing, reporting, or integrations."),
        ("03 · Score", "Combine complaint volume, severity, and recency into a 0–100 Switching Pressure score."),
        ("04 · Activate", "Aggregate by provider and customer segment, then turn the strongest patterns into sales-ready discovery prompts."),
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
    "<div class='footer-note'>PayFwds Signal · Hackathon product prototype · Synthetic demo data in this starter build · Public-review intelligence should always follow source terms and privacy ground rules.</div>",
    unsafe_allow_html=True,
)
