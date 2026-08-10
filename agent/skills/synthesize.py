import json
import re


from models.schemas import (
    ProvenanceGraph,
    SearchHit,
    StanceNote,
    SynthesizedNews,
)
from agent.skills.provenance import build_provenance_graph
from utils.db import db
from utils.ddg_search import search_news, search_web
from utils.progress import ProgressCallback, emit
from utils.zveno import zveno


def synthesize_news(
    topic: str,
    profile_name: str = "default",
    model: str | None = None,
    max_results: int = 20,
    on_progress: ProgressCallback | None = None,
) -> SynthesizedNews:
    """Generate a source-visible news article with explicit stances.

    Citations are restricted to retrieved documents only. Empty search results
    produce an explicit refusal instead of invented URLs.

    Args:
        topic: Event or question to cover.
        profile_name: Profile controlling trusted weights.
        model: Optional Zveno model slug.
        max_results: Soft search budget.
        on_progress: Optional short status callback for the chat UI.

    Returns:
        Synthesized news package with markdown body and graph.
    """

    trust_map = db.trust_by_domain(profile_name)
    trusted = db.list_trusted_media(profile_name)
    emit(on_progress, "Ищу источники…")
    news_hits = search_news(topic, max_results=max_results)
    emit(on_progress, f"Нашёл {len(news_hits)} результатов по теме")
    web_hits = search_web(f"{topic} эксперты мнения", max_results=10)
    emit(on_progress, f"Добавил {len(web_hits)} страниц с мнениями экспертов")
    hits: list[SearchHit] = []
    seen: set[str] = set()
    for hit in news_hits + web_hits:
        if hit.url in seen:
            continue
        seen.add(hit.url)
        hits.append(hit)

    def rank_key(hit: SearchHit) -> float:
        domain = hit.source.lower()
        score = trust_map.get(domain, 0.4)
        for key, value in trust_map.items():
            if key and key in domain:
                score = max(score, value)
        academic = (
            "pubmed.ncbi.nlm.nih.gov" in hit.url
            or "doi.org" in hit.url
            or "openalex.org" in hit.url
            or "wikipedia.org" in hit.url
        )
        if academic:
            score = max(score, 0.75)
        return score

    hits = sorted(hits, key=rank_key, reverse=True)[:max_results]
    emit(on_progress, f"Отобрал {len(hits)} источников")
    if not hits:
        emit(on_progress, "Источников нет, ответ без выдуманных ссылок")
        empty = ProvenanceGraph(title=topic, nodes=[], edges=[])
        return SynthesizedNews(
            headline=topic,
            body_markdown=(
                "Открытый поиск не вернул источников по запросу. "
                "Не формирую ответ со ссылками, чтобы не галлюцинировать URL. "
                "Попробуйте переформулировать запрос или повторить позже."
            ),
            sources=[],
            stances=[],
            graph=empty,
        )

    emit(on_progress, f"Читаю: {hits[0].title[:70]}")
    if len(hits) > 1:
        emit(on_progress, f"Также: {hits[1].title[:70]}")

    catalog = [
        {
            "title": h.title,
            "url": h.url,
            "snippet": h.snippet,
            "domain": h.source,
            "trust_hint": rank_key(h),
        }
        for h in hits
    ]
    allowed_urls = {h.url for h in hits}
    trusted_brief = [
        {
            "name": t.name,
            "domain": t.domain,
            "weight": t.weight,
            "reason": t.reason,
        }
        for t in trusted
    ]

    system = (
        "You write Russian briefs that keep sources visible. "
        "You may cite ONLY urls from the documents array. "
        "Never invent DOIs, pubmed links, journal urls or any other urls. "
        "If a claim is not supported by documents, omit it. "
        "When experts disagree, present each position separately. "
        "Prefer higher-weight trusted outlets from the profile when conflict arises. "
        "Return JSON with headline, body_markdown, stances. "
        "stances is an array of actor, position, assessment, source_url, trust_score. "
        "source_url must be empty or one of the document urls. "
        "Do not use emoji."
    )
    user = {
        "topic": topic,
        "trusted_media": trusted_brief,
        "documents": catalog,
        "allowed_urls": sorted(allowed_urls),
        "style": (
            "Telegram-readable Markdown. Keep contested claims attributed. "
            "If an expert is a qualified specialist, prefer them over an "
            "infocoach from social media."
        ),
    }
    emit(on_progress, "Собираю ответ только по найденным источникам…")
    payload = zveno.chat_json(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
        model=model,
    )

    stances: list[StanceNote] = []
    for item in payload.get("stances", []):
        if not isinstance(item, dict):
            continue
        source_url = str(item.get("source_url") or "")
        if source_url and source_url not in allowed_urls:
            source_url = ""
        score = float(item.get("trust_score", 0.5))
        stances.append(
            StanceNote(
                actor=str(item.get("actor") or ""),
                position=str(item.get("position") or ""),
                assessment=str(item.get("assessment") or ""),
                source_url=source_url,
                trust_score=min(max(score, 0.0), 1.0),
            )
        )

    emit(on_progress, "Строю граф цитирований…")
    graph: ProvenanceGraph = build_provenance_graph(
        topic,
        profile_name=profile_name,
        model=model,
        max_results=max_results,
        on_progress=on_progress,
        seed_hits=hits,
    )
    emit(
        on_progress,
        f"Граф готов: {len(graph.nodes)} узлов, {len(graph.edges)} связей",
    )

    body = str(payload.get("body_markdown") or "")
    found_urls = set(re.findall(r"https?://[^\s\]\)\"<>]+", body))
    for bad in found_urls - allowed_urls:
        body = body.replace(bad, "")

    if stances:
        rows = [
            "",
            "### Позиции и оценки",
            "",
            "| Кто | Позиция | Оценка | Trust |",
            "| --- | --- | --- | ---: |",
        ]
        for s in stances:
            rows.append(
                f"| {s.actor} | {s.position} | {s.assessment} | {s.trust_score:.2f} |"
            )
        body = body.rstrip() + "\n" + "\n".join(rows)

    return SynthesizedNews(
        headline=str(payload.get("headline") or topic),
        body_markdown=body,
        sources=hits,
        stances=stances,
        graph=graph,
    )
