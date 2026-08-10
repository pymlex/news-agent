import xml.etree.ElementTree as ET
from urllib.parse import urlparse


import httpx
from tqdm.auto import tqdm


from models.schemas import SearchHit
from utils.config import settings


AGENT_UA = (
    "news-agent/1.0 (https://github.com/pymlex/news-agent; "
    "research tool; python-httpx)"
)
HEADERS = {"User-Agent": AGENT_UA, "Accept": "*/*"}


def _domain_of(url: str) -> str:
    """Extract a lowercase network location from a URL."""

    netloc = urlparse(url).netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


def _dedupe(hits: list[SearchHit], limit: int) -> list[SearchHit]:
    seen: set[str] = set()
    out: list[SearchHit] = []
    for hit in hits:
        key = hit.url.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(hit)
        if len(out) >= limit:
            break
    return out


def _google_news(client: httpx.Client, query: str, limit: int) -> list[SearchHit]:
    response = client.get(
        "https://news.google.com/rss/search",
        params={"q": query, "hl": "ru", "gl": "RU", "ceid": "RU:ru"},
    )
    response.raise_for_status()
    root = ET.fromstring(response.text)
    hits: list[SearchHit] = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        url = (item.findtext("link") or "").strip()
        snippet = (item.findtext("description") or "").strip()
        source_el = item.find("source")
        source = (source_el.text or "").strip() if source_el is not None else _domain_of(url)
        if not title or not url:
            continue
        hits.append(
            SearchHit(title=title, url=url, snippet=snippet, source=source or _domain_of(url))
        )
        if len(hits) >= limit:
            break
    return hits


def _openalex(client: httpx.Client, query: str, limit: int) -> list[SearchHit]:
    response = client.get(
        "https://api.openalex.org/works",
        params={"search": query, "per-page": limit},
        headers={**HEADERS, "Accept": "application/json"},
    )
    response.raise_for_status()
    payload = response.json()
    hits: list[SearchHit] = []
    for work in payload.get("results", []):
        title = str(work.get("display_name") or "").strip()
        loc = work.get("primary_location") or {}
        url = str(loc.get("landing_page_url") or work.get("doi") or work.get("id") or "")
        if url.startswith("10."):
            url = "https://doi.org/" + url
        if isinstance(work.get("doi"), str) and not url.startswith("http"):
            url = "https://doi.org/" + work["doi"].replace("https://doi.org/", "")
        snippet = ""
        concepts = work.get("concepts") or []
        if concepts:
            snippet = ", ".join(
                str(c.get("display_name") or "") for c in concepts[:4] if c.get("display_name")
            )
        if not title or not url.startswith("http"):
            continue
        hits.append(
            SearchHit(
                title=title,
                url=url,
                snippet=snippet,
                source=_domain_of(url) or "openalex",
            )
        )
    return hits


def _pubmed(client: httpx.Client, query: str, limit: int) -> list[SearchHit]:
    search = client.get(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
        params={"db": "pubmed", "term": query, "retmax": limit, "retmode": "json"},
    )
    search.raise_for_status()
    ids = search.json().get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []
    summary = client.get(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
        params={"db": "pubmed", "id": ",".join(ids), "retmode": "json"},
    )
    summary.raise_for_status()
    result = summary.json().get("result", {})
    hits: list[SearchHit] = []
    for pmid in ids:
        item = result.get(pmid) or {}
        title = str(item.get("title") or "").strip()
        url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        source = str(item.get("fulljournalname") or item.get("source") or "pubmed")
        snippet = str(item.get("sortpubdate") or item.get("pubdate") or "")
        if not title:
            continue
        hits.append(SearchHit(title=title, url=url, snippet=snippet, source=source))
    return hits


