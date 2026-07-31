import pandas as pd

from geoestate.pipeline import preprocess_dataframe


def test_preprocess_standardizes_and_enriches_schema() -> None:
    raw = pd.DataFrame(
        {
            "Unnamed: 0": [0, 1, 2],
            "title": [" 3 BHK Apartment ", "3 BHK Apartment", "Invalid"],
            "location": [" Nizampet ", "Nizampet", ""],
            "price(L)": [108, 108, 0],
            "rate_persqft": [6000, 6000, 4000],
            "area_insqft": [1805, 1805, 0],
            "building_status": ["Under Construction", "Under Construction", "Ready"],
            "SwimmingPool": ["Yes", "Yes", "No"],
        }
    )

    processed = preprocess_dataframe(raw)

    assert len(processed) == 1
    assert processed.loc[0, "property_id"].startswith("hyd-")
    assert processed.loc[0, "location"] == "Nizampet"
    assert processed.loc[0, "bedrooms"] == 3
    assert "price_lakh" in processed.columns
    assert "area_sqft" in processed.columns
    assert "swimming_pool" in processed.columns
    assert processed["property_id"].is_unique
    assert processed["latitude"].isna().all()
    assert processed["ai_summary"].isna().all()
