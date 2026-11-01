# TECHNICAL NOTE: SCHOLARSHIP INTELLIGENCE PLATFORM
### Architecture, Verification Engine, Confidence Scoring & Audit System
**Author:** AI Engineer Intern Candidate  
**Project:** Scholarship Intelligence Crawler (EDXSO Assignment 2)  
**Date:** November 2026  

---

## PAGE 1: PROBLEM, ARCHITECTURE, TECH STACK & DISCOVERY

### 1.1 Problem Statement
Scholarship discovery platforms in India suffer from pervasive data inaccuracy, outdated application cycles, hallucinated eligibility criteria, and broken application links. Commercial aggregators frequently republish stale deadlines or invent requirements to generate web traffic, leaving students misinformed. Furthermore, modern generative AI approaches often hallucinate dates and criteria because LLMs lack direct, traceable evidence linkage.

The goal of this project is to build an automated **Scholarship Intelligence & Verification Platform** that extracts real scholarships from official primary sources, validates every claim with field-level evidence citations, computes a reproducible 100-point confidence score, detects historical mutations across crawl cycles, and presents an auditable inspection interface.

### 1.2 System Architecture
The application is structured into four decoupled layers:
1. **Intelligence Layer:** Discovers candidate URLs via seed traversal, sitemaps, and search; fetches documents with Requests, fallback Playwright headless browser, and PyMuPDF; and stores immutable SHA-256 content snapshots on disk.
2. **Trust & Verification Layer:** Extracts structured Pydantic models with exact quotations, verifies claims against raw snapshot text, validates primary source domain authority, and computes mathematical confidence scores.
3. **Memory & Persistence Layer:** SQLite engine with foreign key enforcement and Write-Ahead Logging (WAL) managing 6 relational tables (`sources`, `scholarships`, `evidence`, `crawl_runs`, `change_history`, and `discovery_candidates`).
4. **Product & Audit Layer:** Streamlit dashboard rendering KPI metrics, multi-attribute filtering, deep-dive evidence inspection, and mutation audit logs.

```
[Web / Official Seed Sources] 
         │
         ▼
[DiscoveryEngine] ──> Classifies Domain & Queues Candidate URLs
         │
         ▼
[PageFetcher & Snapshot Archiver] ──> Saves raw HTML/PDF with SHA-256 hash
         │
         ▼
[DocumentParser & ScholarshipExtractor] ──> Structured Pydantic Record
         │
         ▼
[ScholarshipVerifier & ConfidenceScorer] ──> Quotes Verification & 100-Pt Score
         │
         ▼
[ChangeDetector & ExpiryDetector] ──> Detects Field Shifts & Lifecycle State
         │
         ▼
[SQLite Repository (data/scholarships.db)] ──> Atomic Transactional Storage
         │
         ▼
[Streamlit Interactive Dashboard] ──> Search, Evidence Traceability, History
```

### 1.3 Technology Choices & Tradeoffs
- **Python 3:** Single-language stack unifying web transport, text extraction, data validation, database access, and UI rendering. Eliminates cross-language serialization overhead.
- **SQLite (WAL Mode) vs. MongoDB/PostgreSQL:** SQLite provides embedded zero-configuration execution, inspectable relational integrity, and fast ACID transactions without requiring an external database server daemon.
- **Requests + Playwright Fallback:** Defaulting to lightweight HTTP Requests delivers high throughput (0.5s per page). Playwright is activated only when JavaScript client-side rendering is strictly required.
- **PyMuPDF (fitz):** Fast, high-fidelity PDF text and metadata extraction with per-page tracking for government scheme notifications.
- **Streamlit:** Native Python dashboard enabling instant data reactivity, complex filtering, and detailed audit trails without MERN boilerplate.

### 1.4 Discovery Methodology
The discovery engine (`crawler/discovery.py`) employs a multi-tiered pipeline:
1. **Seed Crawling:** Visits trusted foundational portals (`scholarships.gov.in`, `ugc.gov.in`, `academics.iitd.ac.in`, `scholarships.reliancefoundation.org`, `azimpremjifoundation.org`).
2. **Sitemap Discovery:** Fetches and parses `/sitemap.xml` for keyword patterns (`fellowship`, `scholarship`, `financial-aid`, `scheme`).
3. **Internal Link Traversal:** Follows contextual in-domain links matching scholarship keywords while ignoring non-content anchors.
4. **Search Discovery Adapter:** Executes targeted domain queries (`site:gov.in scholarship scheme`, `site:ac.in financial assistance`) via `duckduckgo_search`.
5. **Source Classification:** Domains are evaluated against a classified source registry (`config/source_registry.json`). Government domains (`.gov.in`, `.nic.in`) and university domains (`.ac.in`, `.edu.in`) receive official candidate status, while commercial aggregators (`buddy4study.com`, `shiksha.com`) are categorized as discovery-only portals.

