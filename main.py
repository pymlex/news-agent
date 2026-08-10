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

html, body {
  background: #020617 !important;
}

.gradio-container {
  font-family: Manrope, 'Segoe UI', sans-serif !important;
  max-width: 1400px !important;
  background: #020617 !important;
  color: #E2E8F0 !important;
}

.gradio-container, .gradio-container * {
  --body-background-fill: #020617 !important;
  --background-fill-primary: #0B1220 !important;
  --background-fill-secondary: #111827 !important;
  --block-background-fill: #0B1220 !important;
  --block-border-color: #1E3A8A !important;
  --border-color-primary: #1E3A8A !important;
  --color-accent: #3B82F6 !important;
  --link-text-color: #93C5FD !important;
  --body-text-color: #E2E8F0 !important;
  --body-text-color-subdued: #94A3B8 !important;
  --input-background-fill: #0F172A !important;
  --input-border-color: #1E3A8A !important;
  --input-placeholder-color: #64748B !important;
  --checkbox-background-color: #0F172A !important;
  --neutral-800: #1E293B !important;
  --neutral-900: #0F172A !important;
  --neutral-950: #020617 !important;
}

footer, .svelte-1sk0pyu {
  color: #64748B !important;
}

#na-app {
  background: linear-gradient(165deg, #020617 0%, #0B1220 42%, #111827 100%);
  border-radius: 28px;
  padding: 18px;
  border: 1px solid #1E293B;
}

#na-title, #na-title h1, #na-title p, #na-title * {
  color: #F8FAFC !important;
  font-weight: 700;
  letter-spacing: -0.02em;
}

#na-title p {
  font-weight: 500 !important;
  color: #94A3B8 !important;
}

.prose, .prose *, .markdown-body, .markdown-body * {
  color: #E2E8F0 !important;
}

.prose table, .markdown-body table {
  border-color: #1E3A8A !important;
}

.prose th, .prose td, .markdown-body th, .markdown-body td {
  border-color: #1E3A8A !important;
  color: #E2E8F0 !important;
}

label, .label-wrap, .label-wrap span {
  color: #CBD5E1 !important;
}

#na-chatbot, #na-graph {
  border-radius: 22px !important;
  border: 1px solid #1E3A8A !important;
  box-shadow: 0 16px 36px rgba(2, 6, 23, 0.55);
  background: #0B1220 !important;
}

#na-chatbot, #na-chatbot > *, #na-chatbot .bubble-wrap, #na-chatbot .message-wrap {
  background: #0B1220 !important;
  color: #E2E8F0 !important;
}

#na-chatbot .message, #na-chatbot .bot, #na-chatbot .user {
  border-radius: 18px !important;
  color: #E2E8F0 !important;
}

#na-chatbot .bot, #na-chatbot [data-testid="bot"] {
  background: #111827 !important;
  border: 1px solid #1E3A8A !important;
}

#na-chatbot .user, #na-chatbot [data-testid="user"] {
  background: #1E3A8A !important;
  border: 1px solid #2563EB !important;
}

#na-input textarea, textarea, input, .wrap-inner, .secondary-wrap {
  border-radius: 18px !important;
  border: 1px solid #1E3A8A !important;
  background: #0F172A !important;
  color: #F8FAFC !important;
}

.gr-dropdown, .container, .wrap {
  color: #E2E8F0 !important;
}

ul.options, .options, [role="listbox"] {
  background: #0F172A !important;
  border: 1px solid #1E3A8A !important;
  color: #E2E8F0 !important;
}

ul.options li, [role="option"] {
  color: #E2E8F0 !important;
}

button {
  border-radius: 16px !important;
}

