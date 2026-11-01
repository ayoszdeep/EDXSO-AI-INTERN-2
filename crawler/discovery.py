"""
Scholarship Discovery Engine.
Implements multi-layer discovery: Seed sources, Internal links, Sitemaps, and Search discovery.
"""
import json
import logging
import re
from typing import Dict, List, Set, Tuple
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import requests
from config.settings import HEADERS, DEFAULT_TIMEOUT, SOURCE_REGISTRY_PATH
from database.repository import ScholarshipRepository

logger = logging.getLogger(__name__)

KEYWORDS = [
    "scholarship",
    "scholarships",
    "fellowship",
    "financial-aid",
    "funding",
    "education-grant",
    "student-support",
    "scheme",
    "stipend",
    "freeship",
]

SEED_URLS = [
    "https://scholarships.gov.in",
    "https://www.ugc.gov.in/Home/student_Corner",
    "https://he.uk.gov.in/scholarship-portal/",
    "https://academics.iitd.ac.in/financial-assistance/",
    "https://scholarships.reliancefoundation.org/UG_Scholarship.aspx",
    "https://azimpremjifoundation.org/what-we-do/education/azim-premji-scholarship/applications/",
]


class DiscoveryEngine:
    def __init__(self, repo: ScholarshipRepository = None):
        self.repo = repo or ScholarshipRepository()
        self.registry = self._load_source_registry()

    def _load_source_registry(self) -> Dict[str, dict]:
        """Loads domain classification registry."""
        if not SOURCE_REGISTRY_PATH.exists():
            return {}
        try:
            sources = json.loads(SOURCE_REGISTRY_PATH.read_text(encoding="utf-8"))
            return {s["domain"]: s for s in sources}
        except Exception as e:
            logger.error(f"Error loading source registry: {e}")
            return {}

    def classify_domain(self, url: str) -> Tuple[str, str, bool]:
        """
        Classifies domain into (provider_name, source_type, is_official).
        Handles known registry, .gov.in (Government), .ac.in / .edu.in (University),
        and aggregators.
        """
        domain = urlparse(url).netloc.lower()
        if domain.startswith("www."):
            clean_domain = domain[4:]
        else:
            clean_domain = domain

        # Check registry first
        if domain in self.registry:
            r = self.registry[domain]
            return r.get("provider", "Official Provider"), r["source_type"], bool(r.get("official"))
        if clean_domain in self.registry:
            r = self.registry[clean_domain]
            return r.get("provider", "Official Provider"), r["source_type"], bool(r.get("official"))

        # Heuristic rules
        if domain.endswith(".gov.in") or domain.endswith(".nic.in"):
            return "Government Department", "GOVERNMENT", True
        if domain.endswith(".ac.in") or domain.endswith(".edu.in") or domain.endswith(".edu"):
            return "Academic Institution", "UNIVERSITY", True
        if any(agg in domain for agg in ["buddy4study", "shiksha", "collegedunia", "freshersworld"]):
            return "Aggregator Portal", "AGGREGATOR", False

        return "Unknown Organization", "OTHER", False

    def is_relevant_link(self, href: str, text: str) -> bool:
        """Determines if a hyperlink is likely related to scholarship information."""
        combined = f"{href} {text}".lower()
        return any(kw in combined for kw in KEYWORDS)

    def discover_links_from_page(self, page_url: str, html: str) -> Set[str]:
        """Parses HTML and extracts candidate scholarship hyperlinks."""
        candidates = set()
        soup = BeautifulSoup(html, "html.parser")
        base_domain = urlparse(page_url).netloc.lower()

        for anchor in soup.find_all("a", href=True):
            raw_href = anchor["href"].strip()
            if not raw_href or raw_href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue

            full_url = urljoin(page_url, raw_href)
            link_domain = urlparse(full_url).netloc.lower()
            link_text = anchor.get_text(" ", strip=True)

            # Check relevance
            if self.is_relevant_link(full_url, link_text):
                # Prefer same domain or known official domains
                candidates.add(full_url)

        return candidates

    def discover_from_sitemap(self, root_url: str) -> Set[str]:
        """Discovers candidate URLs by querying sitemap.xml."""
        candidates = set()
        sitemap_url = urljoin(root_url, "/sitemap.xml")
        try:
            resp = requests.get(sitemap_url, headers=HEADERS, timeout=10)
            if resp.status_code == 200 and "xml" in resp.headers.get("Content-Type", ""):
                soup = BeautifulSoup(resp.content, "xml")
                for loc in soup.find_all("loc"):
                    u = loc.get_text(strip=True)
                    if any(kw in u.lower() for kw in KEYWORDS):
                        candidates.add(u)
        except Exception:
            pass
        return candidates

    def discover_from_search(self, query: str = "site:gov.in scholarship scheme", max_results: int = 10) -> Set[str]:
        """Performs search discovery using duckduckgo_search if available."""
        candidates = set()
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                for res in results:
                    url = res.get("href") or res.get("link")
                    if url:
                        candidates.add(url)
        except Exception as e:
            logger.warning(f"Search discovery skipped or failed: {e}")
        return candidates

    def run_discovery(self, use_search: bool = True) -> Dict[str, int]:
        """
        Executes discovery workflow across seed sources, sitemaps, internal links,
        and optional search discovery.
        """
        discovered_urls: Set[str] = set()

        # Step 1: Add seed URLs
        for url in SEED_URLS:
            discovered_urls.add(url)

        # Step 2: Try sitemaps on seed roots
        for url in SEED_URLS:
            parsed = urlparse(url)
            root = f"{parsed.scheme}://{parsed.netloc}"
            sitemap_urls = self.discover_from_sitemap(root)
            discovered_urls.update(sitemap_urls)

        # Step 3: Optional search discovery
        if use_search:
            queries = [
                "site:scholarships.gov.in schemes",
                "site:ugc.gov.in scholarship fellowship",
                "site:academics.iitd.ac.in financial assistance",
                "reliance foundation undergraduate scholarship official",
            ]
            for q in queries:
                found = self.discover_from_search(q, max_results=5)
                discovered_urls.update(found)

        # Step 4: Classify and save to candidate database
        counts = {"OFFICIAL_CANDIDATE": 0, "CANDIDATE": 0, "AGGREGATOR": 0, "TOTAL": len(discovered_urls)}
        for url in discovered_urls:
            domain = urlparse(url).netloc.lower()
            provider, stype, is_official = self.classify_domain(url)
            
            if stype == "AGGREGATOR":
                classification = "AGGREGATOR"
            elif is_official:
                classification = "OFFICIAL_CANDIDATE"
            else:
                classification = "CANDIDATE"

            counts[classification] = counts.get(classification, 0) + 1
            self.repo.add_candidate(
                url=url,
                domain=domain,
                discovery_method="DISCOVERY_ENGINE",
                classification=classification,
            )

        return counts
