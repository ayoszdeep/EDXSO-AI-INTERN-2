-- Scholarship Intelligence Platform Database Schema

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT UNIQUE NOT NULL,
    provider TEXT,
    source_type TEXT NOT NULL,
    official INTEGER NOT NULL DEFAULT 0,
    root_url TEXT NOT NULL,
    last_checked_at TEXT
);

CREATE TABLE IF NOT EXISTS scholarships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_key TEXT UNIQUE NOT NULL,
    source_id INTEGER,
    name TEXT NOT NULL,
    provider TEXT NOT NULL,
    provider_type TEXT NOT NULL,
    official_source_url TEXT NOT NULL,
    application_url TEXT,
    benefit TEXT,
    eligibility TEXT,
    academic_requirements TEXT,
    education_levels TEXT, -- JSON array of strings
    courses TEXT,          -- JSON array of strings
    income_limit_inr INTEGER,
    age_min INTEGER,
    age_max INTEGER,
    gender_criteria TEXT,
    category_criteria TEXT,
    domicile_criteria TEXT,
    institution_criteria TEXT,
    opening_date TEXT,
    deadline TEXT,
    documents_required TEXT, -- JSON array of strings
    selection_process TEXT,
    renewal_requirements TEXT,
    lifecycle_status TEXT DEFAULT 'REVIEW_REQUIRED', -- ACTIVE, EXPIRING_SOON, EXPIRED, REVIEW_REQUIRED, NO_LONGER_VERIFIABLE
    verification_status TEXT DEFAULT 'REVIEW_REQUIRED', -- VERIFIED, REVIEW_REQUIRED
    confidence_score REAL DEFAULT 0,
    score_breakdown TEXT, -- JSON object
    first_seen_at TEXT,
    last_seen_at TEXT,
    last_verified_at TEXT,
    last_content_hash TEXT,
    FOREIGN KEY(source_id) REFERENCES sources(id)
);

CREATE TABLE IF NOT EXISTS evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scholarship_id INTEGER NOT NULL,
    field_name TEXT NOT NULL,
    extracted_value TEXT,
    source_url TEXT NOT NULL,
    evidence_text TEXT NOT NULL,
    page_number INTEGER,
    snapshot_path TEXT,
    content_hash TEXT,
    fetched_at TEXT NOT NULL,
    extraction_method TEXT, -- RULE_BASED, TABLE, PDF_EXTRACTION, AI_PARSED
    FOREIGN KEY(scholarship_id) REFERENCES scholarships(id)
);

CREATE TABLE IF NOT EXISTS crawl_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT, -- RUNNING, COMPLETED, FAILED
    pages_visited INTEGER DEFAULT 0,
    discovered_count INTEGER DEFAULT 0,
    verified_count INTEGER DEFAULT 0,
    review_count INTEGER DEFAULT 0,
    changes_count INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS change_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scholarship_id INTEGER NOT NULL,
    crawl_run_id INTEGER,
    field_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    detected_at TEXT NOT NULL,
    source_url TEXT,
    old_evidence_id INTEGER,
    new_evidence_id INTEGER,
    FOREIGN KEY(scholarship_id) REFERENCES scholarships(id),
    FOREIGN KEY(crawl_run_id) REFERENCES crawl_runs(id)
);

CREATE TABLE IF NOT EXISTS discovery_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
    domain TEXT NOT NULL,
    discovery_method TEXT, -- SEED, SITEMAP, INTERNAL_LINK, SEARCH, PDF
    classification TEXT DEFAULT 'CANDIDATE', -- OFFICIAL_CANDIDATE, CANDIDATE, AGGREGATOR, REJECTED
    processing_status TEXT DEFAULT 'PENDING', -- PENDING, PROCESSED, FAILED
    discovered_at TEXT,
    last_checked_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_scholarship_status ON scholarships(lifecycle_status);
CREATE INDEX IF NOT EXISTS idx_verification_status ON scholarships(verification_status);
CREATE INDEX IF NOT EXISTS idx_deadline ON scholarships(deadline);
CREATE INDEX IF NOT EXISTS idx_evidence_scholarship ON evidence(scholarship_id);
CREATE INDEX IF NOT EXISTS idx_change_scholarship ON change_history(scholarship_id);
CREATE INDEX IF NOT EXISTS idx_discovery_status ON discovery_candidates(processing_status);
