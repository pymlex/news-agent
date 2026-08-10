import json
from datetime import datetime


from models.schemas import DigestItem, MorningDigest
from utils.db import db
from utils.ddg_search import search_news, search_web
from utils.progress import ProgressCallback, emit
from utils.zveno import zveno


def morning_digest(
    profile_name: str = "default",
    focus: str = "",
    model: str | None = None,
    max_results: int = 20,
    on_progress: ProgressCallback | None = None,
) -> MorningDigest:
    """Build an on-demand morning digest for a profile's preferences.

    Args:
        profile_name: Profile with preferences and trusted media.
        focus: Optional extra region or topic override.
        model: Optional Zveno model slug.
        max_results: Soft search budget.
        on_progress: Optional short status callback for the chat UI.

    Returns:
        Morning digest with markdown ready for Gradio.
    """

    profile = db.get_profile(profile_name)
    preferences = profile.preferences if profile else ""
    region = profile.region if profile else ""
    trusted = db.list_trusted_media(profile_name)
    trust_map = db.trust_by_domain(profile_name)

    query_bits = [preferences, region, focus, "новости сегодня"]
    query = " ".join(bit for bit in query_bits if bit).strip()
    emit(on_progress, "Собираю свежие материалы для сводки…")
    news_hits = search_news(query or "новости", max_results=max_results)
    web_hits = search_web(query or "новости", max_results=10)
    emit(on_progress, f"Нашёл {len(news_hits) + len(web_hits)} материалов")

    catalog = []
    seen: set[str] = set()
    for hit in news_hits + web_hits:
        if hit.url in seen:
            continue
        seen.add(hit.url)
        domain = hit.source.lower()
        score = trust_map.get(domain, 0.4)
        for key, value in trust_map.items():
            if key and key in domain:
                score = max(score, value)
        catalog.append(
            {
                "title": hit.title,
                "url": hit.url,
                "snippet": hit.snippet,
                "outlet": hit.source,
                "trust_score": score,
            }
        )
    catalog = sorted(catalog, key=lambda x: x["trust_score"], reverse=True)[:max_results]

    system = (
        "You write a concise Russian morning digest. "
        "Prioritise items from higher-weight trusted outlets when available. "
        "Return JSON with intro and items. "
        "Each item needs title, summary, url, outlet, trust_score."
    )
    user = {
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "preferences": preferences,
        "region": region,
        "focus": focus,
        "trusted_media": [
            {"name": t.name, "domain": t.domain, "weight": t.weight}
            for t in trusted
        ],
        "candidates": catalog,
    }
    emit(on_progress, "Формирую утреннюю сводку…")
    payload = zveno.chat_json(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
        model=model,
    )

    items: list[DigestItem] = []
    for item in payload.get("items", []):
        if not isinstance(item, dict):
            continue
        score = float(item.get("trust_score", 0.5))
        items.append(
            DigestItem(
                title=str(item.get("title") or ""),
                summary=str(item.get("summary") or ""),
                url=str(item.get("url") or ""),
                outlet=str(item.get("outlet") or ""),
                trust_score=min(max(score, 0.0), 1.0),
            )
        )

    lines = [
        f"## Утренняя сводка · `{profile_name}`",
        "",
        str(payload.get("intro") or ""),
        "",
        "| Тема | СМИ | Trust | Кратко |",
        "| --- | --- | ---: | --- |",
    ]
    for item in items:
        summary = item.summary.replace("|", "/")
        title = item.title
        if item.url:
            title = f"[{item.title}]({item.url})"
        lines.append(
            f"| {title} | {item.outlet} | {item.trust_score:.2f} | {summary} |"
        )

    return MorningDigest(
        profile_name=profile_name,
        focus=focus or preferences or region,
        intro=str(payload.get("intro") or ""),
        items=items,
        markdown="\n".join(lines),
    )
