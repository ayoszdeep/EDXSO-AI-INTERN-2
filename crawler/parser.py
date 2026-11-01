"""
HTML and Structured Content Parser.
Extracts headings, paragraphs, tables, lists, and links from web documents.
"""
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin


class DocumentParser:
    def parse_html(self, html: str, base_url: str = "") -> Dict[str, Any]:
        """
        Parses raw HTML into structured sections: title, headings, paragraphs,
        tables, and extracted links.
        """
        if not html:
            return {
                "title": "",
                "clean_text": "",
                "headings": [],
                "tables": [],
                "paragraphs": [],
                "links": [],
            }

        soup = BeautifulSoup(html, "html.parser")

        # Extract title
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else ""

        # Remove irrelevant non-content tags
        for tag in soup(["script", "style", "noscript", "svg", "header", "footer", "nav"]):
            tag.decompose()

        # Headings
        headings = []
        for h in soup.find_all(["h1", "h2", "h3", "h4"]):
            htext = h.get_text(" ", strip=True)
            if htext:
                headings.append({"level": h.name, "text": htext})

        # Paragraphs
        paragraphs = []
        for p in soup.find_all("p"):
            ptext = p.get_text(" ", strip=True)
            if ptext and len(ptext) > 10:
                paragraphs.append(ptext)

        # Tables
        tables = []
        for table in soup.find_all("table"):
            rows = []
            for tr in table.find_all("tr"):
                cells = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
                if any(cells):
                    rows.append(cells)
            if rows:
                tables.append(rows)

        # Links
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            text = a.get_text(" ", strip=True)
            if href and not href.startswith(("#", "javascript:", "mailto:", "tel:")):
                full_href = urljoin(base_url, href) if base_url else href
                links.append({"text": text, "url": full_href})

        # Clean text
        clean_text = soup.get_text("\n", strip=True)

        return {
            "title": title,
            "clean_text": clean_text,
            "headings": headings,
            "tables": tables,
            "paragraphs": paragraphs,
            "links": links,
        }
