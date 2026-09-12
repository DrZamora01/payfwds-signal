from __future__ import annotations

import pandas as pd

try:
    from .pipeline import switching_pressure_score
except ImportError:
    from pipeline import switching_pressure_score


REGION_COORDS = {
    "Northeast": (42.6, -73.7),
    "Midwest": (41.9, -93.1),
    "South": (33.1, -84.2),
    "West": (40.4, -116.5),
}


def regional_hotspots(frame: pd.DataFrame) -> pd.DataFrame:
    """Aggregate selected evidence into mappable regional pressure signals."""

    if frame.empty:
        return pd.DataFrame()
    grouped = (
        frame.groupby("region", as_index=False)
        .agg(
            complaints=("text", "count"),
            avg_severity=("severity", "mean"),
            avg_recency=("recency", "mean"),
            providers=("provider", "nunique"),
        )
    )
    max_count = max(int(grouped["complaints"].max()), 1)
    grouped["pressure"] = grouped.apply(
        lambda row: switching_pressure_score(
            int(row.complaints),
            float(row.avg_severity),
            float(row.avg_recency),
            max_count,
        ),
        axis=1,
    )

    dominant = (
        frame.groupby(["region", "theme"], as_index=False)
        .agg(mentions=("text", "count"), theme_severity=("severity", "mean"))
    )
    dominant["rank"] = dominant["mentions"] * dominant["theme_severity"]
    dominant = (
        dominant.sort_values(["region", "rank", "mentions"], ascending=[True, False, False])
        .drop_duplicates("region")
        [["region", "theme"]]
        .rename(columns={"theme": "dominant_theme"})
    )
    grouped = grouped.merge(dominant, on="region", how="left")
    grouped["latitude"] = grouped["region"].map(lambda value: REGION_COORDS.get(value, (39.5, -98.35))[0])
    grouped["longitude"] = grouped["region"].map(lambda value: REGION_COORDS.get(value, (39.5, -98.35))[1])
    grouped["radius"] = 140_000 + (grouped["pressure"] * 7_500)
    grouped["color"] = grouped["pressure"].map(
        lambda score: [183, 227, 61, 205] if score >= 75 else [112, 87, 190, 195]
    )
    return grouped.sort_values("pressure", ascending=False)
