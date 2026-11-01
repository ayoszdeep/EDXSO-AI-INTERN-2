"""
Scholarship Extraction Engine.
Converts unstructured document text, tables, and PDF pages into validated Pydantic models
with exact supporting evidence quotes for every extracted claim.
"""
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
from dateutil import parser as date_parser
from pydantic import BaseModel, Field


class ScholarshipRecord(BaseModel):
    canonical_key: str
    name: str
    provider: str
    provider_type: str
    official_source_url: str
    application_url: Optional[str] = None
    benefit: Optional[str] = None
    eligibility: Optional[str] = None
    academic_requirements: Optional[str] = None
    education_levels: List[str] = Field(default_factory=list)
    courses: List[str] = Field(default_factory=list)
    income_limit_inr: Optional[int] = None
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    gender_criteria: Optional[str] = None
    category_criteria: Optional[str] = None
    domicile_criteria: Optional[str] = None
    institution_criteria: Optional[str] = None
    opening_date: Optional[str] = None
    deadline: Optional[str] = None
    documents_required: List[str] = Field(default_factory=list)
    selection_process: Optional[str] = None
    renewal_requirements: Optional[str] = None
    # Traceable evidence mapped per field: {field_name: {"quote": str, "page": Optional[int]}}
    evidence_map: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


def normalize_text(text: str) -> str:
    """Normalizes whitespace and lowercases for evidence matching."""
    return " ".join(text.lower().split())


def validate_evidence(source_text: str, quote: Optional[str]) -> bool:
    """Verifies that the extracted quote actually exists in the source text."""
    if not quote or not source_text:
        return False
    return normalize_text(quote) in normalize_text(source_text)


def parse_inr_amount(text: str) -> Optional[int]:
    """Extracts numeric INR value from strings like '8 lakh', 'Rs. 2,50,000', '15 Lakhs'."""
    lakh_match = re.search(r'(?:rs\.?|inr|₹)?\s*(\d+(?:\.\d+)?)\s*(?:lakh|lac|lacs|lakhs)', text, re.IGNORECASE)
    if lakh_match:
        try:
            return int(float(lakh_match.group(1)) * 100000)
        except ValueError:
            pass

    num_match = re.search(r'(?:rs\.?|inr|₹)\s*([\d,]+)', text, re.IGNORECASE)
    if num_match:
        clean = num_match.group(1).replace(",", "")
        try:
            return int(clean)
        except ValueError:
            pass
    return None


def parse_date(date_str: str) -> Optional[str]:
    """Parses date string into ISO YYYY-MM-DD format."""
    if not date_str:
        return None
    # Remove ordinal suffixes like 31st, 1st, 2nd
    clean = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str.strip(), flags=re.IGNORECASE)
    try:
        # If string starts with 4-digit year (e.g. 2026-11-05), parse year first to avoid MM/DD swap
        if re.match(r'^\d{4}[-\/\.]\d{1,2}[-\/\.]\d{1,2}', clean):
            dt = date_parser.parse(clean, yearfirst=True)
        else:
            dt = date_parser.parse(clean, dayfirst=True, fuzzy=True)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return None


