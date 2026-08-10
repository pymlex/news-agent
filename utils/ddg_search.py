from urllib.parse import parse_qs, unquote, urlparse


import httpx
from bs4 import BeautifulSoup
from tqdm.auto import tqdm


from models.schemas import SearchHit
from utils.config import settings


DDG_HTML = "https://html.duckduckgo.com/html/"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def _domain_of(url: str) -> str:
    """Extract a lowercase network location from a URL."""

    netloc = urlparse(url).netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


def _unwrap_ddg_href(href: str) -> str:
    """Resolve DuckDuckGo redirect links to the destination URL."""

    if not href:
        return ""
    if href.startswith("//"):
        href = "https:" + href
    parsed = urlparse(href)
    if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
        qs = parse_qs(parsed.query)
        if "uddg" in qs and qs["uddg"]:
            return unquote(qs["uddg"][0])
    return href


def search_web(
    query: str,
    max_results: int | None = None,
    region: str = "wt-wt",
) -> list[SearchHit]:
    """Search the public web through DuckDuckGo HTML results.

    Args:
        query: Natural language or keyword query.
        max_results: Soft limit, capped by settings.max_search_hard_cap.
        region: Kept for API compatibility with callers.

    Returns:
        Ranked search hits with title, url and snippet.
    """

    soft = max_results if max_results is not None else settings.max_search_results
    limit = min(max(soft, 1), settings.max_search_hard_cap)
    headers = {"User-Agent": USER_AGENT}
    with httpx.Client(timeout=45.0, follow_redirects=True, headers=headers) as client:
        response = client.get(DDG_HTML, params={"q": query, "kl": region})
        if response.status_code >= 400 or "result__a" not in response.text:
            response = client.post(DDG_HTML, data={"q": query, "kl": region})
        response.raise_for_status()
        html = response.text

    soup = BeautifulSoup(html, "lxml")
    blocks = soup.select("div.result")
    if not blocks:
        blocks = soup.select("div.results_links")
    hits: list[SearchHit] = []
    for block in tqdm(blocks, desc="DDG results", leave=False):
        link = block.select_one("a.result__a")
        if link is None:
            link = block.select_one("a.result-link")
        if link is None:
            continue
        url = _unwrap_ddg_href(str(link.get("href") or ""))
        if not url.startswith("http"):
            continue
        snippet_el = block.select_one("a.result__snippet")
        if snippet_el is None:
            snippet_el = block.select_one(".result__snippet")
        snippet = snippet_el.get_text(" ", strip=True) if snippet_el else ""
        hits.append(
            SearchHit(
                title=link.get_text(" ", strip=True),
                url=url,
                snippet=snippet,
                source=_domain_of(url),
            )
        )
        if len(hits) >= limit:
            break
    return hits


def search_news(
    query: str,
    max_results: int | None = None,
    region: str = "ru-ru",
) -> list[SearchHit]:
    """Search news-oriented results via DuckDuckGo HTML search.

    Args:
        query: Topic or event query.
        max_results: Soft result limit for returned items.
        region: Regional preference passed to DuckDuckGo.

    Returns:
        News-oriented search hits.
    """

    return search_web(f"{query} новости", max_results=max_results, region=region)


def search_around_url(url: str, max_results: int | None = None) -> list[SearchHit]:
    """Find pages that discuss or cite a given article URL.

    Args:
        url: Seed article URL.
        max_results: Soft result limit.

    Returns:
        Related search hits including the seed page when present.
    """

    domain = _domain_of(url)
    queries = [
        f'"{url}"',
        f"site:{domain}",
        url,
    ]
    seen: set[str] = set()
    merged: list[SearchHit] = []
    soft = max_results if max_results is not None else settings.max_search_results
    per_query = max(3, soft // len(queries))
    for query in queries:
        for hit in search_web(query, max_results=per_query):
            if hit.url in seen:
                continue
            seen.add(hit.url)
            merged.append(hit)
            if len(merged) >= soft:
                return merged
    return merged
