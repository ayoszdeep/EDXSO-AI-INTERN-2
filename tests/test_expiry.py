"""
Test suite for Expiry and Stale Lifecycle Detection Module.
"""
from datetime import date, timedelta
from crawler.expiry_detector import ExpiryDetector


def test_deadline_expired():
    detector = ExpiryDetector()
    today = date(2026, 11, 1)
    past_deadline = "2026-10-31"  # yesterday
    status = detector.check_expiry(past_deadline, today=today)
    assert status == "EXPIRED"


def test_deadline_expiring_soon():
    detector = ExpiryDetector()
    today = date(2026, 11, 1)
    near_deadline = "2026-11-05"  # 4 days away
    status = detector.check_expiry(near_deadline, today=today)
    assert status == "EXPIRING_SOON"


def test_deadline_active():
    detector = ExpiryDetector()
    today = date(2026, 11, 1)
    future_deadline = "2026-11-30"  # 29 days away
    status = detector.check_expiry(future_deadline, today=today)
    assert status == "ACTIVE"


def test_missing_deadline():
    detector = ExpiryDetector()
    status = detector.check_expiry(None)
    assert status == "REVIEW_REQUIRED"


def test_removal_and_failure_handling():
    detector = ExpiryDetector()
    assert detector.evaluate_removal(consecutive_fetch_failures=1) == "REVIEW_REQUIRED"
    assert detector.evaluate_removal(consecutive_fetch_failures=3) == "NO_LONGER_VERIFIABLE"
    assert detector.evaluate_removal(consecutive_fetch_failures=1, is_officially_withdrawn=True) == "NO_LONGER_VERIFIABLE"
