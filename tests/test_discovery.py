"""
Test suite for Discovery Engine.
"""
from crawler.discovery import DiscoveryEngine


def test_classify_official_government_domain():
    discovery = DiscoveryEngine()
    provider, stype, is_official = discovery.classify_domain("https://scholarships.gov.in/All-Scholarships")
    assert is_official is True
    assert stype == "GOVERNMENT"


def test_classify_university_domain():
    discovery = DiscoveryEngine()
    provider, stype, is_official = discovery.classify_domain("https://academics.iitd.ac.in/financial-assistance/")
    assert is_official is True
    assert stype == "UNIVERSITY"


def test_classify_aggregator_portal():
    discovery = DiscoveryEngine()
    provider, stype, is_official = discovery.classify_domain("https://www.buddy4study.com/scholarships")
    assert is_official is False
    assert stype == "AGGREGATOR"


def test_is_relevant_link():
    discovery = DiscoveryEngine()
    assert discovery.is_relevant_link("/financial-aid/schemes", "Student scholarships") is True
    assert discovery.is_relevant_link("/privacy-policy", "Privacy Policy") is False
    assert discovery.is_relevant_link("/fellowship-details", "Doctoral Fellowship") is True


def test_discover_links_deduplication():
    discovery = DiscoveryEngine()
    html = """
    <html>
        <body>
            <a href="/scholarship-a">Scholarship Scheme A</a>
            <a href="/scholarship-a">Scholarship Scheme A</a>
            <a href="/about-us">About Our Team</a>
        </body>
    </html>
    """
    links = discovery.discover_links_from_page("https://example.gov.in", html)
    assert len(links) == 1
    assert "https://example.gov.in/scholarship-a" in links
