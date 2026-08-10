import json
import re
from typing import Any


from agent.skills.digest import morning_digest
from agent.skills.provenance import build_provenance_graph, extract_url
from agent.skills.synthesize import synthesize_news
from agent.skills.trusted_media import build_trusted_media, trusted_media_markdown
from models.schemas import AgentReply, Profile
from utils.db import db
from utils.graph_html import render_graph_html
from utils.zveno import CHEAP_MODELS, zveno


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "build_trusted_media",
            "description": (
                "Create and save a weighted trusted media list from natural "
                "language preferences about topics, regions and experts."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "preferences": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["preferences"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "build_provenance_graph",
            "description": (
                "Search the web and build a citation or reinterpretation "
                "graph for a topic or article URL."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query_or_url": {"type": "string"},
                    "max_results": {"type": "integer"},
                },
                "required": ["query_or_url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "synthesize_news",
            "description": (
                "Generate a source-visible news text with explicit positions "
                "and assessments, plus a trust-coloured provenance graph."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string"},
                    "max_results": {"type": "integer"},
                },
                "required": ["topic"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "morning_digest",
            "description": (
                "On-demand morning digest of what is new for the profile "
                "preferences and optional focus region or topic."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "focus": {"type": "string"},
                    "max_results": {"type": "integer"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_trusted_media",
            "description": "Show the trusted media table for the active profile.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


class NewsAgent:
    """Tool-using news provenance agent backed by Zveno AI and DuckDuckGo."""

    def __init__(self) -> None:
        self.profile_name = "default"
        self.model = CHEAP_MODELS[0]
        self.last_graph_html = self._empty_graph_html()


    def _empty_graph_html(self) -> str:
        return (
            "<div style='border-radius:24px;padding:28px;background:linear-gradient"
            "(160deg,#EFF6FF,#DBEAFE);color:#1E3A8A;font-family:Manrope,Segoe UI,"
            "sans-serif;border:1px solid #BFDBFE;'>"
            "<div style='font-weight:700;font-size:18px;'>Граф источников</div>"
            "<div style='margin-top:8px;opacity:0.85;'>"
            "Отправьте тему, ссылку или запрос на доверенные СМИ."
            "</div></div>"
        )


    def set_profile(self, profile_name: str) -> None:
        """Switch the active preference profile."""

        name = profile_name.strip() or "default"
        self.profile_name = name
        if db.get_profile(name) is None:
            db.upsert_profile(Profile(name=name))


    def set_model(self, model: str) -> None:
        """Switch the active cheap Zveno model slug."""

        self.model = model or CHEAP_MODELS[0]


    def _run_tool(self, name: str, arguments: dict[str, Any]) -> AgentReply:
        if name == "build_trusted_media":
            outlets = build_trusted_media(
                preferences=str(arguments.get("preferences") or ""),
                profile_name=self.profile_name,
                region=str(arguments.get("region") or ""),
                model=self.model,
            )
            return AgentReply(
                markdown=trusted_media_markdown(outlets, self.profile_name),
                graph_html=self.last_graph_html,
            )

        if name == "list_trusted_media":
            outlets = db.list_trusted_media(self.profile_name)
            if not outlets:
                return AgentReply(
                    markdown=(
                        "Список доверенных СМИ пуст. Опишите тематику и "
                        "предпочтительных экспертов обычным языком."
                    ),
                    graph_html=self.last_graph_html,
                )
            return AgentReply(
                markdown=trusted_media_markdown(outlets, self.profile_name),
                graph_html=self.last_graph_html,
            )

        if name == "build_provenance_graph":
            query = str(arguments.get("query_or_url") or "")
            max_results = int(arguments.get("max_results") or 20)
            max_results = min(max(max_results, 1), 30)
            graph = build_provenance_graph(
                query,
                profile_name=self.profile_name,
                model=self.model,
                max_results=max_results,
            )
            graph_html = render_graph_html(graph)
            self.last_graph_html = graph_html
            lines = [
                f"## Граф происхождения: {graph.title}",
                "",
                f"Узлов: **{len(graph.nodes)}**, рёбер: **{len(graph.edges)}**.",
                "",
                "| Узел | Тип | Trust | URL |",
                "| --- | --- | ---: | --- |",
            ]
            for node in graph.nodes[:30]:
                url = f"[link]({node.url})" if node.url else "—"
                lines.append(
                    f"| {node.label} | {node.kind.value} | {node.trust_score:.2f} | {url} |"
                )
            return AgentReply(
                markdown="\n".join(lines),
                graph_html=graph_html,
                graph=graph,
            )

        if name == "synthesize_news":
            topic = str(arguments.get("topic") or "")
            max_results = int(arguments.get("max_results") or 20)
            max_results = min(max(max_results, 1), 30)
            package = synthesize_news(
                topic,
                profile_name=self.profile_name,
                model=self.model,
                max_results=max_results,
            )
            graph_html = ""
            if package.graph is not None:
                graph_html = render_graph_html(package.graph)
                self.last_graph_html = graph_html
            md = f"## {package.headline}\n\n{package.body_markdown}"
            if package.sources:
                md += "\n\n### Источники\n\n"
                md += "| Заголовок | СМИ | URL |\n| --- | --- | --- |\n"
                for src in package.sources[:20]:
                    title = src.title.replace("|", "/")
                    md += f"| {title} | {src.source} | [open]({src.url}) |\n"
            return AgentReply(
                markdown=md,
                graph_html=graph_html or self.last_graph_html,
                graph=package.graph,
            )

        if name == "morning_digest":
            digest = morning_digest(
                profile_name=self.profile_name,
                focus=str(arguments.get("focus") or ""),
                model=self.model,
                max_results=min(max(int(arguments.get("max_results") or 20), 1), 30),
            )
            return AgentReply(
                markdown=digest.markdown,
                graph_html=self.last_graph_html,
            )

        return AgentReply(
            markdown=f"Неизвестный инструмент: `{name}`",
            graph_html=self.last_graph_html,
        )


    def _heuristic_route(self, text: str) -> AgentReply | None:
        lowered = text.lower()
        if any(
            key in lowered
            for key in (
                "доверен",
                "trusted",
                "предпочитаю",
                "профиль",
                "мне ближе",
                "эксперт",
            )
        ) and any(
            key in lowered
            for key in ("сми", "источник", "медиа", "издание", "канал", "создай", "собери")
        ):
            return self._run_tool(
                "build_trusted_media",
                {"preferences": text, "region": ""},
            )
        if any(key in lowered for key in ("утренн", "сводка", "digest", "что нового")):
            return self._run_tool("morning_digest", {"focus": text})
        if extract_url(text) or any(
            key in lowered for key in ("граф", "откуда", "цепочк", "цитир", "provenance")
        ):
            return self._run_tool("build_provenance_graph", {"query_or_url": text})
        if any(
            key in lowered
            for key in ("сгенерируй новость", "напиши новость", "собери новость", "синтез")
        ):
            return self._run_tool("synthesize_news", {"topic": text})
        return None


    def _parse_tool_call_from_text(self, content: str) -> tuple[str, dict[str, Any]] | None:
        match = re.search(r"\{[\s\S]*\}", content)
        if not match:
            return None
        payload = json.loads(match.group(0))
        if not isinstance(payload, dict):
            return None
        name = payload.get("tool") or payload.get("name")
        arguments = payload.get("arguments") or payload.get("args") or {}
        if name and isinstance(arguments, dict):
            return str(name), arguments
        return None


    def handle(self, user_text: str) -> AgentReply:
        """Answer one user message with Markdown and optional graph HTML.

        Args:
            user_text: Telegram-style user utterance.

        Returns:
            Agent reply for Gradio rendering.
        """

        text = user_text.strip()
        if not text:
            return AgentReply(
                markdown="Напишите тему, ссылку или предпочтения по СМИ.",
                graph_html=self.last_graph_html,
            )

        routed = self._heuristic_route(text)
        if routed is not None:
            return routed

        profile = db.get_profile(self.profile_name)
        trusted = db.list_trusted_media(self.profile_name)
        system = (
            "Ты новостной агент происхождения источников. "
            "Отвечай по-русски. "
            "Доступные инструменты: build_trusted_media, build_provenance_graph, "
            "synthesize_news, morning_digest, list_trusted_media. "
            "Если нужен инструмент, верни только JSON вида "
            '{"tool":"name","arguments":{...}}. '
            "Если достаточно обычного ответа, верни Markdown без JSON. "
            "Граф строится поиском по интернету. "
            "Квалифицированный специалист важнее инфокоуча из соцсети."
        )
        context = {
            "profile": self.profile_name,
            "preferences": profile.preferences if profile else "",
            "trusted_count": len(trusted),
            "user_message": text,
        }
        data = zveno.chat(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
            ],
            model=self.model,
            temperature=0.2,
            tools=TOOLS,
            tool_choice="auto",
        )
        message = data["choices"][0]["message"]
        tool_calls = message.get("tool_calls") or []
        if tool_calls:
            call = tool_calls[0]
            fn = call.get("function") or {}
            name = str(fn.get("name") or "")
            raw_args = fn.get("arguments") or "{}"
            arguments = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            return self._run_tool(name, arguments or {})

        content = str(message.get("content") or "")
        parsed = self._parse_tool_call_from_text(content)
        if parsed is not None:
            name, arguments = parsed
            return self._run_tool(name, arguments)

        return AgentReply(markdown=content, graph_html=self.last_graph_html)


agent = NewsAgent()
