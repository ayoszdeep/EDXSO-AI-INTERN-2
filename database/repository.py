"""
Repository layer providing CRUD and analytical queries for the Scholarship Intelligence system.
"""
import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from database.db import get_connection


def utc_now_iso() -> str:
    """Return current ISO formatted timestamp in UTC."""
    return datetime.now(timezone.utc).isoformat()


class ScholarshipRepository:
    def __init__(self, conn: Optional[sqlite3.Connection] = None):
        self._external_conn = conn

    def _get_conn(self) -> sqlite3.Connection:
        if self._external_conn:
            return self._external_conn
        return get_connection()

    # --- Sources ---
    def get_source_by_domain(self, domain: str) -> Optional[dict]:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM sources WHERE domain = ?", (domain,)).fetchone()
            return dict(row) if row else None

    def get_all_sources(self) -> List[dict]:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM sources ORDER BY id ASC").fetchall()
            return [dict(r) for r in rows]

    def upsert_source(self, domain: str, provider: str, source_type: str, official: bool, root_url: str) -> int:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO sources (domain, provider, source_type, official, root_url, last_checked_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(domain) DO UPDATE SET
                    provider = excluded.provider,
                    source_type = excluded.source_type,
                    official = excluded.official,
                    root_url = excluded.root_url,
                    last_checked_at = excluded.last_checked_at
                """,
                (domain, provider, source_type, 1 if official else 0, root_url, utc_now_iso()),
            )
            conn.commit()
            row = conn.execute("SELECT id FROM sources WHERE domain = ?", (domain,)).fetchone()
            return row["id"]

    # --- Discovery Candidates ---
    def add_candidate(self, url: str, domain: str, discovery_method: str, classification: str = "CANDIDATE") -> bool:
        with self._get_conn() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO discovery_candidates (url, domain, discovery_method, classification, processing_status, discovered_at)
                    VALUES (?, ?, ?, ?, 'PENDING', ?)
                    ON CONFLICT(url) DO UPDATE SET
                        last_checked_at = excluded.discovered_at
                    """,
                    (url, domain, discovery_method, classification, utc_now_iso()),
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def get_pending_candidates(self, limit: int = 50) -> List[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM discovery_candidates WHERE processing_status = 'PENDING' ORDER BY id ASC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def update_candidate_status(self, candidate_id: int, status: str):
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE discovery_candidates SET processing_status = ?, last_checked_at = ? WHERE id = ?",
                (status, utc_now_iso(), candidate_id),
            )
            conn.commit()

    # --- Crawl Runs ---
    def start_crawl_run(self) -> int:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO crawl_runs (started_at, status) VALUES (?, 'RUNNING')",
                (utc_now_iso(),),
            )
            conn.commit()
            return cursor.lastrowid

    def complete_crawl_run(
        self,
        run_id: int,
        pages_visited: int,
        discovered_count: int,
        verified_count: int,
        review_count: int,
        changes_count: int,
        errors_count: int,
        status: str = "COMPLETED",
    ):
        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE crawl_runs
                SET completed_at = ?,
                    status = ?,
                    pages_visited = ?,
                    discovered_count = ?,
                    verified_count = ?,
                    review_count = ?,
                    changes_count = ?,
                    errors_count = ?
                WHERE id = ?
                """,
                (
                    utc_now_iso(),
                    status,
                    pages_visited,
                    discovered_count,
                    verified_count,
                    review_count,
                    changes_count,
                    errors_count,
                    run_id,
                ),
            )
            conn.commit()

    def get_latest_crawl_run(self) -> Optional[dict]:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM crawl_runs ORDER BY id DESC LIMIT 1").fetchone()
            return dict(row) if row else None

    # --- Scholarships ---
    def get_scholarship_by_canonical_key(self, canonical_key: str) -> Optional[dict]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM scholarships WHERE canonical_key = ?", (canonical_key,)
            ).fetchone()
            return dict(row) if row else None

    def get_scholarship_by_id(self, scholarship_id: int) -> Optional[dict]:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM scholarships WHERE id = ?", (scholarship_id,)).fetchone()
            return dict(row) if row else None

    def get_all_scholarships(
        self,
        search_query: Optional[str] = None,
        provider_type: Optional[str] = None,
        verification_status: Optional[str] = None,
        lifecycle_status: Optional[str] = None,
        min_confidence: Optional[float] = None,
        sort_by: str = "confidence_desc",
    ) -> List[dict]:
        query = "SELECT * FROM scholarships WHERE 1=1"
        params: List[Any] = []

        if search_query:
            query += " AND (name LIKE ? OR provider LIKE ? OR eligibility LIKE ?)"
            term = f"%{search_query.strip()}%"
            params.extend([term, term, term])

        if provider_type and provider_type != "ALL":
            query += " AND provider_type = ?"
            params.append(provider_type)

        if verification_status and verification_status != "ALL":
            query += " AND verification_status = ?"
            params.append(verification_status)

        if lifecycle_status and lifecycle_status != "ALL":
            query += " AND lifecycle_status = ?"
            params.append(lifecycle_status)

        if min_confidence is not None:
            query += " AND confidence_score >= ?"
            params.append(min_confidence)

        if sort_by == "confidence_desc":
            query += " ORDER BY confidence_score DESC, name ASC"
        elif sort_by == "confidence_asc":
            query += " ORDER BY confidence_score ASC"
        elif sort_by == "deadline_asc":
            query += " ORDER BY CASE WHEN deadline IS NULL THEN 1 ELSE 0 END, deadline ASC"
        elif sort_by == "name_asc":
            query += " ORDER BY name ASC"
        else:
            query += " ORDER BY id DESC"

        with self._get_conn() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def upsert_scholarship(self, data: Dict[str, Any]) -> int:
        """Insert or update a scholarship record within a transaction."""
        now = utc_now_iso()
        with self._get_conn() as conn:
            cursor = conn.cursor()
            existing = cursor.execute(
                "SELECT id, first_seen_at FROM scholarships WHERE canonical_key = ?",
                (data["canonical_key"],),
            ).fetchone()

            edu_levels = json.dumps(data.get("education_levels", []))
            courses = json.dumps(data.get("courses", []))
            docs = json.dumps(data.get("documents_required", []))
            score_breakdown = (
                json.dumps(data["score_breakdown"])
                if isinstance(data.get("score_breakdown"), dict)
                else data.get("score_breakdown")
            )

            if existing:
                scholarship_id = existing["id"]
                cursor.execute(
                    """
                    UPDATE scholarships SET
                        source_id = ?,
                        name = ?,
                        provider = ?,
                        provider_type = ?,
                        official_source_url = ?,
                        application_url = ?,
                        benefit = ?,
                        eligibility = ?,
                        academic_requirements = ?,
                        education_levels = ?,
                        courses = ?,
                        income_limit_inr = ?,
                        age_min = ?,
                        age_max = ?,
                        gender_criteria = ?,
                        category_criteria = ?,
                        domicile_criteria = ?,
                        institution_criteria = ?,
                        opening_date = ?,
                        deadline = ?,
                        documents_required = ?,
                        selection_process = ?,
                        renewal_requirements = ?,
                        lifecycle_status = ?,
                        verification_status = ?,
                        confidence_score = ?,
                        score_breakdown = ?,
                        last_seen_at = ?,
                        last_verified_at = ?,
                        last_content_hash = ?
                    WHERE id = ?
                    """,
                    (
                        data.get("source_id"),
                        data["name"],
                        data["provider"],
                        data["provider_type"],
                        data["official_source_url"],
                        data.get("application_url"),
                        data.get("benefit"),
                        data.get("eligibility"),
                        data.get("academic_requirements"),
                        edu_levels,
                        courses,
                        data.get("income_limit_inr"),
                        data.get("age_min"),
                        data.get("age_max"),
                        data.get("gender_criteria"),
                        data.get("category_criteria"),
                        data.get("domicile_criteria"),
                        data.get("institution_criteria"),
                        data.get("opening_date"),
                        data.get("deadline"),
                        docs,
                        data.get("selection_process"),
                        data.get("renewal_requirements"),
                        data.get("lifecycle_status", "REVIEW_REQUIRED"),
                        data.get("verification_status", "REVIEW_REQUIRED"),
                        data.get("confidence_score", 0.0),
                        score_breakdown,
                        now,
                        now if data.get("verification_status") == "VERIFIED" else None,
                        data.get("last_content_hash"),
                        scholarship_id,
                    ),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO scholarships (
                        canonical_key, source_id, name, provider, provider_type,
                        official_source_url, application_url, benefit, eligibility,
                        academic_requirements, education_levels, courses, income_limit_inr,
                        age_min, age_max, gender_criteria, category_criteria,
                        domicile_criteria, institution_criteria, opening_date, deadline,
                        documents_required, selection_process, renewal_requirements,
                        lifecycle_status, verification_status, confidence_score,
                        score_breakdown, first_seen_at, last_seen_at, last_verified_at,
                        last_content_hash
                    ) VALUES (
                        ?, ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?, ?,
                        ?
                    )
                    """,
                    (
                        data["canonical_key"],
                        data.get("source_id"),
                        data["name"],
                        data["provider"],
                        data["provider_type"],
                        data["official_source_url"],
                        data.get("application_url"),
                        data.get("benefit"),
                        data.get("eligibility"),
                        data.get("academic_requirements"),
                        edu_levels,
                        courses,
                        data.get("income_limit_inr"),
                        data.get("age_min"),
                        data.get("age_max"),
                        data.get("gender_criteria"),
                        data.get("category_criteria"),
                        data.get("domicile_criteria"),
                        data.get("institution_criteria"),
                        data.get("opening_date"),
                        data.get("deadline"),
                        docs,
                        data.get("selection_process"),
                        data.get("renewal_requirements"),
                        data.get("lifecycle_status", "REVIEW_REQUIRED"),
                        data.get("verification_status", "REVIEW_REQUIRED"),
                        data.get("confidence_score", 0.0),
                        score_breakdown,
                        now,
                        now,
                        now if data.get("verification_status") == "VERIFIED" else None,
                        data.get("last_content_hash"),
                    ),
                )
                scholarship_id = cursor.lastrowid
            conn.commit()
            return scholarship_id

    # --- Evidence ---
    def add_evidence(
        self,
        scholarship_id: int,
        field_name: str,
        extracted_value: Any,
        source_url: str,
        evidence_text: str,
        page_number: Optional[int] = None,
        snapshot_path: Optional[str] = None,
        content_hash: Optional[str] = None,
        extraction_method: str = "RULE_BASED",
    ) -> int:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO evidence (
                    scholarship_id, field_name, extracted_value, source_url,
                    evidence_text, page_number, snapshot_path, content_hash,
                    fetched_at, extraction_method
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    scholarship_id,
                    field_name,
                    str(extracted_value) if extracted_value is not None else None,
                    source_url,
                    evidence_text,
                    page_number,
                    snapshot_path,
                    content_hash,
                    utc_now_iso(),
                    extraction_method,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def get_evidence_for_scholarship(self, scholarship_id: int) -> List[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM evidence WHERE scholarship_id = ? ORDER BY id ASC",
                (scholarship_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    # --- Change History ---
    def record_change(
        self,
        scholarship_id: int,
        crawl_run_id: Optional[int],
        field_name: str,
        old_value: Any,
        new_value: Any,
        source_url: str,
        old_evidence_id: Optional[int] = None,
        new_evidence_id: Optional[int] = None,
    ) -> int:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO change_history (
                    scholarship_id, crawl_run_id, field_name, old_value,
                    new_value, detected_at, source_url, old_evidence_id, new_evidence_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    scholarship_id,
                    crawl_run_id,
                    field_name,
                    str(old_value) if old_value is not None else None,
                    str(new_value) if new_value is not None else None,
                    utc_now_iso(),
                    source_url,
                    old_evidence_id,
                    new_evidence_id,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def get_changes_for_scholarship(self, scholarship_id: int) -> List[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT c.*, s.name as scholarship_name
                FROM change_history c
                JOIN scholarships s ON c.scholarship_id = s.id
                WHERE c.scholarship_id = ?
                ORDER BY c.detected_at DESC
                """,
                (scholarship_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_all_changes(self, limit: int = 50) -> List[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT c.*, s.name as scholarship_name, s.provider as scholarship_provider
                FROM change_history c
                JOIN scholarships s ON c.scholarship_id = s.id
                ORDER BY c.detected_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    # --- Summary Metrics ---
    def get_metrics(self) -> Dict[str, Any]:
        with self._get_conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM scholarships").fetchone()[0]
            verified = conn.execute("SELECT COUNT(*) FROM scholarships WHERE verification_status = 'VERIFIED'").fetchone()[0]
            review = conn.execute("SELECT COUNT(*) FROM scholarships WHERE verification_status = 'REVIEW_REQUIRED'").fetchone()[0]
            above_95 = conn.execute("SELECT COUNT(*) FROM scholarships WHERE confidence_score >= 95.0").fetchone()[0]
            active = conn.execute("SELECT COUNT(*) FROM scholarships WHERE lifecycle_status = 'ACTIVE'").fetchone()[0]
            expiring_soon = conn.execute("SELECT COUNT(*) FROM scholarships WHERE lifecycle_status = 'EXPIRING_SOON'").fetchone()[0]
            expired = conn.execute("SELECT COUNT(*) FROM scholarships WHERE lifecycle_status = 'EXPIRED'").fetchone()[0]
            sources_count = conn.execute("SELECT COUNT(DISTINCT provider_type) FROM scholarships").fetchone()[0]
            avg_score = conn.execute("SELECT AVG(confidence_score) FROM scholarships").fetchone()[0] or 0.0
            changes_count = conn.execute("SELECT COUNT(*) FROM change_history").fetchone()[0]
            runs_count = conn.execute("SELECT COUNT(*) FROM crawl_runs").fetchone()[0]

            return {
                "total_discovered": total,
                "verified_count": verified,
                "review_required_count": review,
                "above_95_count": above_95,
                "active_count": active,
                "expiring_soon_count": expiring_soon,
                "expired_count": expired,
                "provider_types_count": sources_count,
                "average_confidence": round(avg_score, 1),
                "total_changes": changes_count,
                "total_crawl_runs": runs_count,
            }
