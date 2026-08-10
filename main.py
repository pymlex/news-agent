import gradio as gr


from agent.orchestrator import agent
from utils.config import settings
from utils.db import db
from utils.zveno import CHEAP_MODELS


CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@500;600;700&display=swap');

:root, .dark, body, .gradio-container {
  color-scheme: dark !important;
}

html, body, .gradio-container {
  background: #020617 !important;
  color: #E2E8F0 !important;
  font-family: Manrope, 'Segoe UI', sans-serif !important;
}

.gradio-container {
  max-width: 1480px !important;
}

.gradio-container {
  --body-background-fill: #020617 !important;
  --background-fill-primary: #0B1220 !important;
  --background-fill-secondary: #111827 !important;
  --block-background-fill: transparent !important;
  --block-border-color: transparent !important;
  --border-color-primary: #2A3348 !important;
  --body-text-color: #E2E8F0 !important;
  --body-text-color-subdued: #94A3B8 !important;
  --input-background-fill: #0F172A !important;
  --input-border-color: #2A3348 !important;
  --input-placeholder-color: #64748B !important;
  --link-text-color: #93C5FD !important;
}

footer {
  color: #64748B !important;
}

#na-app {
  background: linear-gradient(165deg, #020617 0%, #0B1220 50%, #111827 100%);
  border-radius: 24px;
  padding: 20px 22px 16px;
  border: 1px solid #252E3F;
  gap: 14px !important;
}

#na-title h1 {
  color: #F8FAFC !important;
  margin-bottom: 4px !important;
}

#na-title p, #na-title .md p {
  color: #94A3B8 !important;
  font-weight: 500 !important;
}

.na-chip {
  display: inline-block;
  background: #172033;
  color: #BFDBFE;
  border-radius: 999px;
  padding: 5px 11px;
  font-size: 12px;
  margin-right: 6px;
  border: 1px solid #2A3348;
}

#na-toolbar {
  gap: 12px !important;
}

#na-toolbar .block {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
}

#na-toolbar label, #na-toolbar .label-wrap span {
  color: #94A3B8 !important;
  font-size: 12px !important;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

#na-toolbar .wrap-inner,
#na-toolbar textarea,
#na-toolbar input {
  background: #0F172A !important;
  border: 1px solid #2A3348 !important;
  border-radius: 14px !important;
  min-height: 44px !important;
  color: #F8FAFC !important;
  box-shadow: none !important;
}

#na-toolbar .wrap-inner {
  padding: 0 12px !important;
}

#na-toolbar button {
  min-height: 44px !important;
  border-radius: 14px !important;
  margin-top: 22px !important;
}

#na-main {
  gap: 12px !important;
  align-items: stretch !important;
}

#na-chatbot, #na-graph {
  border-radius: 18px !important;
  border: 1px solid #2A3348 !important;
  background: #0B1220 !important;
  overflow: hidden !important;
}

#na-chatbot .bubble-wrap,
#na-chatbot .message-wrap,
#na-chatbot > div {
  background: #0B1220 !important;
}

#na-chatbot .bot, #na-chatbot [data-testid="bot"] {
  background: #111827 !important;
  border: 1px solid #2A3348 !important;
  border-radius: 16px !important;
  color: #E2E8F0 !important;
}

#na-chatbot .user, #na-chatbot [data-testid="user"] {
  background: #172033 !important;
  border: 1px solid #2A3348 !important;
  border-radius: 16px !important;
  color: #E2E8F0 !important;
}

.prose, .prose *, .markdown-body, .markdown-body *, #na-status {
  color: #E2E8F0 !important;
}

.prose th, .prose td, .markdown-body th, .markdown-body td {
  border-color: #2A3348 !important;
  color: #E2E8F0 !important;
}

#na-composer .block {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
}

#na-composer textarea {
  background: #0F172A !important;
  border: 1px solid #2A3348 !important;
  border-radius: 16px !important;
  color: #F8FAFC !important;
  min-height: 72px !important;
}

#na-composer button {
  border-radius: 14px !important;
  min-height: 44px !important;
}

button.primary, .primary {
  background: #2563EB !important;
  border: 1px solid #3B4A63 !important;
  color: #F8FAFC !important;
}

button.secondary, .secondary {
  background: #111827 !important;
  border: 1px solid #2A3348 !important;
  color: #E2E8F0 !important;
}

ul.options, .options, [role="listbox"] {
  background: #0F172A !important;
  border: 1px solid #2A3348 !important;
  color: #E2E8F0 !important;
}

