"""
Unit & Integration Tests for VIGIL Detector Adapter (tests/test_detector_adapter.py)
Verifies schema compliance, pattern translation, non-fabrication of evidence, and safety constraints.
"""

import copy
import pandas as pd
import pytest

from backend.adapters.detector_adapter import (
    VIGIL_PATTERNS,
    adapt_detector_result_to_vigil_pattern,
    evaluate_all_seven_vigil_patterns,
    map_detector_score_to_confidence,
)
from backend.fraud_patterns.aggregator import run_all_detectors
from schemas.evidence import EvidenceItem
from schemas.investigation import (
    FraudPatternResult,
    GraphAnalysisResult,
    InvestigationState,
)
from schemas.transaction import MLPrediction, Transaction


def test_map_detector_score_to_confidence():
    """Verifies numeric scale mapping from 0-100 to 0.0-1.0."""
    assert map_detector_score_to_confidence(0.0) == 0.0
    assert map_detector_score_to_confidence(50.0) == 0.5
    assert map_detector_score_to_confidence(100.0) == 1.0
    assert map_detector_score_to_confidence(85.5) == 0.855
    assert map_detector_score_to_confidence(-10) == 0.0
    assert map_detector_score_to_confidence(150) == 1.0
    assert map_detector_score_to_confidence(True) == 0.0


def test_adapt_single_detector_result_card_testing():
    """Verifies mapping of a valid Card Testing detector output."""
    raw_res = {
        "pattern_name": "CARD_TESTING",
        "detected": True,
        "score": 85.0,
        "severity": "HIGH",
        "evidence": ["5 small transactions within 60s"],
        "entities": {"devices": ["D101"]},
        "transactions": ["TX101", "TX102"],
        "metrics": {"small_tx_count": 5},
        "explanation": "Rapid small amount burst detected.",
    }
    raw_res_copy = copy.deepcopy(raw_res)

    pat_res, ev_items = adapt_detector_result_to_vigil_pattern("CARD_TESTING", raw_res)

    # Immutability check
    assert raw_res == raw_res_copy

    # FraudPatternResult assertion
    assert isinstance(pat_res, FraudPatternResult)
    assert pat_res.pattern_name == "Card Testing"
    assert pat_res.detected is True
    assert pat_res.confidence == 0.85
    assert "RULE_CARD_TESTING_HIGH" in pat_res.matched_rules

    # EvidenceItem assertion
    assert len(ev_items) == 1
    ev = ev_items[0]
    assert isinstance(ev, EvidenceItem)
    assert ev.signal_type == "CARD_TESTING"
    assert ev.category == "INDICATOR"
    assert ev.weight == 0.85
    assert ev.source == "fraud_rules"


def test_skipped_and_errored_detectors_emit_no_counter_evidence():
    """Verifies that missing data or errors do NOT create false counter-evidence."""
    raw_res_skipped = {
        "pattern_name": "IMPOSSIBLE_TRAVEL",
        "detected": False,
        "score": 0.0,
        "severity": "NONE",
        "evidence": [],
        "entities": {},
        "transactions": [],
        "metrics": {},
        "explanation": "No city data available",
    }

    _, ev_items = adapt_detector_result_to_vigil_pattern(
        "IMPOSSIBLE_TRAVEL",
        raw_res_skipped,
        execution_status="SKIPPED_MISSING_DATA",
    )

    # Must NOT generate counter-evidence (proof of innocence) on missing data
    assert len(ev_items) == 0


def test_all_seven_vigil_patterns_represented():
    """Verifies that all seven authoritative VIGIL patterns exist in InvestigationState."""
    stage_8c_out = {
        "account_id": "ACC_101",
        "overall_score": 65.0,
        "detector_results": {
            "CARD_TESTING": {
                "pattern_name": "CARD_TESTING",
                "detected": True,
                "score": 65.0,
                "severity": "MEDIUM",
                "evidence": ["Test evidence"],
                "entities": {},
                "transactions": ["TX1"],
                "metrics": {},
                "explanation": "Card testing detected.",
            }
        },
        "execution_status": {"CARD_TESTING": "SUCCESS_FLAGGED"},
    }

    state = evaluate_all_seven_vigil_patterns("ACC_101", stage_8c_out)

    assert isinstance(state, InvestigationState)
    assert len(state.patterns_detected) == 7

    pattern_names = [p.pattern_name for p in state.patterns_detected]
    for expected_p in VIGIL_PATTERNS:
        assert expected_p in pattern_names


