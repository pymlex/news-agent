import json
import re
from urllib.parse import urlparse


from models.schemas import (
    EdgeKind,
    GraphEdge,
    GraphNode,
    NodeKind,
    ProvenanceGraph,
    SearchHit,
    TrustLevel,
)
from utils.db import db
from utils.ddg_search import search_around_url, search_news, search_web
from utils.graph_html import score_to_level
from utils.progress import ProgressCallback, emit
from utils.zveno import zveno


_URL_RE = re.compile(r"https?://[^\s<>\"']+")


def extract_url(text: str) -> str | None:
    """Return the first HTTP URL found in free text."""

    match = _URL_RE.search(text)
    return match.group(0) if match else None


def _domain(url: str) -> str:
    netloc = urlparse(url).netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


def _trust_for_hit(hit: SearchHit, trust_map: dict[str, float]) -> float:
    domain = hit.source.lower() or _domain(hit.url)
    if domain in trust_map:
        return trust_map[domain]
    for key, value in trust_map.items():
        if key and key in domain:
            return value
        if key and key in hit.title.lower():
            return value
    return 0.4


def build_provenance_graph(
    query_or_url: str,
    profile_name: str = "default",
    model: str | None = None,
    max_results: int = 20,
    on_progress: ProgressCallback | None = None,
) -> ProvenanceGraph:
    """Build a citation and reinterpretation graph around a topic or URL.

    Args:
        query_or_url: Topic text or article URL.
        profile_name: Profile whose trusted weights colour the graph.
        model: Optional Zveno model slug.
        max_results: Soft search budget, hard-capped elsewhere.
        on_progress: Optional short status callback for the chat UI.

    Returns:
        Provenance graph with outlets, articles, experts and citation edges.
    """

    trust_map = db.trust_by_domain(profile_name)
    seed_url = extract_url(query_or_url)
    if seed_url:
        emit(on_progress, "Разбираю ссылку и ищу пересказы…")
        hits = search_around_url(seed_url, max_results=max_results)
        topic = query_or_url.replace(seed_url, "").strip() or seed_url
        related = search_web(
            f"источник цитирует {topic}",
            max_results=max(5, max_results // 2),
        )
        for hit in related:
            if all(hit.url != existing.url for existing in hits):
                hits.append(hit)
    else:
        topic = query_or_url.strip()
        emit(on_progress, "Ищу материалы для графа…")
        news_hits = search_news(topic, max_results=max_results)
        web_hits = search_web(
            f"{topic} источник цитата",
            max_results=max(5, max_results // 2),
        )
        hits = []
        seen: set[str] = set()
        for hit in news_hits + web_hits:
            if hit.url in seen:
                continue
            seen.add(hit.url)
            hits.append(hit)
    emit(on_progress, f"Для графа собрал {len(hits)} страниц")
    if hits:
        emit(on_progress, f"Смотрю: {hits[0].title[:70]}")

    catalog = []
    for idx, hit in enumerate(hits[:max_results]):
        score = _trust_for_hit(hit, trust_map)
        catalog.append(
            {
                "id": f"a{idx}",
                "title": hit.title,
                "url": hit.url,
                "snippet": hit.snippet,
                "domain": hit.source or _domain(hit.url),
                "trust_score": score,
            }
        )

    system = (
        "You reconstruct news provenance graphs. "
        "Nodes may be outlet, article, event, expert, claim. "
        "Edges may be cites, reposts, reinterprets, attributes, mentions. "
        "Infer likely citation and reinterpretation flows from titles and "
        "snippets. Prefer edges grounded in explicit evidence phrases. "
        "Return JSON with keys title, nodes, edges. "
        "Each node needs id, label, kind, url, trust_score in [0,1]. "
        "Each edge needs source, target, kind, weight in [0,1], evidence. "
        "Keep labels concise. Russian evidence strings are preferred."
    )
    user = {
        "seed": query_or_url,
        "profile_trust_hints": trust_map,
        "documents": catalog,
        "limits": {"max_nodes": 30, "expected_typical": 7},
    }
    emit(on_progress, "Связываю цитирования и переинтерпретации…")
    payload = zveno.chat_json(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
        model=model,
    )

    nodes: list[GraphNode] = []
    for item in payload.get("nodes", []):
        if not isinstance(item, dict):
            continue
        score = float(item.get("trust_score", 0.5))
        score = min(max(score, 0.0), 1.0)
        domain = _domain(str(item.get("url") or ""))
        if domain in trust_map:
            score = max(score, trust_map[domain])
        kind_raw = str(item.get("kind") or "article")
        kind_allowed = {kind.value for kind in NodeKind}
        kind = NodeKind(kind_raw) if kind_raw in kind_allowed else NodeKind.ARTICLE
        level = score_to_level(score)
        nodes.append(
            GraphNode(
                id=str(item.get("id")),
                label=str(item.get("label") or item.get("id")),
                kind=kind,
                url=str(item.get("url") or ""),
                trust_score=score,
                trust_level=level,
                meta={"domain": domain},
            )
        )

    if not nodes:
        for doc in catalog:
            score = float(doc["trust_score"])
            nodes.append(
                GraphNode(
                    id=doc["id"],
                    label=doc["title"][:72] or doc["domain"],
                    kind=NodeKind.ARTICLE,
                    url=doc["url"],
                    trust_score=score,
                    trust_level=score_to_level(score),
                    meta={"domain": doc["domain"]},
                )
            )
            outlet_id = f"o_{doc['domain']}"
            if not any(n.id == outlet_id for n in nodes):
                nodes.append(
                    GraphNode(
                        id=outlet_id,
                        label=doc["domain"] or "outlet",
                        kind=NodeKind.OUTLET,
                        url=f"https://{doc['domain']}" if doc["domain"] else "",
                        trust_score=score,
                        trust_level=score_to_level(score),
                    )
                )

    node_ids = {n.id for n in nodes}
    edges: list[GraphEdge] = []
    for item in payload.get("edges", []):
        if not isinstance(item, dict):
            continue
        source = str(item.get("source"))
        target = str(item.get("target"))
        if source not in node_ids or target not in node_ids:
            continue
        kind_raw = str(item.get("kind") or "cites")
        edge_allowed = {kind.value for kind in EdgeKind}
        kind = EdgeKind(kind_raw) if kind_raw in edge_allowed else EdgeKind.CITES
        weight = float(item.get("weight", 0.5))
        edges.append(
            GraphEdge(
                source=source,
                target=target,
                kind=kind,
                weight=min(max(weight, 0.0), 1.0),
                evidence=str(item.get("evidence") or ""),
            )
        )

    if not edges and len(nodes) >= 2:
        articles = [n for n in nodes if n.kind == NodeKind.ARTICLE]
        outlets = [n for n in nodes if n.kind == NodeKind.OUTLET]
        for article in articles:
            domain = str(article.meta.get("domain") or _domain(article.url))
            outlet = next((o for o in outlets if o.label == domain), None)
            if outlet:
                edges.append(
                    GraphEdge(
                        source=outlet.id,
                        target=article.id,
                        kind=EdgeKind.ATTRIBUTES,
                        weight=0.6,
                        evidence="публикация на площадке",
                    )
                )

    graph = ProvenanceGraph(
        title=str(payload.get("title") or topic)[:120],
        nodes=nodes,
        edges=edges,
    )
    db.save_graph(graph, profile_name=profile_name)
    return graph
