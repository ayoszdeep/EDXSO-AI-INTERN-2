"""
Test suite for Change Detection Engine.
"""
from crawler.change_detector import ChangeDetector, normalize_field_value


def test_normalize_date_equivalence():
    assert normalize_field_value("deadline", "31-08-2026") == "2026-08-31"
    assert normalize_field_value("deadline", "2026-08-31") == "2026-08-31"
    assert normalize_field_value("deadline", "31st August 2026") == "2026-08-31"


def test_detect_deadline_and_benefit_changes():
    detector = ChangeDetector()
    old_record = {
        "deadline": "2026-08-31",
        "benefit": "Grant of INR 50,000",
        "eligibility": "Class 12 with 60%",
    }
    new_record = {
        "deadline": "2026-09-15",
        "benefit": "Grant of INR 75,000",
        "eligibility": "Class 12 with 60%",
    }
    changes = detector.detect_changes(old_record, new_record)
    assert len(changes) == 2
    changed_fields = {ch["field_name"] for ch in changes}
    assert "deadline" in changed_fields
    assert "benefit" in changed_fields


def test_no_false_positive_on_equivalent_date_format():
    detector = ChangeDetector()
    old_record = {"deadline": "2026-08-31"}
    new_record = {"deadline": "31-08-2026"}
    changes = detector.detect_changes(old_record, new_record)
    assert len(changes) == 0