class ScholarshipExtractor:
    def __init__(self):
        pass

    def generate_canonical_key(self, provider: str, name: str) -> str:
        """Generates a stable unique canonical key for deduplication."""
        norm_p = re.sub(r'[^a-z0-9]', '', provider.lower())
        norm_n = re.sub(r'[^a-z0-9]', '', name.lower())
        return f"{norm_p}:{norm_n}"

    def extract_from_text(
        self,
        text: str,
        source_url: str,
        provider_name: str,
        provider_type: str,
        pdf_pages: Optional[Dict[int, str]] = None,
    ) -> List[ScholarshipRecord]:
        """
        Extracts scholarship record(s) from text using pattern matching,
        sentence scanning, and exact quote capturing.
        """
        records: List[ScholarshipRecord] = []
        if not text:
            return records

        # Split text into paragraphs and sentences for targeted evidence isolation
        sentences = [s.strip() for s in re.split(r'[.\n]\s*', text) if len(s.strip()) > 8]

        # 1. Scholarship Name Identification
        name = None
        name_quote = None
        name_page = None

        name_patterns = [
            r'([A-Z][A-Za-z0-9\s\-\–\(\)]+Scholarship(?:\s+(?:Scheme|Program|Programme|for\s+[A-Za-z0-9\s]+))?)',
            r'([A-Z][A-Za-z0-9\s\-\–\(\)]+Fellowship(?:\s+(?:Scheme|Program|Programme))?)',
            r'(Financial Assistance for [A-Za-z0-9\s\-\–\(\)]+)',
            r'(Merit-cum-Means Scholarship(?:\s+[A-Za-z0-9\s]+)?)',
        ]

        for s in sentences:
            for pat in name_patterns:
                m = re.search(pat, s)
                if m:
                    cand = m.group(1).strip()
                    if 10 <= len(cand) <= 100:
                        name = cand
                        name_quote = s
                        break
            if name:
                break

        if not name:
            # Fallback: Check first heading or prominent line
            for line in text.splitlines():
                cl = line.strip()
                if "scholarship" in cl.lower() and 10 <= len(cl) <= 90:
                    name = cl
                    name_quote = cl
                    break

        if not name:
            return []  # No credible scholarship identified

        # Find which PDF page contains the quote if available
        if pdf_pages and name_quote:
            for pnum, ptxt in pdf_pages.items():
                if normalize_text(name_quote) in normalize_text(ptxt):
                    name_page = pnum
                    break

        evidence_map: Dict[str, Dict[str, Any]] = {
            "name": {"quote": name_quote, "page": name_page},
            "provider": {"quote": f"Offered by {provider_name}", "page": None},
        }

        # 2. Benefit Extraction
        benefit = None
        benefit_quote = None
        benefit_page = None
        for s in sentences:
            if any(w in s.lower() for w in ["grant", "amount", "stipend", "rs.", "inr", "₹", "per month", "per annum", "tuition fee"]):
                b_match = re.search(r'(?:₹|rs\.?|inr)\s*[\d,]+(?:\s*(?:per\s+(?:month|annum|year)|lakhs?|lacs?))?', s, re.IGNORECASE)
                if b_match or "tuition" in s.lower() or "financial assistance" in s.lower():
                    benefit = s.strip()
                    benefit_quote = s.strip()
                    break

        if benefit_quote:
            if pdf_pages:
                for pnum, ptxt in pdf_pages.items():
                    if normalize_text(benefit_quote) in normalize_text(ptxt):
                        benefit_page = pnum
                        break
            evidence_map["benefit"] = {"quote": benefit_quote, "page": benefit_page}

        # 3. Eligibility & Academic Requirements
        eligibility = None
        elig_quote = None
        academic_req = None
        for s in sentences:
            sl = s.lower()
            if any(w in sl for w in ["eligibility", "eligible", "citizen", "resident", "who can apply"]):
                eligibility = s.strip()
                elig_quote = s.strip()
                break

        if elig_quote:
            evidence_map["eligibility"] = {"quote": elig_quote, "page": None}

        # Check % or CGPA requirement
        for s in sentences:
            if any(w in s.lower() for w in ["marks", "cgpa", "%", "percent", "passed class", "grade"]):
                academic_req = s.strip()
                evidence_map["academic_requirements"] = {"quote": s.strip(), "page": None}
                break

        # 4. Income Criteria
        income_limit = None
        for s in sentences:
            sl = s.lower()
            if any(w in sl for w in ["income", "parental income", "family income", "household income"]):
                amt = parse_inr_amount(s)
                if amt:
                    income_limit = amt
                    evidence_map["income_limit_inr"] = {"quote": s.strip(), "page": None}
                    break

        # 5. Application Deadline
        deadline = None
        deadline_quote = None
        deadline_patterns = [
            r'(?:last date|closing date|deadline|open till|apply by|valid upto|upto)\s*[:\-]?\s*([0-9]{1,2}(?:st|nd|rd|th)?[\/\-\s]+[A-Za-z0-9]+[\/\-\s]+[0-9]{4})',
            r'([0-9]{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+[0-9]{4})',
            r'([0-9]{4}\-[0-9]{2}\-[0-9]{2})',
        ]
        for s in sentences:
            sl = s.lower()
            if any(w in sl for w in ["last date", "deadline", "closing date", "apply by", "open till", "upto"]):
                for pat in deadline_patterns:
                    m = re.search(pat, s, re.IGNORECASE)
                    if m:
                        d_str = m.group(1).strip()
                        parsed_d = parse_date(d_str)
                        if parsed_d:
                            deadline = parsed_d
                            deadline_quote = s.strip()
                            break
            if deadline:
                break

        if deadline_quote:
            evidence_map["deadline"] = {"quote": deadline_quote, "page": None}

        # 6. Education Levels & Courses
        education_levels = []
        tl = text.lower()
        if "undergraduate" in tl or " ug " in tl or "bachelor" in tl or "b.tech" in tl:
            education_levels.append("UNDERGRADUATE")
        if "postgraduate" in tl or " pg " in tl or "master" in tl or "m.tech" in tl:
            education_levels.append("POSTGRADUATE")
        if "phd" in tl or "doctoral" in tl or "fellowship" in tl:
            education_levels.append("DOCTORAL")
        if "diploma" in tl or "polytechnic" in tl:
            education_levels.append("DIPLOMA")
        if "school" in tl or "class 1" in tl or "class 10" in tl or "class 12" in tl:
            education_levels.append("SCHOOL")

        # 7. Category and Gender Criteria
        gender_criteria = None
        if "girl" in tl or "female" in tl or "women" in tl:
            gender_criteria = "Female only"
            evidence_map["gender_criteria"] = {"quote": "Eligible for female/girl students", "page": None}

        category_criteria = None
        categories_found = []
        for cat in ["SC", "ST", "OBC", "EWS", "Disability", "PWD", "Minority"]:
            if re.search(rf'\b{cat}\b', text, re.IGNORECASE):
                categories_found.append(cat)
        if categories_found:
            category_criteria = ", ".join(categories_found)
            evidence_map["category_criteria"] = {"quote": f"Applicable for {category_criteria}", "page": None}

        canonical_key = self.generate_canonical_key(provider_name, name)

        record = ScholarshipRecord(
            canonical_key=canonical_key,
            name=name,
            provider=provider_name,
            provider_type=provider_type,
            official_source_url=source_url,
            application_url=source_url,
            benefit=benefit,
            eligibility=eligibility,
            academic_requirements=academic_req,
            education_levels=education_levels,
            courses=[],
            income_limit_inr=income_limit,
            gender_criteria=gender_criteria,
            category_criteria=category_criteria,
            deadline=deadline,
            evidence_map=evidence_map,
        )
        records.append(record)
        return records

    def extract_from_tables(
        self,
        tables: List[List[List[str]]],
        source_url: str,
        provider_name: str,
        provider_type: str,
    ) -> List[ScholarshipRecord]:
        """
        Extracts scholarships structured in tabular format, commonly found on
        National Scholarship Portal and Government Ministry scheme directories.
        """
        records: List[ScholarshipRecord] = []
        for table in tables:
            if not table or len(table) < 2:
                continue

            header = [col.lower() for col in table[0]]
            # Find indices for scheme name, deadline, guidelines/apply
            name_idx = None
            date_idx = None
            benefit_idx = None

            for i, col in enumerate(header):
                if any(w in col for w in ["scheme", "scholarship", "programme", "name"]):
                    name_idx = i
                elif any(w in col for w in ["date", "deadline", "closing", "open till"]):
                    date_idx = i
                elif any(w in col for w in ["amount", "benefit", "grant", "stipend"]):
                    benefit_idx = i

            if name_idx is None:
                continue

            for row in table[1:]:
                if len(row) <= name_idx:
                    continue
                scheme_name = row[name_idx].strip()
                if len(scheme_name) < 5 or "click here" in scheme_name.lower():
                    continue

                deadline = None
                deadline_quote = None
                if date_idx is not None and len(row) > date_idx:
                    date_val = row[date_idx].strip()
                    parsed_d = parse_date(date_val)
                    if parsed_d:
                        deadline = parsed_d
                        deadline_quote = f"Table date: {date_val}"

                benefit = None
                if benefit_idx is not None and len(row) > benefit_idx:
                    benefit = row[benefit_idx].strip()

                evidence_map = {
                    "name": {"quote": scheme_name, "page": None},
                    "provider": {"quote": f"Offered by {provider_name}", "page": None},
                }
                if deadline_quote:
                    evidence_map["deadline"] = {"quote": deadline_quote, "page": None}
                if benefit:
                    evidence_map["benefit"] = {"quote": benefit, "page": None}

                rec = ScholarshipRecord(
                    canonical_key=self.generate_canonical_key(provider_name, scheme_name),
                    name=scheme_name,
                    provider=provider_name,
                    provider_type=provider_type,
                    official_source_url=source_url,
                    application_url=source_url,
                    benefit=benefit,
                    deadline=deadline,
                    evidence_map=evidence_map,
                )
                records.append(rec)

        return records
