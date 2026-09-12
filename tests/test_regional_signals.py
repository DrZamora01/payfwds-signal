import pandas as pd

from src.regional_signals import regional_hotspots


def test_regional_hotspots_maps_pressure_and_dominant_theme():
    frame = pd.DataFrame(
        [
            {
                "region": "South",
                "provider": "A",
                "theme": "Tax Filing",
                "text": "Tax issue",
                "severity": 3,
                "recency": 0.9,
            },
            {
                "region": "South",
                "provider": "B",
                "theme": "Tax Filing",
                "text": "Filing issue",
                "severity": 2,
                "recency": 0.8,
            },
            {
                "region": "West",
                "provider": "A",
                "theme": "Reporting",
                "text": "Report issue",
                "severity": 1,
                "recency": 0.5,
            },
        ]
    )

    result = regional_hotspots(frame)
    south = result[result.region == "South"].iloc[0]

    assert south.dominant_theme == "Tax Filing"
    assert south.providers == 2
    assert south.pressure > result[result.region == "West"].iloc[0].pressure
    assert (south.latitude, south.longitude) == (33.1, -84.2)


def test_regional_hotspots_handles_empty_frame():
    assert regional_hotspots(pd.DataFrame()).empty