def test_synthetic_identity_and_push_payment_scam_not_fabricated():
    """Verifies that missing data for Synthetic Identity & Push Payment Scam produces un-evaluable status."""
    stage_8c_out = {"account_id": "ACC_102", "overall_score": 0.0, "detector_results": {}}
    state = evaluate_all_seven_vigil_patterns("ACC_102", stage_8c_out)

    p_map = {p.pattern_name: p for p in state.patterns_detected}

    # Synthetic Identity
    synth_p = p_map["Synthetic Identity Fraud"]
    assert synth_p.detected is False
    assert synth_p.confidence == 0.0
    assert synth_p.details.get("status") == "NOT_EVALUABLE_MISSING_DATA"

    # Push Payment Scam
    scam_p = p_map["Push Payment Scam"]
    assert scam_p.detected is False
    assert scam_p.confidence == 0.0
    assert scam_p.details.get("status") == "NOT_EVALUABLE_MISSING_DATA"


def test_device_syndicate_handling_with_and_without_graph():
    """Verifies Device Syndicate alone does NOT establish a Coordinated Fraud Ring without graph confirmation."""
    stage_8c_out = {
        "account_id": "ACC_103",
        "overall_score": 70.0,
        "detector_results": {
            "DEVICE_SYNDICATE": {
                "pattern_name": "DEVICE_SYNDICATE",
                "detected": True,
                "score": 70.0,
                "severity": "HIGH",
                "evidence": ["Device D1 shared across 4 accounts"],
                "entities": {"devices": ["D1"]},
                "transactions": ["TX9"],
                "metrics": {"shared_accounts": 4},
                "explanation": "Device sharing detected.",
            }
        },
        "execution_status": {"DEVICE_SYNDICATE": "SUCCESS_FLAGGED"},
    }

    # 1. Without Graph Result -> Coordinated Fraud Ring MUST NOT be declared True
    state_no_graph = evaluate_all_seven_vigil_patterns("ACC_103", stage_8c_out)
    p_map_no_graph = {p.pattern_name: p for p in state_no_graph.patterns_detected}

    ring_p = p_map_no_graph["Coordinated Fraud Ring"]
    assert ring_p.detected is False
    assert ring_p.confidence == 0.0
    assert ring_p.details.get("status") == "PENDING_GRAPH_ENGINE"

    # 2. With Graph Result -> Coordinated Fraud Ring IS declared True via graph member match
    graph_res = GraphAnalysisResult(
        account_id="ACC_103",
        is_ring_member=True,
        ring_id="RING_99",
        hub_score=0.91,
    )
    state_graph = evaluate_all_seven_vigil_patterns("ACC_103", stage_8c_out, graph_result=graph_res)
    p_map_graph = {p.pattern_name: p for p in state_graph.patterns_detected}

    ring_p_graph = p_map_graph["Coordinated Fraud Ring"]
    assert ring_p_graph.detected is True
    assert ring_p_graph.confidence == 0.91
    assert ring_p_graph.details.get("graph_result", {}).get("ring_id") == "RING_99"


def test_end_to_end_stage_8c_aggregator_integration():
    """Integration test combining run_all_detectors with evaluate_all_seven_vigil_patterns."""
    tx_df = pd.DataFrame(
        [
            {
                "transaction_id": "TX_E2E_1",
                "account_id": "ACC_E2E",
                "timestamp": "2026-10-09 10:00:00",
                "amount": 10.0,
                "device_id": "DEV_E2E",
                "ip": "1.1.1.1",
            },
            {
                "transaction_id": "TX_E2E_2",
                "account_id": "ACC_E2E",
                "timestamp": "2026-10-09 10:00:30",
                "amount": 12.0,
                "device_id": "DEV_E2E",
                "ip": "1.1.1.1",
            },
        ]
    )

    stage_8c_res = run_all_detectors(
        account_id="ACC_E2E",
        transactions_df=tx_df,
        as_of_timestamp="2026-10-09 10:05:00",
    )

    tx_obj = Transaction(
        transaction_id="TX_E2E_1",
        timestamp="2026-10-09T10:00:00Z",
        account_id="ACC_E2E",
        amount=10.0,
        device_id="DEV_E2E",
        ip="1.1.1.1",
    )

    investigation_state = evaluate_all_seven_vigil_patterns(
        account_id="ACC_E2E",
        stage_8c_output=stage_8c_res,
        transaction=tx_obj,
    )

    assert isinstance(investigation_state, InvestigationState)
    assert investigation_state.case_id == "CASE_TX_E2E_1"
    assert investigation_state.transaction.account_id == "ACC_E2E"
    assert 0.0 <= investigation_state.risk_score <= 100.0
    assert investigation_state.recommended_action in ["APPROVE", "HOLD", "ESCALATE", "BLOCK"]
