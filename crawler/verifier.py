"""
Scholarship Verification Engine.
Performs evidence verification against primary source documents, enforces hard gates,
and orchestrates confidence scoring.
"""
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse
from crawler.extractor import ScholarshipRecord, validate_evidence, normalize_text
from crawler.scorer import ConfidenceScorer
from config.settings import CRITICAL_EVIDENCE_FIELDS


class ScholarshipVerifier:
    def __init__(self, registry: Dict[str, dict] = None):
        self.scorer = ConfidenceScorer()
        self.registry = registry or {}

    def is_official_source(self, url: str) -> Tuple[bool, bool, bool]:
        """
        Determines (is_official, is_aggregator, is_linked_from_official) based on domain.
        """
        domain = urlparse(url).netloc.lower()
        if domain.startswith("www."):
            clean_domain = domain[4:]
        else:
            clean_domain = domain

        # Check in registry
        entry = self.registry.get(domain) or self.registry.get(clean_domain)
        if entry:
            is_off = bool(entry.get("official"))
            is_agg = entry.get("source_type") == "AGGREGATOR"
            return is_off, is_agg, False

        # Domain heuristics
        if domain.endswith(".gov.in") or domain.endswith(".nic.in"):
            return True, False, False
        if domain.endswith(".ac.in") or domain.endswith(".edu.in"):
            return True, False, False
        if any(agg in domain for agg in ["buddy4study", "shiksha", "collegedunia"]):
            return False, True, False

        return False, False, False

    def verify_record(
        self,
        record: ScholarshipRecord,
        source_text: str,
        snapshot_path: str = None,
        content_hash: str = None,
        last_verified_at: str = None,
        has_conflict: bool = False,
    ) -> Dict[str, Any]:
        """
        Verifies all claims in a scholarship record against the source text,
        evaluates confidence score, and determines verification status.
        """
        is_official, is_aggregator, is_linked = self.is_official_source(record.official_source_url)

        # Validate each claim against source text
        valid_evidence_items: List[Dict[str, Any]] = []
        supported_claims = 0
        total_claims = 0

        # Important fields to track
        eval_fields = [
            "name",
            "provider",
            "benefit",
            "eligibility",
            "academic_requirements",
            "deadline",
            "income_limit_inr",
            "gender_criteria",
            "category_criteria",
        ]

        rec_dict = record.model_dump()

        for field in eval_fields:
            val = rec_dict.get(field)
            if val is not None and val != "":
                total_claims += 1
                ev = record.evidence_map.get(field, {})
                quote = ev.get("quote")
                page_num = ev.get("page")

                is_supported = False
                if quote:
                    if normalize_text(quote) in normalize_text(source_text):
                        is_supported = True
                    elif str(val).lower() in normalize_text(source_text):
                        is_supported = True

                if is_supported:
                    supported_claims += 1
                    valid_evidence_items.append({
                        "field_name": field,
                        "extracted_value": str(val),
                        "source_url": record.official_source_url,
                        "evidence_text": quote or f"Found in text: {val}",
                        "page_number": page_num,
                        "snapshot_path": snapshot_path,
                        "content_hash": content_hash,
                        "extraction_method": "RULE_BASED",
                    })

        # Check critical evidence presence (name and provider or eligibility)
        has_critical = any(
            item["field_name"] == "name" for item in valid_evidence_items
        ) and (
            any(item["field_name"] == "eligibility" for item in valid_evidence_items)
            or any(item["field_name"] == "deadline" for item in valid_evidence_items)
            or any(item["field_name"] == "benefit" for item in valid_evidence_items)
        )

        has_eligibility = any(item["field_name"] == "eligibility" for item in valid_evidence_items)
        has_deadline = any(item["field_name"] == "deadline" for item in valid_evidence_items)
        is_present = any(item["field_name"] == "name" for item in valid_evidence_items)
        has_verified_app = bool(record.application_url and is_official)

        score, breakdown = self.scorer.calculate_score(
            is_official_source=is_official,
            is_aggregator=is_aggregator,
            is_linked_from_official=is_linked,
            is_present_on_source=is_present,
            is_older_cycle_document=False,
            supported_claims_count=supported_claims,
            total_claims_count=total_claims,
            has_eligibility_evidence=has_eligibility,
            has_deadline_evidence=has_deadline,
            has_verified_app_url=has_verified_app,
            last_verified_at=last_verified_at,
            has_unresolved_conflict=has_conflict,
        )

        verification_status = self.scorer.determine_status(
            score=score,
            is_official_source=is_official,
            has_critical_evidence=has_critical,
            has_unresolved_conflict=has_conflict,
        )

        res = dict(rec_dict)
        res["confidence_score"] = score
        res["score_breakdown"] = breakdown
        res["verification_status"] = verification_status
        res["validated_evidence"] = valid_evidence_items
        return res
