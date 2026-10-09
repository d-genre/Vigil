import pytest
import pandas as pd
import numpy as np
from backend.fraud_patterns.impossible_travel import detect_impossible_travel, haversine

CITIES_DATA = [
    {"city": "CityA", "country": "CountryA", "lat": 0.0, "lon": 0.0},
    {"city": "CityB", "country": "CountryA", "lat": 0.0, "lon": 1.0},
    {"city": "CityC", "country": "CountryA", "lat": 0.0, "lon": 10.0},
    {"city": "CityD", "country": "CountryA", "lat": 0.0, "lon": 90.0},
    {"city": "CityAntimeridian1", "country": "CountryA", "lat": 0.0, "lon": 179.0},
    {"city": "CityAntimeridian2", "country": "CountryA", "lat": 0.0, "lon": -179.0},
    {"city": "CityInvalid", "country": "CountryA", "lat": 999.0, "lon": 0.0}
]

@pytest.fixture
def sample_cities_df():
    return pd.DataFrame(CITIES_DATA)

def make_tx(tx_id, ts, acc, city, country="CountryA", is_fraud=0):
    return {
        "transaction_id": tx_id,
        "timestamp": ts,
        "nameOrig": acc,
        "city": city,
        "country": country,
        "isFraud": is_fraud,
        "fraud_type": "none",
        "campaign_id": "none"
    }

def test_01_valid_impossible_travel_pair(sample_cities_df):
    txs = [
        make_tx("1", "2026-01-01 10:00:00", "A1", "CityA"),
        make_tx("2", "2026-01-01 10:30:00", "A1", "CityC") 
    ]
    res = detect_impossible_travel("A1", pd.DataFrame(txs), sample_cities_df)
    assert res["detected"] is True
    assert res["score"] == 85.0

def test_02_plausible_short_distance(sample_cities_df):
    txs = [
        make_tx("1", "2026-01-01 10:00:00", "A1", "CityA"),
        make_tx("2", "2026-01-01 12:00:00", "A1", "CityB") 
    ]
    res = detect_impossible_travel("A1", pd.DataFrame(txs), sample_cities_df)
    assert res["detected"] is False

def test_03_long_distance_sufficient_time(sample_cities_df):
    txs = [
        make_tx("1", "2026-01-01 10:00:00", "A1", "CityA"),
        make_tx("2", "2026-01-02 10:00:00", "A1", "CityD") 
    ]
    res = detect_impossible_travel("A1", pd.DataFrame(txs), sample_cities_df)
    assert res["detected"] is False

def test_04_missing_previous_location(sample_cities_df):
    txs = [
        make_tx("1", "2026-01-01 10:00:00", "A1", None),
        make_tx("2", "2026-01-01 11:00:00", "A1", "CityA")
    ]
    res = detect_impossible_travel("A1", pd.DataFrame(txs), sample_cities_df)
    assert res["detected"] is False

def test_05_missing_current_location(sample_cities_df):
    txs = [
        make_tx("1", "2026-01-01 10:00:00", "A1", "CityA"),
        make_tx("2", "2026-01-01 11:00:00", "A1", None)
    ]
    res = detect_impossible_travel("A1", pd.DataFrame(txs), sample_cities_df)
    assert res["detected"] is False

def test_06_invalid_coordinates(sample_cities_df):
    txs = [
        make_tx("1", "2026-01-01 10:00:00", "A1", "CityA"),
        make_tx("2", "2026-01-01 11:00:00", "A1", "CityInvalid")
    ]
    res = detect_impossible_travel("A1", pd.DataFrame(txs), sample_cities_df)
    assert res["detected"] is False

def test_07_unknown_city(sample_cities_df):
    txs = [
        make_tx("1", "2026-01-01 10:00:00", "A1", "CityA"),
        make_tx("2", "2026-01-01 11:00:00", "A1", "UnknownCity")
    ]
    res = detect_impossible_travel("A1", pd.DataFrame(txs), sample_cities_df)
    assert res["detected"] is False

def test_08_single_transaction(sample_cities_df):
    txs = [make_tx("1", "2026-01-01 10:00:00", "A1", "CityA")]
    res = detect_impossible_travel("A1", pd.DataFrame(txs), sample_cities_df)
    assert res["detected"] is False

