import json
from urllib.parse import urlparse


from models.schemas import Profile, TrustLevel, TrustedOutlet
from utils.db import db
from utils.ddg_search import search_web
from utils.graph_html import score_to_level
from utils.zveno import zveno


def _domain(url: str) -> str:
    netloc = urlparse(url).netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


def build_trusted_media(
    preferences: str,
    profile_name: str = "default",
    region: str = "",
    model: str | None = None,
) -> list[TrustedOutlet]:
    """Build a weighted trusted-media list from natural language preferences.

    The skill searches the web for candidate outlets, then asks Zveno AI to
    rank institutional or expert sources above lifestyle coaches and anonymous
    social accounts for the stated topic.

    Args:
        preferences: Free-form user intent, topics and preferred experts.
        profile_name: Profile that will own the saved list.
        region: Optional geographic focus.
        model: Optional Zveno model slug.

    Returns:
        Trusted outlets persisted under the profile.
    """

    query = preferences.strip()
    if region:
        query = f"{query} {region}".strip()
    search_query = (
        f"{query} reliable news sources journalists experts publications"
    )
    hits = search_web(search_query, max_results=20)
    catalog = [
        {
            "title": h.title,
            "url": h.url,
            "snippet": h.snippet,
            "domain": h.source,
        }
        for h in hits
    ]

    system = (
        "You compile trusted media lists for a news provenance agent. "
        "Prefer qualified domain experts, peer-reviewed outlets, specialised "
        "trade press and established newsrooms over social media coaches, "
        "anonymous channels and clickbait blogs. "
        "Return JSON only with key outlets, an array of objects with fields "
        "name, domain, url, weight in [0,1], reason, topics, trust_level "
        "in very_low|low|medium|high|very_high. "
        "Weight reflects how much the agent should trust this outlet for the "
        "user preferences. Reply language for reason fields is Russian."
    )
    user = {
        "preferences": preferences,
        "region": region,
        "candidates": catalog,
        "instruction": (
            "Select up to 15 outlets. If candidates are weak, invent only "
            "well-known real outlets clearly matching the preference, still "
            "with urls when possible."
        ),
    }
    payload = zveno.chat_json(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
        model=model,
    )
    raw_outlets = payload.get("outlets") if isinstance(payload, dict) else payload
    if not isinstance(raw_outlets, list):
        raw_outlets = []

    outlets: list[TrustedOutlet] = []
    for item in raw_outlets:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "")
        domain = str(item.get("domain") or _domain(url))
        weight = float(item.get("weight", 0.5))
        weight = min(max(weight, 0.0), 1.0)
        level_raw = str(item.get("trust_level") or score_to_level(weight).value)
        allowed = {level.value for level in TrustLevel}
        level = TrustLevel(level_raw) if level_raw in allowed else score_to_level(weight)
        topics = item.get("topics") or []
        if not isinstance(topics, list):
            topics = [str(topics)]
        outlets.append(
            TrustedOutlet(
                name=str(item.get("name") or domain or "outlet"),
                domain=domain,
                url=url,
                weight=weight,
                reason=str(item.get("reason") or ""),
                topics=[str(t) for t in topics],
                trust_level=level,
            )
        )

    profile = Profile(
        name=profile_name,
        preferences=preferences,
        region=region,
        topics=[],
    )
    db.upsert_profile(profile)
    db.replace_trusted_media(profile_name, outlets)
    return outlets


def trusted_media_markdown(outlets: list[TrustedOutlet], profile_name: str) -> str:
    """Format trusted outlets as a Markdown table for Gradio."""

    lines = [
        f"### Доверенные СМИ для профиля `{profile_name}`",
        "",
        "| СМИ | Домен | Вес | Уровень | Почему |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for o in outlets:
        reason = o.reason.replace("|", "/")
        lines.append(
            f"| {o.name} | {o.domain or '—'} | {o.weight:.2f} | "
            f"{o.trust_level.value} | {reason} |"
        )
    return "\n".join(lines)
