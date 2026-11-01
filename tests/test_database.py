"""
Test suite for SQLite Database and Repository Layer.
"""
import sqlite3
from pathlib import Path
import pytest
from database.db import initialize_database, get_connection
from database.repository import ScholarshipRepository


@pytest.fixture
def test_repo(tmp_path):
    test_db = tmp_path / "test_scholarships.db"
    initialize_database(db_path=test_db, recreate=True)
    conn = get_connection(test_db)
    repo = ScholarshipRepository(conn=conn)
    yield repo
    conn.close()


def test_upsert_and_retrieve_scholarship(test_repo):
    data = {
        "canonical_key": "test:schemex",
        "name": "Scheme X",
        "provider": "Ministry of Education",
        "provider_type": "GOVERNMENT",
        "official_source_url": "https://scholarships.gov.in/test",
        "deadline": "2026-11-30",
        "confidence_score": 98.0,
        "verification_status": "VERIFIED",
        "lifecycle_status": "ACTIVE",
    }
    sch_id = test_repo.upsert_scholarship(data)
    assert sch_id > 0

    fetched = test_repo.get_scholarship_by_id(sch_id)
    assert fetched["name"] == "Scheme X"
    assert fetched["confidence_score"] == 98.0

    # Upsert with updated score
    data["confidence_score"] = 99.5
    updated_id = test_repo.upsert_scholarship(data)
    assert updated_id == sch_id
    updated = test_repo.get_scholarship_by_id(sch_id)
    assert updated["confidence_score"] == 99.5


def test_evidence_and_change_history(test_repo):
    run_id = test_repo.start_crawl_run()
    sch_id = test_repo.upsert_scholarship({
        "canonical_key": "test:change_rec",
        "name": "Change Scheme",
        "provider": "Test Org",
        "provider_type": "GOVERNMENT",
        "official_source_url": "https://gov.in",
        "deadline": "2026-08-31",
    })

    ev_id = test_repo.add_evidence(
        scholarship_id=sch_id,
        field_name="deadline",
        extracted_value="2026-08-31",
        source_url="https://gov.in",
        evidence_text="open till: 31-08-2026",
    )
    assert ev_id > 0

    ch_id = test_repo.record_change(
        scholarship_id=sch_id,
        crawl_run_id=run_id,
        field_name="deadline",
        old_value="2026-08-31",
        new_value="2026-09-15",
        source_url="https://gov.in",
        new_evidence_id=ev_id,
    )
    assert ch_id > 0

    changes = test_repo.get_changes_for_scholarship(sch_id)
    assert len(changes) == 1
    assert changes[0]["old_value"] == "2026-08-31"
    assert changes[0]["new_value"] == "2026-09-15"