def test_09_empty_dataframe(sample_cities_df):
    res = detect_impossible_travel("A1", pd.DataFrame(), sample_cities_df)
    assert res["detected"] is False

def test_10_missing_account(sample_cities_df):
    txs = [make_tx("1", "2026-01-01 10:00:00", "A2", "CityA")]
    res = detect_impossible_travel("A1", pd.DataFrame(txs), sample_cities_df)
    assert res["detected"] is False

def test_11_missing_required_timestamp(sample_cities_df):
    txs = [
        make_tx("1", "2026-01-01 10:00:00", "A1", "CityA"),
        make_tx("3", None, "A1", "CityD")
    ]
    res = detect_impossible_travel("A1", pd.DataFrame(txs), sample_cities_df)
    assert res["detected"] is False

def test_12_invalid_timestamp(sample_cities_df):
    txs = [
        make_tx("1", "2026-01-01 10:00:00", "A1", "CityA"),
        make_tx("2", "invalid_time", "A1", "CityC")
    ]
    res = detect_impossible_travel("A1", pd.DataFrame(txs), sample_cities_df)
    assert res["detected"] is False

def test_13_duplicate_transaction_ids(sample_cities_df):
    txs = [
        make_tx("1", "2026-01-01 10:00:00", "A1", "CityA"),
        make_tx("1", "2026-01-01 10:00:00", "A1", "CityA")
    ]
    res = detect_impossible_travel("A1", pd.DataFrame(txs), sample_cities_df)
    assert res["detected"] is False

def test_14_equal_timestamps(sample_cities_df):
    txs = [
        make_tx("1", "2026-01-01 10:00:00", "A1", "CityA"),
        make_tx("2", "2026-01-01 10:00:00", "A1", "CityC")
    ]
    res = detect_impossible_travel("A1", pd.DataFrame(txs), sample_cities_df)
    assert res["detected"] is True

def test_15_negative_elapsed_interval(sample_cities_df):
    txs = [
        make_tx("1", "2026-01-01 10:00:00", "A1", "CityA"),
        make_tx("2", "2026-01-01 09:00:00", "A1", "CityC")
    ]
    res = detect_impossible_travel("A1", pd.DataFrame(txs), sample_cities_df)
    assert res["detected"] is True

def test_16_stable_ordering(sample_cities_df):
    txs = [
        make_tx("1", "2026-01-01 10:00:00", "A1", "CityA"),
        make_tx("2", "2026-01-01 10:00:00", "A1", "CityC")
    ]
    res1 = detect_impossible_travel("A1", pd.DataFrame(txs), sample_cities_df)
    res2 = detect_impossible_travel("A1", pd.DataFrame([txs[1], txs[0]]), sample_cities_df)
    assert res1["score"] == res2["score"]

def test_17_exclusion_of_future_transactions(sample_cities_df):
    txs = [
        make_tx("1", "2026-01-01 10:00:00", "A1", "CityA"),
        make_tx("2", "2026-01-01 10:30:00", "A1", "CityC")
    ]
    res = detect_impossible_travel("A1", pd.DataFrame(txs), sample_cities_df, as_of_timestamp="2026-01-01 10:15:00")
    assert res["detected"] is False

def test_18_cutoff_exactly_at_investigated(sample_cities_df):
    txs = [
        make_tx("1", "2026-01-01 10:00:00", "A1", "CityA"),
        make_tx("2", "2026-01-01 10:30:00", "A1", "CityC")
    ]
    res = detect_impossible_travel("A1", pd.DataFrame(txs), sample_cities_df, as_of_timestamp="2026-01-01 10:30:00")
    assert res["detected"] is True

def test_19_earlier_cutoff_excludes(sample_cities_df):
    txs = [
        make_tx("1", "2026-01-01 10:00:00", "A1", "CityA"),
        make_tx("2", "2026-01-01 10:30:00", "A1", "CityC")
    ]
    res = detect_impossible_travel("A1", pd.DataFrame(txs), sample_cities_df, as_of_timestamp="2026-01-01 09:00:00")
    assert res["detected"] is False

