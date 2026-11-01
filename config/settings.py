"""
Configuration and settings for Scholarship Intelligence Crawler.
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Storage paths
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "scholarships.db"
RAW_PAGES_DIR = DATA_DIR / "raw_pages"
FIXTURES_DIR = DATA_DIR / "fixtures"
SOURCE_REGISTRY_PATH = BASE_DIR / "config" / "source_registry.json"

# Network & crawler settings
DEFAULT_TIMEOUT = 25
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 (ScholarshipResearchBot/1.0; +https://edxso.org)"
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

MAX_CONCURRENT_REQUESTS = 5
MAX_PAGES_PER_DOMAIN = 15
REQUEST_DELAY_SECONDS = 0.5

# Scoring thresholds
CONFIDENCE_VERIFIED_THRESHOLD = 95.0
CRITICAL_EVIDENCE_FIELDS = ["name", "provider", "eligibility"]
