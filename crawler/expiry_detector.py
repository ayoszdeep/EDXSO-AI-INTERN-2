"""
Scholarship Expiry and Stale Lifecycle Detection Module.
Calculates lifecycle_status (ACTIVE, EXPIRING_SOON, EXPIRED, REVIEW_REQUIRED, NO_LONGER_VERIFIABLE).
"""
from datetime import date, datetime
from typing import Optional
from crawler.extractor import parse_date


class ExpiryDetector:
    def check_expiry(self, deadline_str: Optional[str], today: Optional[date] = None) -> str:
        """
        Calculates lifecycle_status based on confirmed application deadline.
        """
        if today is None:
            today = date.today()

        if not deadline_str:
            return "REVIEW_REQUIRED"

        parsed = parse_date(deadline_str)
        if not parsed:
            return "REVIEW_REQUIRED"

        try:
            deadline_date = datetime.strptime(parsed, "%Y-%m-%d").date()
        except ValueError:
            return "REVIEW_REQUIRED"

        if deadline_date < today:
            return "EXPIRED"

        remaining_days = (deadline_date - today).days
        if remaining_days <= 7:
            return "EXPIRING_SOON"

        return "ACTIVE"

    def evaluate_removal(self, consecutive_fetch_failures: int, is_officially_withdrawn: bool = False) -> str:
        """
        Handles missing pages or official withdrawal notices.
        A single 404 does NOT immediately delete or mark invalid.
        Only after repeated persistent failures is it marked NO_LONGER_VERIFIABLE.
        """
        if is_officially_withdrawn:
            return "NO_LONGER_VERIFIABLE"
        if consecutive_fetch_failures >= 3:
            return "NO_LONGER_VERIFIABLE"
        return "REVIEW_REQUIRED"