---

## PAGE 2: EXTRACTION, EVIDENCE VALIDATION & CONFIDENCE SCORING

### 2.1 Extraction Engine
Extraction is handled by `crawler/extractor.py` using layered deterministic parsing:
- **Layer 1: Rule-Based Regular Expressions:** Formats currency strings (`₹50,000`, `Rs. 15 lakh`, `1.5 Lakhs`) into integer INR ceilings; parses messy date strings (`30-11-2026`, `31st October 2026`) into standardized ISO `YYYY-MM-DD`.
- **Layer 2: DOM & Accordion Traversal:** Extracts scheme titles, opening dates, student application deadlines, and verification deadlines from structured portal cards.
- **Layer 3: Pydantic Data Validation:** Enforces strict field typing, list validation (`education_levels`, `courses`), and stable canonical key synthesis (`provider:normalized_name`) for deduplication.

### 2.2 Anti-Hallucination & Evidence Validation
To prevent artificial intelligence hallucinations:
1. **Explicit Null Preservation:** If a provider does not state an income ceiling, benefit amount, or academic percentage, the system stores `None` / `null`. No synthetic default values or LLM guesses are ever inserted.
2. **Field-Level Quotation Tracking:** For every populated claim, an exact verbatim quotation is captured alongside the document URL, PDF page number, and content hash.
3. **Source Verification:** The `ScholarshipVerifier` performs normalized whitespace substring matching:
   $$\text{normalize}(Q) \subseteq \text{normalize}(D)$$
   If an extracted claim's quotation cannot be matched in the archived snapshot, the claim fails validation and is excluded from the verified evidence table.

### 2.3 Mathematical Confidence Scoring (100-Point Formula)
Confidence is calculated as an objective sum across six distinct dimensions:

$$\text{Confidence Score} = S_{\text{auth}} + S_{\text{pres}} + S_{\text{cov}} + S_{\text{ed}} + S_{\text{app}} + S_{\text{fresh}} - P_{\text{conflict}}$$

1. **Official Source Authenticity ($S_{\text{auth}}$, Max 25 pts):**
   - 25 pts: Primary provider domain or endorsed government/university portal (`.gov.in`, `.ac.in`).
   - 15 pts: Authoritative linked external destination.
   - 0 pts: Unverified aggregator or blog.
2. **Page Presence ($S_{\text{pres}}$, Max 15 pts):**
   - 15 pts: Exact scholarship found on active, currently accessible official page.
   - 8 pts: Found in archived document; active cycle unconfirmed.
   - 0 pts: Absent.
3. **Field-Level Evidence Coverage ($S_{\text{cov}}$, Max 25 pts):**
   $$S_{\text{cov}} = 25 \times \frac{\text{Supported Populated Claims}}{\text{Total Populated Claims}}$$
   Unspecified fields are not penalized; populated fields must pass verbatim quotation checks.
4. **Eligibility & Deadline Support ($S_{\text{ed}}$, Max 15 pts):**
   - 15 pts: Both eligibility and deadline backed by primary source quotes.
   - 8 pts: Partial citation.
   - 0 pts: Unsupported.
5. **Application Route Validation ($S_{\text{app}}$, Max 10 pts):**
   - 10 pts: Verified official direct application URL.
   - 5 pts: Hosted within official portal domain.
   - 0 pts: Broken or external unverified link.
6. **Freshness ($S_{\text{fresh}}$, Max 10 pts):**
   - 10 pts: Verified $\le 7$ days ago.
   - 7 pts: Verified 8–30 days ago.
   - 4 pts: Verified 31–90 days ago.
   - 0 pts: Stale ($> 90$ days).
7. **Conflict Penalty ($P_{\text{conflict}}$, -15 pts):**
   Subtracted if conflicting dates or eligibility criteria exist between official circulars.

### 2.4 Strict Hard Verification Gates
A scholarship is designated as `VERIFIED` **if and only if**:
- Confidence Score $\ge 95.0$
- Source is officially verified (`is_official_source == True`)
- Critical evidence (`name`, `provider`, `eligibility`/`deadline`) passes quotation validation.
- No unresolved data conflict exists.
Otherwise, the record is flagged as `REVIEW_REQUIRED`. Aggregator sites are permanently blocked from receiving `VERIFIED` status.

