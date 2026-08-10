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
  margin: 0 !important;
  min-height: 100vh !important;
}

.gradio-container {
  font-family: Manrope, 'Segoe UI', sans-serif !important;
  max-width: 1860px !important;
  width: 100% !important;
  margin: 0 auto !important;
  padding: 16px 24px 20px !important;
  background: #020617 !important;
  color: #E2E8F0 !important;
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
  display: none !important;
}

#na-app {
  background: linear-gradient(165deg, #020617 0%, #0B1220 50%, #111827 100%);
  border-radius: 20px;
  padding: 18px 20px 14px;
  border: 1px solid #252E3F;
  gap: 12px !important;
  min-height: calc(1080px - 48px);
}

#na-title h1 {
  color: #F8FAFC !important;
  margin: 0 0 8px 0 !important;
  font-size: 28px !important;
}

#na-toolbar {
  gap: 10px !important;
  flex-wrap: nowrap !important;
  align-items: center !important;
}

#na-toolbar > * {
  flex: 0 1 auto !important;
}

#na-toolbar .block {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin: 0 !important;
}

#na-profile {
  max-width: 180px !important;
  min-width: 140px !important;
  flex: 0 0 180px !important;
}

#na-model {
  max-width: 280px !important;
  min-width: 220px !important;
  flex: 0 0 280px !important;
}

#na-new-profile {
  max-width: 220px !important;
  min-width: 180px !important;
  flex: 0 0 220px !important;
}

#na-create-btn {
  max-width: 120px !important;
  min-width: 110px !important;
  flex: 0 0 120px !important;
}

#na-toolbar .wrap-inner,
#na-toolbar textarea,
#na-toolbar input {
  background: #0F172A !important;
  border: 1px solid #2A3348 !important;
  border-radius: 12px !important;
  color: #F8FAFC !important;
  box-shadow: none !important;
  min-height: 40px !important;
  height: 40px !important;
  padding: 0 12px !important;
}

#na-toolbar button {
  border-radius: 12px !important;
  min-height: 40px !important;
  height: 40px !important;
}

#na-main {
  gap: 14px !important;
  align-items: stretch !important;
  flex: 1 1 auto !important;
}

#na-chatbot, #na-graph {
  border-radius: 16px !important;
  border: 1px solid #2A3348 !important;
  background: #0B1220 !important;
  overflow: hidden !important;
  height: 760px !important;
  min-height: 760px !important;
}

#na-chatbot .bubble-wrap,
#na-chatbot .message-wrap,
#na-chatbot > div {
  background: #0B1220 !important;
  height: 100% !important;
}

#na-chatbot .bot, #na-chatbot [data-testid="bot"] {
  background: #111827 !important;
  border: 1px solid #2A3348 !important;
  border-radius: 14px !important;
  color: #E2E8F0 !important;
}

#na-chatbot .user, #na-chatbot [data-testid="user"] {
  background: #172033 !important;
  border: 1px solid #2A3348 !important;
  border-radius: 14px !important;
  color: #E2E8F0 !important;
}

#na-composer {
  gap: 10px !important;
  align-items: stretch !important;
}

#na-composer .block {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin: 0 !important;
}

#na-composer textarea {
  background: #0F172A !important;
  border: 1px solid #2A3348 !important;
  border-radius: 14px !important;
  color: #F8FAFC !important;
  min-height: 56px !important;
}

#na-composer button {
  border-radius: 12px !important;
  min-height: 56px !important;
  max-width: 160px !important;
}

.prose, .prose *, .markdown-body, .markdown-body * {
  color: #E2E8F0 !important;
}

.prose th, .prose td, .markdown-body th, .markdown-body td {
  border-color: #2A3348 !important;
  color: #E2E8F0 !important;
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


def on_profile_change(profile_name: str) -> None:
    agent.set_profile(profile_name)


def on_model_change(model_name: str) -> None:
    agent.set_model(model_name)


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
    return gr.update(choices=choices, value=name), ""


def build_ui() -> gr.Blocks:
    default_model = (
        settings.zvenoai_model
        if settings.zvenoai_model in CHEAP_MODELS
        else CHEAP_MODELS[0]
    )
    with gr.Blocks(fill_height=True) as demo:
        with gr.Column(elem_id="na-app"):
            gr.Markdown("# Агент цитирований", elem_id="na-title")

            with gr.Row(elem_id="na-toolbar", equal_height=True):
                profile = gr.Dropdown(
                    choices=_profile_choices(),
                    value="default",
                    show_label=False,
                    container=False,
                    interactive=True,
                    elem_id="na-profile",
                    scale=0,
                    min_width=140,
                )
                model = gr.Dropdown(
                    choices=CHEAP_MODELS,
                    value=default_model,
                    show_label=False,
                    container=False,
                    interactive=True,
                    elem_id="na-model",
                    scale=0,
                    min_width=220,
                )
                new_profile = gr.Textbox(
                    show_label=False,
                    container=False,
                    placeholder="Создать профиль",
                    elem_id="na-new-profile",
                    scale=0,
                    min_width=180,
                )
                create_btn = gr.Button(
                    "Создать",
                    variant="secondary",
                    elem_id="na-create-btn",
                    scale=0,
                    min_width=110,
                )

            with gr.Row(elem_id="na-main", equal_height=True):
                chatbot = gr.Chatbot(
                    elem_id="na-chatbot",
                    show_label=False,
                    height=760,
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
                    placeholder=(
                        "доверенные СМИ про пилатес, ссылка на новость, "
                        "тема для графа или синтез новости"
                    ),
                    scale=6,
                    lines=2,
                    show_label=False,
                    container=False,
                )
                send_btn = gr.Button("Отправить", variant="primary", scale=1)
                digest_btn = gr.Button("Сводка", variant="secondary", scale=1)

            profile.change(on_profile_change, inputs=profile, outputs=None)
            model.change(on_model_change, inputs=model, outputs=None)
            create_btn.click(
                create_profile,
                inputs=[new_profile, profile],
                outputs=[profile, new_profile],
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
    """Launch the Gradio citation agent interface."""

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