ul.options li, [role="option"] {
  color: #E2E8F0 !important;
}
"""


def _profile_choices() -> list[str]:
    names = [p.name for p in db.list_profiles()]
    if "default" not in names:
        names = ["default", *names]
    return names


def on_profile_change(profile_name: str) -> str:
    agent.set_profile(profile_name)
    return f"Профиль: **{profile_name}**"


def on_model_change(model_name: str) -> str:
    agent.set_model(model_name)
    return f"Модель: `{model_name}`"


def respond(
    message: str,
    history: list[dict],
    profile_name: str,
    model_name: str,
):
    agent.set_profile(profile_name)
    agent.set_model(model_name)
    reply = agent.handle(message)
    history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": reply.markdown},
    ]
    return history, reply.graph_html, ""


def run_digest(profile_name: str, model_name: str, history: list[dict]):
    agent.set_profile(profile_name)
    agent.set_model(model_name)
    reply = agent.handle("утренняя сводка по моим предпочтениям")
    history = history + [
        {"role": "user", "content": "утренняя сводка"},
        {"role": "assistant", "content": reply.markdown},
    ]
    return history, reply.graph_html


def create_profile(new_name: str, current: str):
    name = (new_name or "").strip() or current or "default"
    agent.set_profile(name)
    choices = _profile_choices()
    if name not in choices:
        choices.append(name)
    return (
        gr.update(choices=choices, value=name),
        "",
        f"Профиль: **{name}**",
    )


def build_ui() -> gr.Blocks:
    default_model = (
        settings.zvenoai_model
        if settings.zvenoai_model in CHEAP_MODELS
        else CHEAP_MODELS[0]
    )
    with gr.Blocks(fill_height=True) as demo:
        with gr.Column(elem_id="na-app"):
            gr.Markdown(
                """
# News Agent
<span class="na-chip">Zveno</span>
<span class="na-chip">DuckDuckGo</span>
<span class="na-chip">Graph</span>

Доверенные СМИ, граф цитирований, новость с источниками, утренняя сводка.
                """,
                elem_id="na-title",
            )

            with gr.Row(elem_id="na-toolbar"):
                profile = gr.Dropdown(
                    choices=_profile_choices(),
                    value="default",
                    label="Профиль",
                    interactive=True,
                    scale=1,
                    container=True,
                )
                model = gr.Dropdown(
                    choices=CHEAP_MODELS,
                    value=default_model,
                    label="Модель",
                    interactive=True,
                    scale=2,
                    container=True,
                )

            with gr.Row(elem_id="na-toolbar"):
                new_profile = gr.Textbox(
                    label="Создать профиль",
                    placeholder="pilates, силовые, медицина",
                    scale=4,
                    container=True,
                )
                create_btn = gr.Button("Создать", variant="secondary", scale=1)

            status = gr.Markdown("Профиль: **default**", elem_id="na-status")

            with gr.Row(elem_id="na-main", equal_height=True):
                chatbot = gr.Chatbot(
                    elem_id="na-chatbot",
                    label="Диалог",
                    height=560,
                    render_markdown=True,
                    layout="bubble",
                    scale=1,
                )
                graph_html = gr.HTML(
                    value=agent.last_graph_html,
                    elem_id="na-graph",
                    scale=1,
                )

            with gr.Row(elem_id="na-composer"):
                user_input = gr.Textbox(
                    elem_id="na-input",
                    placeholder=(
                        "доверенные СМИ про пилатес, ссылка на новость, "
                        "тема для графа или синтез новости"
                    ),
                    scale=5,
                    lines=2,
                    show_label=False,
                    container=True,
                )
                send_btn = gr.Button("Отправить", variant="primary", scale=1)
                digest_btn = gr.Button("Сводка", variant="secondary", scale=1)

            profile.change(on_profile_change, inputs=profile, outputs=status)
            model.change(on_model_change, inputs=model, outputs=status)
            create_btn.click(
                create_profile,
                inputs=[new_profile, profile],
                outputs=[profile, new_profile, status],
            )
            send_btn.click(
                respond,
                inputs=[user_input, chatbot, profile, model],
                outputs=[chatbot, graph_html, user_input],
            )
            user_input.submit(
                respond,
                inputs=[user_input, chatbot, profile, model],
                outputs=[chatbot, graph_html, user_input],
            )
            digest_btn.click(
                run_digest,
                inputs=[profile, model, chatbot],
                outputs=[chatbot, graph_html],
            )

    return demo


def main() -> None:
    """Launch the Gradio news agent interface."""

    settings.ensure_data_dir()
    demo = build_ui()
    theme = gr.themes.Ocean(
        primary_hue="blue",
        secondary_hue="slate",
        neutral_hue="slate",
        font=[gr.themes.GoogleFont("Manrope"), "Segoe UI", "sans-serif"],
    ).set(
        body_background_fill="#020617",
        body_background_fill_dark="#020617",
        background_fill_primary="#0B1220",
        background_fill_primary_dark="#0B1220",
        background_fill_secondary="#111827",
        background_fill_secondary_dark="#111827",
        block_background_fill="transparent",
        block_background_fill_dark="transparent",
        block_border_width="0px",
        block_border_width_dark="0px",
        block_shadow="none",
        block_shadow_dark="none",
        body_text_color="#E2E8F0",
        body_text_color_dark="#E2E8F0",
        input_background_fill="#0F172A",
        input_background_fill_dark="#0F172A",
        input_border_color="#2A3348",
        input_border_color_dark="#2A3348",
        button_primary_background_fill="#2563EB",
        button_primary_background_fill_dark="#2563EB",
        button_secondary_background_fill="#111827",
        button_secondary_background_fill_dark="#111827",
        border_color_primary="#2A3348",
        border_color_primary_dark="#2A3348",
        link_text_color="#93C5FD",
        link_text_color_dark="#93C5FD",
    )
    demo.queue().launch(
        server_name=settings.gradio_server_name,
        server_port=settings.gradio_server_port,
        css=CUSTOM_CSS,
        theme=theme,
    )


if __name__ == "__main__":
    main()