def _wikipedia(client: httpx.Client, query: str, lang: str, limit: int) -> list[SearchHit]:
    response = client.get(
        f"https://{lang}.wikipedia.org/w/api.php",
        params={
            "action": "opensearch",
            "search": query,
            "limit": limit,
            "namespace": 0,
            "format": "json",
        },
    )
    response.raise_for_status()
    payload = response.json()
    titles = payload[1] if len(payload) > 1 else []
    descs = payload[2] if len(payload) > 2 else []
    urls = payload[3] if len(payload) > 3 else []
    hits: list[SearchHit] = []
    for idx, title in enumerate(titles):
        url = urls[idx] if idx < len(urls) else ""
        snippet = descs[idx] if idx < len(descs) else ""
        if not title or not url:
            continue
        hits.append(
            SearchHit(
                title=str(title),
                url=str(url),
                snippet=str(snippet),
                source=f"{lang}.wikipedia.org",
            )
        )
    return hits


def _crossref(client: httpx.Client, query: str, limit: int) -> list[SearchHit]:
    response = client.get(
        "https://api.crossref.org/works",
        params={"query": query, "rows": limit},
    )
    response.raise_for_status()
    items = response.json().get("message", {}).get("items", [])
    hits: list[SearchHit] = []
    for item in items:
        titles = item.get("title") or []
        title = str(titles[0] if titles else "").strip()
        url = str(item.get("URL") or "")
        if item.get("DOI") and not url:
            url = "https://doi.org/" + str(item["DOI"])
        container = item.get("container-title") or []
        source = str(container[0] if container else "crossref")
        snippet = str(item.get("abstract") or "")[:280]
        if not title or not url.startswith("http"):
            continue
        hits.append(SearchHit(title=title, url=url, snippet=snippet, source=source))
    return hits


def search_web(
    query: str,
    max_results: int | None = None,
    region: str = "wt-wt",
) -> list[SearchHit]:
    """Search the public web through multiple open APIs.

    DuckDuckGo HTML is often blocked by anomaly checks, so the agent gathers
    sources from Google News RSS, OpenAlex, PubMed, Crossref and Wikipedia.

    Args:
        query: Natural language or keyword query.
        max_results: Soft limit, capped by settings.max_search_hard_cap.
        region: Kept for API compatibility with callers.

    Returns:
        Ranked search hits with title, url and snippet.
    """

    soft = max_results if max_results is not None else settings.max_search_results
    limit = min(max(soft, 1), settings.max_search_hard_cap)
    per_backend = max(3, limit // 2)
    collected: list[SearchHit] = []
    with httpx.Client(timeout=45.0, follow_redirects=True, headers=HEADERS) as client:
        backends = [
            ("OpenAlex", lambda: _openalex(client, query, per_backend)),
            ("PubMed", lambda: _pubmed(client, query, per_backend)),
            ("Crossref", lambda: _crossref(client, query, per_backend)),
            ("Wikipedia RU", lambda: _wikipedia(client, query, "ru", per_backend)),
            ("Wikipedia EN", lambda: _wikipedia(client, query, "en", per_backend)),
            ("Google News", lambda: _google_news(client, query, per_backend)),
        ]
        for name, getter in tqdm(backends, desc="Search backends"):
            batch = getter()
            collected.extend(batch)
    return _dedupe(collected, limit)


def search_news(
    query: str,
    max_results: int | None = None,
    region: str = "ru-ru",
) -> list[SearchHit]:
    """Search news-oriented results via Google News and related APIs.

    Args:
        query: Topic or event query.
        max_results: Soft result limit for returned items.
        region: Regional preference kept for compatibility.

    Returns:
        News-oriented search hits.
    """

    soft = max_results if max_results is not None else settings.max_search_results
    limit = min(max(soft, 1), settings.max_search_hard_cap)
    with httpx.Client(timeout=45.0, follow_redirects=True, headers=HEADERS) as client:
        news = _google_news(client, query, limit)
        wiki = _wikipedia(client, query, "ru", max(3, limit // 3))
        papers = _openalex(client, query, max(3, limit // 3))
    return _dedupe(news + wiki + papers, limit)


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
        url,
        domain,
        f"{domain} review",
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
