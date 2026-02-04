# rfsn_kernel/tools/web.py
"""Web tools: search and browse."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


@dataclass
class WebSearchResponse:
    query: str
    results: List[SearchResult]
    error: Optional[str] = None


@dataclass
class BrowseResponse:
    url: str
    content: str
    status_code: int
    error: Optional[str] = None


def web_search(
    query: str,
    num_results: int = 5,
    api_key: Optional[str] = None,
) -> WebSearchResponse:
    """
    Search the web using DuckDuckGo (no API key required) or other providers.
    """
    try:
        # Try DuckDuckGo HTML scraping (lightweight, no API key)
        import httpx

        headers = {"User-Agent": "Mozilla/5.0 (compatible; RFSN/1.0)"}
        url = f"https://html.duckduckgo.com/html/?q={query}"

        with httpx.Client(timeout=20.0) as client:
            resp = client.get(url, headers=headers, follow_redirects=True)
            resp.raise_for_status()

        # Simple parsing - extract result links
        results = []
        content = resp.text

        # Extract result divs (simplified parsing)
        import re
        # Match result links
        pattern = r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>([^<]*)</a>'
        matches = re.findall(pattern, content, re.IGNORECASE)

        for url_match, title in matches[:num_results]:
            results.append(SearchResult(
                title=title.strip(),
                url=url_match,
                snippet="",
            ))

        return WebSearchResponse(query=query, results=results)

    except Exception as e:
        return WebSearchResponse(query=query, results=[], error=str(e))


def browse_url(
    url: str,
    max_chars: int = 50_000,
) -> BrowseResponse:
    """
    Fetch and extract text content from a URL.
    Returns markdown-formatted content.
    """
    try:
        import httpx

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; RFSN/1.0)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)

        content_type = resp.headers.get("content-type", "")

        if "text/html" in content_type:
            # Extract text from HTML
            html = resp.text
            text = _html_to_text(html)
        elif "application/json" in content_type:
            text = resp.text
        else:
            text = resp.text

        # Truncate if needed
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[TRUNCATED]"

        return BrowseResponse(
            url=url,
            content=text,
            status_code=resp.status_code,
        )

    except Exception as e:
        return BrowseResponse(
            url=url,
            content="",
            status_code=0,
            error=str(e),
        )


def _html_to_text(html: str) -> str:
    """Convert HTML to plain text, preserving structure."""
    import re

    # Remove script and style elements
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)

    # Convert common elements
    html = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'</p>', '\n\n', html, flags=re.IGNORECASE)
    html = re.sub(r'</div>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'</h[1-6]>', '\n\n', html, flags=re.IGNORECASE)
    html = re.sub(r'<h[1-6][^>]*>', '\n\n# ', html, flags=re.IGNORECASE)
    html = re.sub(r'</li>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'<li[^>]*>', '• ', html, flags=re.IGNORECASE)

    # Remove all remaining tags
    html = re.sub(r'<[^>]+>', '', html)

    # Decode entities
    html = html.replace('&nbsp;', ' ')
    html = html.replace('&amp;', '&')
    html = html.replace('&lt;', '<')
    html = html.replace('&gt;', '>')
    html = html.replace('&quot;', '"')

    # Clean up whitespace
    lines = [line.strip() for line in html.split('\n')]
    lines = [line for line in lines if line]

    return '\n'.join(lines)
