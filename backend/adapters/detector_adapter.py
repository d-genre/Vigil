"""
VIGIL Detector Adapter (backend/adapters/detector_adapter.py)

Maps FRAUD_RING Stage 8B/8C detector signals to authoritative VIGIL contracts:
- FraudPatternResult (schemas/investigation.py)
- EvidenceItem (schemas/evidence.py)
- InvestigationState (schemas/investigation.py)

Enforces strict correctness rules:
1. Missing data, skipped detectors, and execution errors NEVER become counter-evidence.
2. Device Syndicate alone NEVER establishes a Coordinated Fraud Ring without positive graph evidence.
3. Beneficiary / Account Takeover requires explicit beneficiary-change or target payload evidence.
4. Synthetic Identity Fraud and Push Payment Scam are marked unevaluable when supporting data is absent.
5. Heuristic scores are scale-normalized without claiming calibrated probabilities.
"""

import copy
import hashlib
import logging
from typing import Any, Dict, List, Optional, Tuple

from schemas.evidence import EvidenceItem
from schemas.investigation import (
    FraudPatternResult,
    GraphAnalysisResult,
    InvestigationState,
)
from schemas.transaction import MLPrediction, Transaction

logger = logging.getLogger(__name__)

# Authoritative VIGIL Finalized 7 Fraud Pattern Names
VIGIL_PATTERNS = [
    "Card Testing",
    "Account Takeover (ATO)",
    "Mule Account Chain",
    "Synthetic Identity Fraud",
    "Push Payment Scam",
    "Beneficiary / Account Takeover",
    "Coordinated Fraud Ring",
]


def map_detector_score_to_confidence(score: float) -> float:
    """
    Normalizes a 0-100 detector heuristic score to a 0.0-1.0 confidence float.
    Does not alter scoring rank or semantics.
    """
    if not isinstance(score, (int, float)) or isinstance(score, bool):
        return 0.0
    return float(round(max(0.0, min(1.0, float(score) / 100.0)), 4))


def _generate_evidence_id(signal_type: str, seed_str: str) -> str:
    """Generates a deterministic evidence identifier matching VIGIL conventions."""
    clean_seed = str(seed_str or "generic").strip()
    hash_digest = hashlib.md5(f"{signal_type}:{clean_seed}".encode("utf-8")).hexdigest()[:6].upper()
    return f"EV_{signal_type.upper()}_{hash_digest}"


def adapt_detector_result_to_vigil_pattern(
    detector_name: str,
    raw_result: Dict[str, Any],
    execution_status: Optional[str] = None
) -> Tuple[Optional[FraudPatternResult], List[EvidenceItem]]:
    """
    Translates a single Stage 8B raw detector output into VIGIL schemas.

    Returns:
    - FraudPatternResult (or None if detector is purely a supporting signal)
    - List[EvidenceItem] (structured risk indicators or counter-evidence)
    """
    if not isinstance(raw_result, dict):
        return None, []

    # Deepcopy to guarantee strict immutability of raw detector output
    res = copy.deepcopy(raw_result)

    detected = bool(res.get("detected", False))
    raw_score = res.get("score", 0.0)
    confidence = map_detector_score_to_confidence(raw_score)
    severity = str(res.get("severity", "NONE"))
    evidence_strings = res.get("evidence", [])
    if not isinstance(evidence_strings, list):
        evidence_strings = []
    entities = res.get("entities", {})
    metrics = res.get("metrics", {})
    transactions = res.get("transactions", [])
    explanation = str(res.get("explanation", ""))

    matched_rules = [f"RULE_{detector_name}_{severity}"]
    if evidence_strings:
        matched_rules.extend([str(e) for e in evidence_strings[:3]])

    details = {
        "source_detector": detector_name,
        "raw_score": raw_score,
        "severity": severity,
        "entities": entities,
        "metrics": metrics,
        "transactions": transactions,
        "explanation": explanation,
    }

    # Map detector to primary VIGIL pattern name
    primary_pattern = None
    if detector_name == "CARD_TESTING":
        primary_pattern = "Card Testing"
    elif detector_name == "ACCOUNT_TAKEOVER":
        primary_pattern = "Account Takeover (ATO)"
    elif detector_name == "MULE_CHAIN":
        primary_pattern = "Mule Account Chain"

    pattern_result = None
    if primary_pattern:
        pattern_result = FraudPatternResult(
            pattern_name=primary_pattern,
            detected=detected,
            confidence=confidence,
            matched_rules=matched_rules,
            details=details,
        )

    # Generate structured EvidenceItems
    evidence_items = []
    first_tx = transactions[0] if transactions else "NO_TX"
    ev_id = _generate_evidence_id(detector_name, first_tx)

    # Correctness constraint: Only emit COUNTER_EVIDENCE if execution succeeded cleanly on actual data.
    # Missing data or execution errors must NEVER become counter-evidence (proof of innocence).
    status = execution_status or res.get("status")
    if not status:
        status = "SUCCESS_FLAGGED" if detected else "SUCCESS_CLEAN"

    if detected:
        ev_item = EvidenceItem(
            evidence_id=ev_id,
            signal_type=detector_name,
            category="INDICATOR",
            description=explanation if explanation else f"{detector_name} flagged risk signal.",
            weight=confidence,
            source="fraud_rules",
            metadata={
                "raw_score": raw_score,
                "severity": severity,
                "flagged_transactions": transactions,
                "entities": entities,
            },
        )
        evidence_items.append(ev_item)
    elif status in ("SUCCESS_CLEAN", "SUCCESS"):
        ev_item = EvidenceItem(
            evidence_id=ev_id,
            signal_type=detector_name,
            category="COUNTER_EVIDENCE",
            description=explanation if explanation else f"{detector_name} completed clean evaluation.",
            weight=round(1.0 - confidence, 4),
            source="fraud_rules",
            metadata={
                "raw_score": raw_score,
                "severity": severity,
                "flagged_transactions": transactions,
                "entities": entities,
            },
        )
        evidence_items.append(ev_item)
    # If status is SKIPPED_MISSING_DATA or ERROR, no counter-evidence item is generated.

    return pattern_result, evidence_items


