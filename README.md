# News Agent

News Agent recovers citation and reinterpretation flows around online stories. A user describes topical preferences in natural language, receives a weighted trusted media list, then inspects an interactive provenance graph coloured by trust. Search runs through DuckDuckGo. Reasoning and writing run through the Zveno AI chat completions API with inexpensive Chinese model slugs such as `qwen/qwen3.7-flash`.

## Pipeline

1. Preference intake stores a named profile in SQLite and asks Zveno AI to rank outlets found by DuckDuckGo. Qualified specialists outrank anonymous social coaches for the stated domain.
2. Provenance search gathers up to twenty hits by default, never more than thirty, and asks the model to emit outlets, articles, events, experts, claims and directed edges of types cites, reposts, reinterprets, attributes, mentions.
3. News synthesis writes Russian Markdown where every contested claim stays attributed, while stance rows keep actor, position, assessment and trust.
4. Morning digest ranks fresh hits by profile weights and returns a table of what is new for the chosen focus.

## Trust colouring

Continuous trust scores map to discrete bands that paint the vis-network canvas:

- very high near $0.85$ and above, deep blue
- high near $0.70$, bright blue
- medium near $0.45$, soft blue
- low near $0.25$, amber
- very low below that band, rose

Edge direction follows the inferred information flow. Double-click opens a node URL when present.

## Interface

Gradio serves a Telegram-like chat with Markdown tables and an interactive HTML graph panel. Profiles and cheap Zveno model slugs are selectable in the header. The same trusted-media builder is also exposed as an MCP stdio server under `mcp_server/server.py`.

## Layout

- `main.py` — Gradio entrypoint
- `models/schemas.py` — Pydantic contracts
- `utils/config.py` — settings from `.env`
- `utils/db.py` — SQLite profiles, trusted media, graphs
- `utils/ddg_search.py` — DuckDuckGo web and news search
- `utils/zveno.py` — Zveno AI client
- `utils/graph_html.py` — interactive blue graph widget
- `agent/orchestrator.py` — routing and tool execution
- `agent/skills/` — trusted media, provenance, synthesis, digest
- `mcp_server/server.py` — MCP tools for trusted media
- `data/` — on-disk SQLite database

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Put `ZVENOAI_API_KEY` into `.env`. Optional keys cover base URL, default model, database path and Gradio bind address.

```bash
python main.py
```

MCP trusted-media server:

```bash
python -m mcp_server.server
```

## Example prompts

- доверенные СМИ про пилатес и сертифицированных физиотерапевтов
- построй граф по этой ссылке https://example.com/story
- собери новость про реформу с позициями экспертов
- утренняя сводка по моим предпочтениям

## Configuration

| Variable | Role |
| --- | --- |
| `ZVENOAI_API_KEY` | Bearer token for Zveno AI |
| `ZVENOAI_BASE_URL` | defaults to `https://api.zveno.ai/v1` |
| `ZVENOAI_MODEL` | defaults to `qwen/qwen3.7-flash` |
| `DATABASE_PATH` | SQLite file under `data/` |
| `MAX_SEARCH_RESULTS` | soft budget, default $20$ |
| `MAX_SEARCH_HARD_CAP` | hard cap, default $30$ |

## References

```bibtex
@misc{news_agent_2026,
  title        = {News Agent: provenance graphs and trusted media profiles},
  author       = {Zyukov, Alex},
  year         = {2026},
  howpublished = {\url{https://github.com/pymlex/news-agent}},
  note         = {DuckDuckGo search, Zveno AI, Gradio}
}
```

The project is under GPL-3.0 license.
