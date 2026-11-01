"""
Crawler Fetcher: Handles HTTP retrieval, Playwright JavaScript fallback,
PDF extraction via PyMuPDF, content hashing, and snapshot archiving.
"""
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse
import requests
from config.settings import DEFAULT_TIMEOUT, HEADERS, RAW_PAGES_DIR

logger = logging.getLogger(__name__)


def compute_hash(data: bytes) -> str:
    """Computes SHA-256 fingerprint for snapshot verification."""
    return hashlib.sha256(data).hexdigest()


class PageFetcher:
    def __init__(self, raw_pages_dir: Path = RAW_PAGES_DIR):
        self.raw_pages_dir = raw_pages_dir
        self.raw_pages_dir.mkdir(parents=True, exist_ok=True)

    def _save_snapshot(self, domain: str, extension: str, content: bytes, content_hash: str) -> str:
        """Saves page or PDF snapshot to disk."""
        safe_domain = "".join(c if c.isalnum() else "_" for c in domain)
        filename = f"{safe_domain}_{content_hash[:12]}.{extension}"
        path = self.raw_pages_dir / filename
        if not path.exists():
            path.write_bytes(content)
        return str(path)

    def fetch_page(self, url: str, use_playwright_fallback: bool = False) -> Dict[str, Any]:
        """
        Fetches webpage or PDF document using requests, with optional Playwright fallback.
        Extracts PDF text using PyMuPDF if applicable.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        domain = urlparse(url).netloc.lower()

        try:
            resp = requests.get(
                url,
                headers=HEADERS,
                timeout=DEFAULT_TIMEOUT,
                allow_redirects=True,
                verify=True,
            )
            status_code = resp.status_code
            final_url = resp.url
            content_type = resp.headers.get("Content-Type", "").lower()
            raw_bytes = resp.content
            content_hash = compute_hash(raw_bytes)

            # Check if PDF
            if "application/pdf" in content_type or url.lower().endswith(".pdf"):
                snapshot_path = self._save_snapshot(domain, "pdf", raw_bytes, content_hash)
                pdf_text, pdf_pages = self._extract_pdf_text(raw_bytes)
                return {
                    "requested_url": url,
                    "final_url": final_url,
                    "status_code": status_code,
                    "content_type": "application/pdf",
                    "html": None,
                    "text": pdf_text,
                    "pdf_pages": pdf_pages,
                    "content_hash": content_hash,
                    "snapshot_path": snapshot_path,
                    "fetched_at": now_iso,
                    "success": True,
                    "error": None,
                }

            # Ordinary HTML
            html_text = resp.text
            snapshot_path = self._save_snapshot(domain, "html", raw_bytes, content_hash)

            # Check if HTML requires JS rendering (e.g. very empty body with <div id="root"></div>)
            if use_playwright_fallback and len(html_text) < 1200 and "noscript" in html_text.lower():
                pw_html = self._fetch_with_playwright(url)
                if pw_html:
                    html_text = pw_html
                    raw_bytes = pw_html.encode("utf-8")
                    content_hash = compute_hash(raw_bytes)
                    snapshot_path = self._save_snapshot(domain, "html", raw_bytes, content_hash)

            return {
                "requested_url": url,
                "final_url": final_url,
                "status_code": status_code,
                "content_type": content_type,
                "html": html_text,
                "text": None,  # Will be extracted by parser
                "pdf_pages": {},
                "content_hash": content_hash,
                "snapshot_path": snapshot_path,
                "fetched_at": now_iso,
                "success": status_code < 400,
                "error": None if status_code < 400 else f"HTTP Status {status_code}",
            }

        except requests.RequestException as e:
            logger.warning(f"Failed to fetch {url} via requests: {e}")
            if use_playwright_fallback:
                pw_html = self._fetch_with_playwright(url)
                if pw_html:
                    raw_bytes = pw_html.encode("utf-8")
                    content_hash = compute_hash(raw_bytes)
                    snapshot_path = self._save_snapshot(domain, "html", raw_bytes, content_hash)
                    return {
                        "requested_url": url,
                        "final_url": url,
                        "status_code": 200,
                        "content_type": "text/html",
                        "html": pw_html,
                        "text": None,
                        "pdf_pages": {},
                        "content_hash": content_hash,
                        "snapshot_path": snapshot_path,
                        "fetched_at": now_iso,
                        "success": True,
                        "error": None,
                    }

            return {
                "requested_url": url,
                "final_url": url,
                "status_code": None,
                "content_type": None,
                "html": None,
                "text": None,
                "pdf_pages": {},
                "content_hash": None,
                "snapshot_path": None,
                "fetched_at": now_iso,
                "success": False,
                "error": str(e),
            }

    def _extract_pdf_text(self, pdf_bytes: bytes) -> tuple[str, dict]:
        """Extracts text page by page from PDF using PyMuPDF."""
        try:
            import pymupdf
            doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
            full_text = []
            pages_dict = {}
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                txt = page.get_text("text")
                pages_dict[page_num + 1] = txt
                full_text.append(f"--- Page {page_num + 1} ---\n{txt}")
            doc.close()
            return "\n\n".join(full_text), pages_dict
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            return "", {}

    def _fetch_with_playwright(self, url: str) -> Optional[str]:
        """Fallback to Playwright headless browser for JavaScript-heavy rendering."""
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(user_agent=HEADERS["User-Agent"])
                page.goto(url, wait_until="networkidle", timeout=30000)
                content = page.content()
                browser.close()
                return content
        except Exception as e:
            logger.warning(f"Playwright fallback not available or failed for {url}: {e}")
            return None
