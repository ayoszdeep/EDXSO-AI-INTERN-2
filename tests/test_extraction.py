"""
Test suite for Extraction Engine.
"""
from crawler.extractor import (
    ScholarshipExtractor,
    parse_date,
    parse_inr_amount,
    validate_evidence,
    normalize_text,
)


def test_parse_date():
    assert parse_date("30-11-2026") == "2026-11-30"
    assert parse_date("31st October 2026") == "2026-10-31"
    assert parse_date("15 September 2026") == "2026-09-15"
    assert parse_date("2026-08-31") == "2026-08-31"
    assert parse_date(None) is None


def test_parse_inr_amount():
    assert parse_inr_amount("household income below Rs. 15 lakh") == 1500000
    assert parse_inr_amount("annual family income not exceeding Rs. 4.5 Lakhs") == 450000
    assert parse_inr_amount("grant of ₹50,000 per annum") == 50000
    assert parse_inr_amount("income criteria not specified") is None


def test_validate_evidence_direct_and_normalized():
    source_text = "The Reliance Foundation Undergraduate Scholarship is open till 30-11-2026 for eligible students."
    assert validate_evidence(source_text, "open till 30-11-2026") is True
    assert validate_evidence(source_text, "Reliance Foundation Undergraduate Scholarship") is True
    assert validate_evidence(source_text, "family income below 2 lakh") is False


def test_missing_fields_preserved_as_none():
    extractor = ScholarshipExtractor()
    sample_text = """
    Merit-cum-Means Scholarships
    The Institute offers Merit-cum-Means scholarships to undergraduate students in engineering.
    """
    records = extractor.extract_from_text(
        sample_text,
        "https://academics.iitd.ac.in",
        "IIT Delhi",
        "UNIVERSITY",
    )
    assert len(records) >= 1
    rec = records[0]
    # Income limit was not in text, must be None!
    assert rec.income_limit_inr is None
