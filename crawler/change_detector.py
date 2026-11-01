"""
Change Detection Engine.
Tracks field-level mutations between crawls, normalizes values to prevent false positives,
and logs historical transitions.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from crawler.extractor import parse_date, parse_inr_amount, normalize_text

TRACKED_FIELDS = [
    "deadline",
    "benefit",
    "eligibility",
    "academic_requirements",
    "income_limit_inr",
    "opening_date",
    "selection_process",
    "renewal_requirements",
]


def normalize_field_value(field: str, value: Any) -> Any:
    """Normalizes field values so formatting differences do not trigger false changes."""
    if value is None:
        return None
    val_str = str(value).strip()
    if not val_str:
        return None

    if field in ["deadline", "opening_date"]:
        parsed = parse_date(val_str)
        return parsed if parsed else val_str.lower()

    if field == "income_limit_inr":
        try:
            return int(val_str)
        except ValueError:
            return parse_inr_amount(val_str)

    # Text fields: normalize whitespace and casing
    return normalize_text(val_str)


class ChangeDetector:
    def detect_changes(
        self,
        old_record: Dict[str, Any],
        new_record: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Compares old scholarship database record with freshly extracted record.
        Returns a list of detected field changes.
        """
        changes: List[Dict[str, Any]] = []

        for field in TRACKED_FIELDS:
            old_raw = old_record.get(field)
            new_raw = new_record.get(field)

            # If both are none/empty, no change
            if old_raw is None and new_raw is None:
                continue

            old_norm = normalize_field_value(field, old_raw)
            new_norm = normalize_field_value(field, new_raw)

            if old_norm != new_norm:
                changes.append({
                    "field_name": field,
                    "old_value": str(old_raw) if old_raw is not None else None,
                    "new_value": str(new_raw) if new_raw is not None else None,
                    "source_url": new_record.get("official_source_url") or old_record.get("official_source_url"),
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                })

        return changes
