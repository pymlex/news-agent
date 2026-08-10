import json


from models.schemas import (
    ProvenanceGraph,
    SearchHit,
    StanceNote,
    SynthesizedNews,
)
from agent.skills.provenance import build_provenance_graph
from utils.db import db
from utils.ddg_search import search_news, search_web
from utils.zveno import zveno


def synthesize_news(
    topic: str,
    profile_name: str = "default",
    model: str | None = None,
    max_results: int = 20,
) -> SynthesizedNews:
    """Generate a source-visible news article with explicit stances.

    Different outlets and experts keep distinct positions and assessments.
    The accompanying provenance graph is coloured by trust weights from the
    active profile.

    Args:
        topic: Event or question to cover.
        profile_name: Profile controlling trusted weights.
        model: Optional Zveno model slug.
        max_results: Soft search budget.

    Returns:
        Synthesized news package with markdown body and graph.
    """

    trust_map = db.trust_by_domain(profile_name)
    trusted = db.list_trusted_media(profile_name)
    news_hits = search_news(topic, max_results=max_results)
    web_hits = search_web(f"{topic} эксперты мнения", max_results=10)
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
        return score

    hits = sorted(hits, key=rank_key, reverse=True)[:max_results]

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
        "You write Russian news briefs that keep sources visible. "
        "Every factual claim must point to a source. "
        "When experts disagree, present each position separately with an "
        "assessment label. Prefer higher-weight trusted outlets from the "
        "profile when conflict arises, and say so explicitly. "
        "Return JSON with headline, body_markdown, stances. "
        "stances is an array of actor, position, assessment, source_url, "
        "trust_score. body_markdown may include tables and lists."
    )
    user = {
        "topic": topic,
        "trusted_media": trusted_brief,
        "documents": catalog,
        "style": (
            "Telegram-readable Markdown. Keep contested claims attributed. "
            "If an expert is a qualified specialist, prefer them over an "
            "infocoach from social media."
        ),
    }
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
        score = float(item.get("trust_score", 0.5))
        stances.append(
            StanceNote(
                actor=str(item.get("actor") or ""),
                position=str(item.get("position") or ""),
                assessment=str(item.get("assessment") or ""),
                source_url=str(item.get("source_url") or ""),
                trust_score=min(max(score, 0.0), 1.0),
            )
        )

    graph: ProvenanceGraph = build_provenance_graph(
        topic,
        profile_name=profile_name,
        model=model,
        max_results=max_results,
    )

    body = str(payload.get("body_markdown") or "")
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
