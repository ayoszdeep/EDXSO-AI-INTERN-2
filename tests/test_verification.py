"""
Test suite for Verification Engine.
"""
from crawler.verifier import ScholarshipVerifier
from crawler.extractor import ScholarshipRecord


def test_official_source_check():
    verifier = ScholarshipVerifier()
    is_off, is_agg, _ = verifier.is_official_source("https://scholarships.gov.in/All-Scholarships")
    assert is_off is True
    assert is_agg is False

    is_off_uni, is_agg_uni, _ = verifier.is_official_source("https://academics.iitd.ac.in")
    assert is_off_uni is True
    assert is_agg_uni is False


def test_aggregator_cannot_be_verified():
    verifier = ScholarshipVerifier()
    is_off, is_agg, _ = verifier.is_official_source("https://www.buddy4study.com/scholarship")
    assert is_off is False
    assert is_agg is True


def test_verification_status_with_valid_evidence():
    verifier = ScholarshipVerifier()
    source_url = "https://scholarships.gov.in/All-Scholarships"
    source_text = "AICTE - Pragati Scholarship Scheme For Girl Students (Technical Degree) Student Application Open till : 30-11-2026"

    rec = ScholarshipRecord(
        canonical_key="nsp:pragatidegree",
        name="AICTE - Pragati Scholarship Scheme For Girl Students (Technical Degree)",
        provider="AICTE",
        provider_type="GOVERNMENT",
        official_source_url=source_url,
        application_url=source_url,
        eligibility="For Girl Students (Technical Degree)",
        deadline="2026-11-30",
        evidence_map={
            "name": {"quote": "AICTE - Pragati Scholarship Scheme For Girl Students (Technical Degree)", "page": None},
            "provider": {"quote": "AICTE", "page": None},
            "eligibility": {"quote": "For Girl Students (Technical Degree)", "page": None},
            "deadline": {"quote": "Student Application Open till : 30-11-2026", "page": None},
        },
    )

    res = verifier.verify_record(rec, source_text)
    assert res["verification_status"] == "VERIFIED"
    assert res["confidence_score"] >= 95.0
