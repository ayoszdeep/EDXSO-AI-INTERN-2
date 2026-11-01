"""
Test suite for Confidence Scoring Module.
"""
from crawler.scorer import ConfidenceScorer


def test_full_confidence_calculation():
    scorer = ConfidenceScorer()
    score, breakdown = scorer.calculate_score(
        is_official_source=True,
        is_aggregator=False,
        is_linked_from_official=False,
        is_present_on_source=True,
        is_older_cycle_document=False,
        supported_claims_count=5,
        total_claims_count=5,
        has_eligibility_evidence=True,
        has_deadline_evidence=True,
        has_verified_app_url=True,
    )
    # 25 (auth) + 15 (presence) + 25 (coverage) + 15 (eligibility/deadline) + 10 (app route) + 10 (freshness) = 100
    assert score == 100.0
    status = scorer.determine_status(score, is_official_source=True, has_critical_evidence=True)
    assert status == "VERIFIED"


def test_aggregator_hard_gate_failure():
    scorer = ConfidenceScorer()
    score, breakdown = scorer.calculate_score(
        is_official_source=False,
        is_aggregator=True,
        is_linked_from_official=False,
        is_present_on_source=True,
        is_older_cycle_document=False,
        supported_claims_count=5,
        total_claims_count=5,
        has_eligibility_evidence=True,
        has_deadline_evidence=True,
        has_verified_app_url=False,
    )
    # Aggregator receives 0 for official authenticity
    status = scorer.determine_status(score, is_official_source=False, has_critical_evidence=True)
    assert status == "REVIEW_REQUIRED"


def test_conflict_penalty():
    scorer = ConfidenceScorer()
    score, breakdown = scorer.calculate_score(
        is_official_source=True,
        is_aggregator=False,
        is_linked_from_official=False,
        is_present_on_source=True,
        is_older_cycle_document=False,
        supported_claims_count=5,
        total_claims_count=5,
        has_eligibility_evidence=True,
        has_deadline_evidence=True,
        has_verified_app_url=True,
        has_unresolved_conflict=True,
    )
    assert score == 85.0  # 100 - 15 penalty
    status = scorer.determine_status(score, is_official_source=True, has_critical_evidence=True, has_unresolved_conflict=True)
    assert status == "REVIEW_REQUIRED"