---

## PAGE 3: CHANGE DETECTION, LIFECYCLE, DATABASE & TESTING

### 3.1 Change-Detection Engine
The `ChangeDetector` monitors field-level differences across consecutive crawls:
1. **Tracked Fields:** `deadline`, `benefit`, `eligibility`, `academic_requirements`, `income_limit_inr`, `opening_date`, `selection_process`, and `renewal_requirements`.
2. **Equivalence Normalization:** Prevents false alarms by normalizing equivalent representations:
   - Dates: `31-08-2026`, `2026-08-31`, and `31st August 2026` all normalize to ISO `2026-08-31`.
   - Currency: `Rs. 15 lakh` and `1500000` normalize to integer `1500000`.
   - Text: Strips non-semantic whitespace and casing.
3. **Audit Trail Persistence:** Detected changes insert a record into `change_history` containing `scholarship_id`, `crawl_run_id`, `field_name`, `old_value`, `new_value`, `detected_at`, `source_url`, and foreign-key pointers to new evidence snapshots.
4. **Controlled Replay Mode:** Built-in fixture replay (`scheme_change_v1.html` vs. `scheme_change_v2.html`) demonstrates automated detection of an extended deadline and upgraded benefit without fabricating live portal data.

### 3.2 Expired & Stale Lifecycle Detection
The system decouples data authenticity (`verification_status`) from application window state (`lifecycle_status`):
- **`ACTIVE`:** Confirmed application deadline $\ge \text{today}$.
- **`EXPIRING_SOON`:** Confirmed deadline is within 7 days.
- **`EXPIRED`:** Confirmed application deadline $< \text{today}$.
  - *Observed Live Cases:* Schemes on the National Scholarship Portal where the student application window closed on `2026-10-31` (e.g. *Pre-Matric Scholarship for Students with Disabilities* and *Financial Assistance for Wards of Beedi/Cine Workers*) are recorded as `EXPIRED` while retaining their `VERIFIED` authenticity badge.
- **`NO_LONGER_VERIFIABLE`:** Triggered when a webpage returns 404/500 errors across 3 consecutive crawl cycles, or when an official withdrawal circular is observed.

### 3.3 Database Relational Integrity
The SQLite database (`data/scholarships.db`) utilizes 6 relational tables:
- `sources`: Tracks trusted domains, classifications, and verification status.
- `scholarships`: Central repository indexed on `canonical_key`, `verification_status`, and `deadline`.
- `evidence`: Foreign-key linked to `scholarships(id)`, storing field-level text quotes, snapshot file paths, and SHA-256 hashes.
- `crawl_runs`: Audit log tracking pages visited, discovery counts, and errors per run.
- `change_history`: Foreign-key linked to `scholarships(id)` and `crawl_runs(id)` storing mutations.
- `discovery_candidates`: Candidate URL queue with unique constraints to prevent redundant crawls.

### 3.4 Verification & Acceptance Testing Strategy
The test suite (`pytest`) comprises 25 tests spanning 7 dedicated test modules:
1. `test_discovery.py`: Validates domain classification, aggregator identification, and link deduplication.
2. `test_extraction.py`: Validates date parsing, INR amount conversion, null preservation, and quotation matching.
3. `test_verification.py`: Verifies official domain recognition and aggregator rejection.
4. `test_scoring.py`: Tests the 100-point calculation, hard verification gates, and conflict penalties.
5. `test_changes.py`: Validates field comparison and date format normalization.
6. `test_expiry.py`: Tests lifecycle boundaries (`ACTIVE`, `EXPIRING_SOON`, `EXPIRED`, `NO_LONGER_VERIFIABLE`).
7. `test_database.py`: Validates ACID transaction integrity, upsert logic, and evidence linking.

*Test Execution Result: 25 / 25 Passing (100% pass rate in 0.48s).*

### 3.5 Limitations & Future Work
1. **Dynamic Form Barriers:** Portals requiring user authentication or CAPTCHAs before revealing scheme guidelines cannot be crawled without authorized API credentials.
2. **Multi-Lingual Official Circulars:** State government notices published exclusively in Hindi or regional languages require multi-lingual OCR and translation pipelines.
3. **Document-Level Diffing:** Extending change detection from single structured fields to visual PDF layout diffing for annual gazette notifications.