def test_20_future_appended_records(sample_cities_df):
    txs = [make_tx("1", "2026-01-01 10:00:00", "A1", "CityA"), make_tx("2", "2026-01-01 12:00:00", "A1", "CityB")]
    res1 = detect_impossible_travel("A1", pd.DataFrame(txs), sample_cities_df, as_of_timestamp="2026-01-01 12:00:00")
    txs.append(make_tx("3", "2026-01-01 12:01:00", "A1", "CityD"))
    res2 = detect_impossible_travel("A1", pd.DataFrame(txs), sample_cities_df, as_of_timestamp="2026-01-01 12:00:00")
    assert res1["score"] == res2["score"]

def test_21_future_locations_cannot_change_score(sample_cities_df):
    txs = [make_tx("1", "2026-01-01 10:00:00", "A1", "CityA"), make_tx("2", "2026-01-01 12:00:00", "A1", "CityB")]
    res1 = detect_impossible_travel("A1", pd.DataFrame(txs), sample_cities_df, transaction_id="2")
    txs.append(make_tx("3", "2026-01-01 12:01:00", "A1", "CityD"))
    res2 = detect_impossible_travel("A1", pd.DataFrame(txs), sample_cities_df, transaction_id="2")
    assert res1["score"] == res2["score"]

def test_22_tx_id_investigation_uses_eligible_history(sample_cities_df):
    txs = [
        make_tx("1", "2026-01-01 10:00:00", "A1", "CityA"),
        make_tx("2", "2026-01-01 10:30:00", "A1", "CityC"),
        make_tx("3", "2026-01-01 11:00:00", "A1", "CityC")
    ]
    res_tx3 = detect_impossible_travel("A1", pd.DataFrame(txs), sample_cities_df, transaction_id="3")
    assert res_tx3["detected"] is False

def test_23_combined_tx_id_and_cutoff(sample_cities_df):
    txs = [
        make_tx("1", "2026-01-01 10:00:00", "A1", "CityA"),
        make_tx("2", "2026-01-01 10:30:00", "A1", "CityC")
    ]
    res = detect_impossible_travel("A1", pd.DataFrame(txs), sample_cities_df, transaction_id="2", as_of_timestamp="2026-01-01 10:15:00")
    assert res["detected"] is False

def test_24_works_without_isfraud(sample_cities_df):
    txs = [make_tx("1", "2026-01-01 10:00:00", "A1", "CityA"), make_tx("2", "2026-01-01 10:30:00", "A1", "CityC")]
    df = pd.DataFrame(txs).drop(columns=["isFraud"])
    res = detect_impossible_travel("A1", df, sample_cities_df)
    assert res["detected"] is True

def test_25_works_without_fraud_type(sample_cities_df):
    txs = [make_tx("1", "2026-01-01 10:00:00", "A1", "CityA"), make_tx("2", "2026-01-01 10:30:00", "A1", "CityC")]
    df = pd.DataFrame(txs).drop(columns=["fraud_type"])
    res = detect_impossible_travel("A1", df, sample_cities_df)
    assert res["detected"] is True

def test_26_works_without_campaign_id(sample_cities_df):
    txs = [make_tx("1", "2026-01-01 10:00:00", "A1", "CityA"), make_tx("2", "2026-01-01 10:30:00", "A1", "CityC")]
    df = pd.DataFrame(txs).drop(columns=["campaign_id"])
    res = detect_impossible_travel("A1", df, sample_cities_df)
    assert res["detected"] is True

def test_27_results_unchanged_when_labels_removed(sample_cities_df):
    txs = [make_tx("1", "2026-01-01 10:00:00", "A1", "CityA", is_fraud=1), make_tx("2", "2026-01-01 10:30:00", "A1", "CityC", is_fraud=1)]
    df1 = pd.DataFrame(txs)
    df2 = df1.drop(columns=["isFraud", "fraud_type", "campaign_id"])
    res1 = detect_impossible_travel("A1", df1, sample_cities_df)
    res2 = detect_impossible_travel("A1", df2, sample_cities_df)
    assert res1["score"] == res2["score"]

def test_28_haversine_known_coordinates():
    dist = haversine(0.0, 0.0, 0.0, 1.0)
    assert 110.0 < dist < 112.0

