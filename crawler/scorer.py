"""
Confidence Scoring Module.
Calculates a 100-point reproducible confidence score with exact point breakdowns and explanations.
"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from config.settings import CONFIDENCE_VERIFIED_THRESHOLD


class ConfidenceScorer:
    """
    100-Point Scoring Breakdown:
    A. Official source authenticity: 25 pts
    B. Scholarship presence on official source: 15 pts
    C. Field-level evidence coverage: 25 pts
    D. Eligibility and deadline support: 15 pts
    E. Application route validation: 10 pts
    F. Information freshness: 10 pts
    Conflict penalty: -15 pts
    """

    def calculate_score(
        self,
        is_official_source: bool,
        is_aggregator: bool,
        is_linked_from_official: bool,
        is_present_on_source: bool,
        is_older_cycle_document: bool,
        supported_claims_count: int,
        total_claims_count: int,
        has_eligibility_evidence: bool,
        has_deadline_evidence: bool,
        has_verified_app_url: bool,
        last_verified_at: Optional[str] = None,
        has_unresolved_conflict: bool = False,
    ) -> Tuple[float, Dict[str, Any]]:
        breakdown = {}

        # A. Official Source Authenticity (Max 25)
        if is_official_source and not is_aggregator:
            src_score = 25.0
            src_reason = "Provider-owned official website or endorsed government portal"
        elif is_linked_from_official and not is_aggregator:
            src_score = 15.0
            src_reason = "Linked from authoritative government/provider source"
        else:
            src_score = 0.0
            src_reason = "Aggregator or unverified external source"
        breakdown["official_source"] = {"score": src_score, "max": 25, "reason": src_reason}

        # B. Scholarship Presence (Max 15)
        if is_present_on_source:
            pres_score = 15.0
            pres_reason = "Scholarship confirmed present on active official document/page"
        elif is_older_cycle_document:
            pres_score = 8.0
            pres_reason = "Located in older official document; current cycle unconfirmed"
        else:
            pres_score = 0.0
            pres_reason = "No direct scholarship presence on source"
        breakdown["page_presence"] = {"score": pres_score, "max": 15, "reason": pres_reason}

        # C. Evidence Coverage (Max 25)
        if total_claims_count > 0:
            coverage_ratio = min(1.0, max(0.0, supported_claims_count / total_claims_count))
            cov_score = round(25.0 * coverage_ratio, 1)
            cov_reason = f"{supported_claims_count} of {total_claims_count} extracted claims supported by direct evidence"
        else:
            cov_score = 0.0
            cov_reason = "No extracted claims to evaluate"
        breakdown["evidence_coverage"] = {"score": cov_score, "max": 25, "reason": cov_reason}

        # D. Eligibility and Deadline Support (Max 15)
        if has_eligibility_evidence and has_deadline_evidence:
            ed_score = 15.0
            ed_reason = "Both eligibility and application deadline backed by primary source quotations"
        elif has_eligibility_evidence or has_deadline_evidence:
            ed_score = 8.0
            ed_reason = "Partial support: either eligibility or deadline has direct citation"
        else:
            ed_score = 0.0
            ed_reason = "Neither eligibility nor deadline supported by evidence"
        breakdown["eligibility_deadline"] = {"score": ed_score, "max": 15, "reason": ed_reason}

        # E. Application Route Validation (Max 10)
        if has_verified_app_url:
            app_score = 10.0
            app_reason = "Official direct application URL or verified institutional route"
        elif is_official_source:
            app_score = 5.0
            app_reason = "Application hosted within official primary portal domain"
        else:
            app_score = 0.0
            app_reason = "Application URL missing or unverified"
        breakdown["application_route"] = {"score": app_score, "max": 10, "reason": app_reason}

        # F. Freshness (Max 10)
        fresh_score = 10.0
        fresh_reason = "Verified within the last 7 days"
        if last_verified_at:
            try:
                dt = datetime.fromisoformat(last_verified_at.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                days = (now - dt).days
                if days <= 7:
                    fresh_score = 10.0
                    fresh_reason = f"Verified recently ({days} days ago)"
                elif days <= 30:
                    fresh_score = 7.0
                    fresh_reason = f"Verified {days} days ago (within 1 month)"
                elif days <= 90:
                    fresh_score = 4.0
                    fresh_reason = f"Verified {days} days ago (within 3 months)"
                else:
                    fresh_score = 0.0
                    fresh_reason = f"Stale verification ({days} days ago)"
            except Exception:
                pass
        breakdown["freshness"] = {"score": fresh_score, "max": 10, "reason": fresh_reason}

        total_score = src_score + pres_score + cov_score + ed_score + app_score + fresh_score

        # G. Conflict Penalty
        if has_unresolved_conflict:
            penalty = 15.0
            total_score = max(0.0, total_score - penalty)
            breakdown["conflict_penalty"] = {
                "score": -penalty,
                "reason": "Conflicting cycle or eligibility dates between official sources",
            }

        total_score = round(min(100.0, max(0.0, total_score)), 1)
        return total_score, breakdown

    def determine_status(
        self,
        score: float,
        is_official_source: bool,
        has_critical_evidence: bool,
        has_unresolved_conflict: bool = False,
    ) -> str:
        """
        Hard Verification Gates:
        Must score >= 95.0 AND be from official source AND have critical evidence AND have no conflict.
        """
        if (
            score >= CONFIDENCE_VERIFIED_THRESHOLD
            and is_official_source
            and has_critical_evidence
            and not has_unresolved_conflict
        ):
            return "VERIFIED"
        return "REVIEW_REQUIRED"
