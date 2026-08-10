from urllib.parse import urlparse


from duckduckgo_search import DDGS
from tqdm.auto import tqdm


from models.schemas import SearchHit
from utils.config import settings


def _domain_of(url: str) -> str:
    """Extract a lowercase network location from a URL."""

    netloc = urlparse(url).netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


def search_web(
    query: str,
    max_results: int | None = None,
    region: str = "wt-wt",
) -> list[SearchHit]:
    """Search the public web with DuckDuckGo.

    Args:
        query: Natural language or keyword query.
        max_results: Soft limit, capped by settings.max_search_hard_cap.
        region: DuckDuckGo region code.

    Returns:
        Ranked search hits with title, url and snippet.
    """

    soft = max_results if max_results is not None else settings.max_search_results
    limit = min(max(soft, 1), settings.max_search_hard_cap)
    hits: list[SearchHit] = []
    with DDGS() as ddgs:
        raw = list(ddgs.text(query, region=region, max_results=limit))
    for item in tqdm(raw, desc="DDG results", leave=False):
        url = str(item.get("href") or item.get("link") or "")
        hits.append(
            SearchHit(
                title=str(item.get("title") or ""),
                url=url,
                snippet=str(item.get("body") or item.get("snippet") or ""),
                source=_domain_of(url),
            )
        )
    return hits


def search_news(
    query: str,
    max_results: int | None = None,
    region: str = "ru-ru",
) -> list[SearchHit]:
    """Search news-oriented DuckDuckGo results.

    Args:
        query: Topic or event query.
        max_results: Soft limit for returned items.
        region: DuckDuckGo region code.

    Returns:
        News-oriented search hits.
    """

    soft = max_results if max_results is not None else settings.max_search_results
    limit = min(max(soft, 1), settings.max_search_hard_cap)
    hits: list[SearchHit] = []
    with DDGS() as ddgs:
        raw = list(ddgs.news(query, region=region, max_results=limit))
    for item in tqdm(raw, desc="DDG news", leave=False):
        url = str(item.get("url") or item.get("href") or "")
        hits.append(
            SearchHit(
                title=str(item.get("title") or ""),
                url=url,
                snippet=str(item.get("body") or item.get("excerpt") or ""),
                source=str(item.get("source") or _domain_of(url)),
            )
        )
    return hits


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