def test_29_zero_distance_movement():
    assert haversine(10.0, 10.0, 10.0, 10.0) == 0.0

def test_30_invalid_latitude():
    assert np.isnan(haversine(95.0, 0.0, 0.0, 0.0))

def test_31_invalid_longitude():
    assert np.isnan(haversine(0.0, 185.0, 0.0, 0.0))

def test_32_antimeridian_handling():
    dist = haversine(0.0, 179.0, 0.0, -179.0)
    assert 220.0 < dist < 225.0

def test_33_very_short_elapsed_time(sample_cities_df):
    txs = [make_tx("1", "2026-01-01 10:00:00", "A1", "CityA"), make_tx("2", "2026-01-01 10:00:01", "A1", "CityC")]
    res = detect_impossible_travel("A1", pd.DataFrame(txs), sample_cities_df)
    assert res["detected"] is True

def test_34_missing_geographic_mapping(sample_cities_df):
    txs = [make_tx("1", "2026-01-01 10:00:00", "A1", "Unknown1"), make_tx("2", "2026-01-01 11:00:00", "A1", "Unknown2")]
    res = detect_impossible_travel("A1", pd.DataFrame(txs), sample_cities_df)
    assert res["detected"] is False

def test_35_score_bounds(sample_cities_df):
    txs = [make_tx("1", "2026-01-01 10:00:00", "A1", "CityA"), make_tx("2", "2026-01-01 10:00:01", "A1", "CityD")]
    res = detect_impossible_travel("A1", pd.DataFrame(txs), sample_cities_df)
    assert 0 <= res["score"] <= 100

def test_36_deterministic_results(sample_cities_df):
    txs = [make_tx("1", "2026-01-01 10:00:00", "A1", "CityA"), make_tx("2", "2026-01-01 10:30:00", "A1", "CityC")]
    res1 = detect_impossible_travel("A1", pd.DataFrame(txs), sample_cities_df)
    res2 = detect_impossible_travel("A1", pd.DataFrame(txs), sample_cities_df)
    assert res1 == res2

def test_37_evidence_references_real_transaction_ids(sample_cities_df):
    txs = [make_tx("1", "2026-01-01 10:00:00", "A1", "CityA"), make_tx("2", "2026-01-01 10:30:00", "A1", "CityC")]
    res = detect_impossible_travel("A1", pd.DataFrame(txs), sample_cities_df)
    assert "1" in res["evidence"][0]["transaction_ids"]

def test_38_missing_data_does_not_generate_high_score(sample_cities_df):
    txs = [make_tx("1", "2026-01-01 10:00:00", "A1", "CityMissing"), make_tx("2", "2026-01-01 10:30:00", "A1", "CityMissing")]
    res = detect_impossible_travel("A1", pd.DataFrame(txs), sample_cities_df)
    assert res["score"] == 0.0

def test_39_suspicious_and_implausible_distinguishable(sample_cities_df):
    txs_susp = [make_tx("1", "2026-01-01 10:00:00", "A1", "CityA"), make_tx("2", "2026-01-01 11:15:00", "A1", "CityC")] 
    res_susp = detect_impossible_travel("A1", pd.DataFrame(txs_susp), sample_cities_df)
    assert res_susp["score"] == 60.0
    
    txs_impl = [make_tx("1", "2026-01-01 10:00:00", "A1", "CityA"), make_tx("2", "2026-01-01 10:30:00", "A1", "CityC")]
    res_impl = detect_impossible_travel("A1", pd.DataFrame(txs_impl), sample_cities_df)
    assert res_impl["score"] == 85.0

def test_40_multiple_suspicious_pairs(sample_cities_df):
    txs = [
        make_tx("1", "2026-01-01 10:00:00", "A1", "CityA"),
        make_tx("2", "2026-01-01 10:30:00", "A1", "CityC"),
        make_tx("3", "2026-01-01 11:00:00", "A1", "CityC"),
        make_tx("4", "2026-01-01 12:00:00", "A1", "CityD") 
    ]
    res = detect_impossible_travel("A1", pd.DataFrame(txs), sample_cities_df)
    assert res["score"] == 85.0
    assert len(res["evidence"]) == 2