button.primary, .primary {
  background: linear-gradient(135deg, #2563EB, #1D4ED8) !important;
  border: 1px solid #3B82F6 !important;
  color: #F8FAFC !important;
}

button.secondary, .secondary {
  background: #111827 !important;
  border: 1px solid #1E3A8A !important;
  color: #E2E8F0 !important;
}

.na-chip {
  display: inline-block;
  background: #1D4ED8;
  color: #F8FAFC;
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 12px;
  margin-right: 6px;
  border: 1px solid #3B82F6;
}
"""



def _profile_choices() -> list[str]:
    names = [p.name for p in db.list_profiles()]
    if "default" not in names:
        names = ["default", *names]
    return names


def on_profile_change(profile_name: str) -> str:
    agent.set_profile(profile_name)
    return f"Активный профиль: **{profile_name}**"


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
    return gr.update(choices=choices, value=name), f"Профиль `{name}` готов."


def build_ui() -> gr.Blocks:
    with gr.Blocks() as demo:
        with gr.Column(elem_id="na-app"):
            gr.Markdown(
                """
# News Agent
<span class="na-chip">Zveno AI</span>
<span class="na-chip">DuckDuckGo</span>
<span class="na-chip">Provenance Graph</span>

Чат в духе Telegram-бота: доверенные СМИ по предпочтениям, граф цитирований,
новость с видимыми источниками и утренняя сводка по запросу.
                """,
                elem_id="na-title",
            )

            with gr.Row():
                profile = gr.Dropdown(
                    choices=_profile_choices(),
                    value="default",
                    label="Профиль",
                    interactive=True,
                )
                new_profile = gr.Textbox(
                    label="Новый профиль",
                    placeholder="например: pilates или силовые",
                )
                create_btn = gr.Button("Создать / выбрать", variant="secondary")
                model = gr.Dropdown(
                    choices=CHEAP_MODELS,
                    value=settings.zvenoai_model
                    if settings.zvenoai_model in CHEAP_MODELS
                    else CHEAP_MODELS[0],
                    label="Модель Zveno",
                )

            status = gr.Markdown("Активный профиль: **default**")

            with gr.Row():
                chatbot = gr.Chatbot(
                    elem_id="na-chatbot",
                    label="Диалог",
                    height=560,
                    render_markdown=True,
                    layout="bubble",
                )
                graph_html = gr.HTML(
                    value=agent.last_graph_html,
                    elem_id="na-graph",
                )

            with gr.Row():
                user_input = gr.Textbox(
                    elem_id="na-input",
                    placeholder=(
                        "Пример: доверенные СМИ про пилатес и физиотерапевтов, "
                        "или ссылка на новость, или тема для графа"
                    ),
                    scale=5,
                    lines=2,
                )
                send_btn = gr.Button("Отправить", variant="primary", scale=1)
                digest_btn = gr.Button("Утренняя сводка", scale=1)

            profile.change(on_profile_change, inputs=profile, outputs=status)
            model.change(on_model_change, inputs=model, outputs=status)
            create_btn.click(
                create_profile,
                inputs=[new_profile, profile],
                outputs=[profile, status],
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
        block_background_fill="#0B1220",
        block_background_fill_dark="#0B1220",
        block_border_color="#1E3A8A",
        block_border_color_dark="#1E3A8A",
        body_text_color="#E2E8F0",
        body_text_color_dark="#E2E8F0",
        body_text_color_subdued="#94A3B8",
        body_text_color_subdued_dark="#94A3B8",
        input_background_fill="#0F172A",
        input_background_fill_dark="#0F172A",
        input_border_color="#1E3A8A",
        input_border_color_dark="#1E3A8A",
        button_primary_background_fill="#2563EB",
        button_primary_background_fill_dark="#2563EB",
        button_primary_text_color="#F8FAFC",
        button_primary_text_color_dark="#F8FAFC",
        button_secondary_background_fill="#111827",
        button_secondary_background_fill_dark="#111827",
        button_secondary_text_color="#E2E8F0",
        button_secondary_text_color_dark="#E2E8F0",
        border_color_primary="#1E3A8A",
        border_color_primary_dark="#1E3A8A",
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