def evaluate_all_seven_vigil_patterns(
    account_id: str,
    stage_8c_output: Dict[str, Any],
    transaction: Optional[Transaction] = None,
    graph_result: Optional[GraphAnalysisResult] = None,
    ml_screening: Optional[MLPrediction] = None,
) -> InvestigationState:
    """
    Combines Stage 8C detector outputs and VIGIL graph/ML findings into an
    authoritative VIGIL InvestigationState object evaluating all 7 patterns.
    """
    detector_results = stage_8c_output.get("detector_results", {})
    execution_statuses = stage_8c_output.get("execution_status", {})
    if not isinstance(detector_results, dict):
        detector_results = {}
    if not isinstance(execution_statuses, dict):
        execution_statuses = {}

    collected_evidences: List[EvidenceItem] = []
    collected_counter_evidences: List[EvidenceItem] = []
    pattern_results_map: Dict[str, FraudPatternResult] = {}

    # 1. Process standard Stage 8B detector outputs
    for det_name, raw_res in detector_results.items():
        status = execution_statuses.get(det_name)
        pat_res, ev_items = adapt_detector_result_to_vigil_pattern(det_name, raw_res, execution_status=status)
        if pat_res:
            pattern_results_map[pat_res.pattern_name] = pat_res

        for ev in ev_items:
            if ev.category == "INDICATOR":
                collected_evidences.append(ev)
            else:
                collected_counter_evidences.append(ev)

    # 2. Evaluate Card Testing
    if "Card Testing" not in pattern_results_map:
        card_res = detector_results.get("CARD_TESTING", {})
        det = bool(card_res.get("detected", False))
        conf = map_detector_score_to_confidence(card_res.get("score", 0.0))
        pattern_results_map["Card Testing"] = FraudPatternResult(
            pattern_name="Card Testing",
            detected=det,
            confidence=conf,
            matched_rules=["CARD_TESTING_EVALUATION"] if det else [],
            details=card_res if isinstance(card_res, dict) else {},
        )

    # 3. Evaluate Account Takeover (ATO)
    if "Account Takeover (ATO)" not in pattern_results_map:
        ato_res = detector_results.get("ACCOUNT_TAKEOVER", {})
        travel_res = detector_results.get("IMPOSSIBLE_TRAVEL", {})
        det = bool(ato_res.get("detected", False) or travel_res.get("detected", False))
        max_score = max(ato_res.get("score", 0.0), travel_res.get("score", 0.0))
        conf = map_detector_score_to_confidence(max_score)
        pattern_results_map["Account Takeover (ATO)"] = FraudPatternResult(
            pattern_name="Account Takeover (ATO)",
            detected=det,
            confidence=conf,
            matched_rules=["ATO_EVALUATION"] if det else [],
            details={"ato": ato_res, "impossible_travel": travel_res},
        )

    # 4. Evaluate Mule Account Chain
    if "Mule Account Chain" not in pattern_results_map:
        mule_res = detector_results.get("MULE_CHAIN", {})
        drain_res = detector_results.get("RAPID_DRAIN", {})
        det = bool(mule_res.get("detected", False))
        conf = map_detector_score_to_confidence(mule_res.get("score", 0.0))
        pattern_results_map["Mule Account Chain"] = FraudPatternResult(
            pattern_name="Mule Account Chain",
            detected=det,
            confidence=conf,
            matched_rules=["MULE_CHAIN_EVALUATION"] if det else [],
            details={"mule": mule_res, "rapid_drain": drain_res},
        )

    # 5. Evaluate Synthetic Identity Fraud (Missing data handling)
    pattern_results_map["Synthetic Identity Fraud"] = FraudPatternResult(
        pattern_name="Synthetic Identity Fraud",
        detected=False,
        confidence=0.0,
        matched_rules=[],
        details={
            "status": "NOT_EVALUABLE_MISSING_DATA",
            "reason": "No identity attribute or credit profile dataset available for evaluation.",
        },
    )

    # 6. Evaluate Push Payment Scam (Missing data handling)
    pattern_results_map["Push Payment Scam"] = FraudPatternResult(
        pattern_name="Push Payment Scam",
        detected=False,
        confidence=0.0,
        matched_rules=[],
        details={
            "status": "NOT_EVALUABLE_MISSING_DATA",
            "reason": "No push payment scam deception evidence available; velocity alone is insufficient to infer deception.",
        },
    )

    # 7. Evaluate Beneficiary / Account Takeover
    ato_res = detector_results.get("ACCOUNT_TAKEOVER", {})
    drain_res = detector_results.get("RAPID_DRAIN", {})
    ben_id = transaction.beneficiary_id if transaction else None
    has_beneficiary_payload = bool(ben_id or "beneficiaries" in ato_res.get("entities", {}))

    ben_detected = bool(has_beneficiary_payload and ato_res.get("detected", False) and drain_res.get("detected", False))
    ben_conf = map_detector_score_to_confidence(min(ato_res.get("score", 0.0), drain_res.get("score", 0.0))) if ben_detected else 0.0

    pattern_results_map["Beneficiary / Account Takeover"] = FraudPatternResult(
        pattern_name="Beneficiary / Account Takeover",
        detected=ben_detected,
        confidence=ben_conf,
        matched_rules=["BENEFICIARY_TAKEOVER_RULE"] if ben_detected else [],
        details={
            "status": "EVALUATED" if ben_detected else "NOT_EVALUABLE_MISSING_DATA",
            "reason": "Evaluated with beneficiary payload, ATO, and Rapid Drain indicators." if ben_detected else "No beneficiary modification or target beneficiary payload present.",
        },
    )

    # 8. Evaluate Coordinated Fraud Ring (Device Syndicate + Graph)
    # Device Syndicate alone MUST NOT establish a Coordinated Fraud Ring without positive graph evidence.
    ds_res = detector_results.get("DEVICE_SYNDICATE", {})
    ds_detected = bool(ds_res.get("detected", False))
    ring_detected = False
    ring_conf = 0.0

    if graph_result and graph_result.is_ring_member:
        ring_detected = True
        ring_conf = max(0.75, graph_result.hub_score)
    else:
        # Device Syndicate alone cannot establish a Coordinated Fraud Ring without graph confirmation
        ring_detected = False
        ring_conf = 0.0

    pattern_results_map["Coordinated Fraud Ring"] = FraudPatternResult(
        pattern_name="Coordinated Fraud Ring",
        detected=ring_detected,
        confidence=ring_conf,
        matched_rules=["GRAPH_RING_MEMBER"] if ring_detected else [],
        details={
            "device_syndicate": ds_res,
            "graph_result": graph_result.model_dump() if graph_result else None,
            "status": "EVALUATED" if ring_detected else ("PENDING_GRAPH_ENGINE" if ds_detected else "CLEAN"),
            "note": "Device Syndicate provides shared-device evidence signal. Full Coordinated Fraud Ring requires NetworkX graph ring member confirmation.",
        },
    )

    # 9. Extract overall score from Stage 8C aggregator output (overlap-aware)
    overall_score = float(stage_8c_output.get("overall_score", 0.0))

    # Derive recommended action based on authoritative VIGIL risk tiers
    if overall_score >= 80.0:
        recommended_action = "BLOCK"
    elif overall_score >= 50.0:
        recommended_action = "ESCALATE"
    elif overall_score >= 25.0:
        recommended_action = "HOLD"
    else:
        recommended_action = "APPROVE"

    status = "PENDING_REVIEW" if overall_score >= 25.0 else "RESOLVED"

    # Default transaction placeholder if not provided
    if transaction is None:
        transaction = Transaction(
            transaction_id=f"TX_{account_id}_01",
            timestamp="2026-10-09T10:00:00Z",
            account_id=account_id,
            amount=0.0,
        )

    case_id = f"CASE_{transaction.transaction_id}"

    # Construct final VIGIL InvestigationState
    return InvestigationState(
        case_id=case_id,
        transaction=transaction,
        ml_screening=ml_screening,
        patterns_detected=[pattern_results_map[p] for p in VIGIL_PATTERNS],
        graph_result=graph_result,
        evidences=collected_evidences,
        counter_evidences=collected_counter_evidences,
        similar_attacks=[],
        risk_score=overall_score,
        llm_summary=f"Investigation completed for account {account_id}. Overall risk score: {overall_score:.1f}.",
        recommended_action=recommended_action,
        status=status,
    )
