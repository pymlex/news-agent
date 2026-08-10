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
  font-size: 16px !important;
  max-width: 1860px !important;
  width: 100% !important;
  margin: 0 auto !important;
  padding: 12px 20px 16px !important;
  background: #020617 !important;
  color: #E2E8F0 !important;
  --body-background-fill: #020617 !important;
  --background-fill-primary: #0B1220 !important;
  --background-fill-secondary: #111827 !important;
  --block-background-fill: transparent !important;
  --block-border-color: transparent !important;
  --block-border-width: 0px !important;
  --block-shadow: none !important;
  --border-color-primary: #2A3348 !important;
  --body-text-color: #E2E8F0 !important;
  --input-background-fill: #0F172A !important;
  --input-border-color: #2A3348 !important;
  --input-placeholder-color: #64748B !important;
  --link-text-color: #93C5FD !important;
}

footer {
  display: none !important;
}

#na-app {
  background: linear-gradient(165deg, #020617 0%, #0B1220 50%, #111827 100%);
  border-radius: 20px;
  padding: 14px 18px 12px;
  border: 1px solid #252E3F;
  gap: 12px !important;
  min-height: calc(100vh - 28px);
}

#na-header {
  display: flex !important;
  flex-direction: row !important;
  flex-wrap: nowrap !important;
  align-items: center !important;
  justify-content: space-between !important;
  gap: 12px !important;
  width: 100% !important;
  min-height: 52px !important;
  margin: 0 !important;
  padding: 0 !important;
}

#na-header > div {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin: 0 !important;
}

#na-title {
  flex: 1 1 auto !important;
  min-width: 220px !important;
}

#na-title h1, #na-title .prose h1, #na-title md h1 {
  color: #F8FAFC !important;
  margin: 0 !important;
  padding: 0 !important;
  font-size: 30px !important;
  line-height: 1.15 !important;
  font-weight: 700 !important;
}

#na-controls {
  display: flex !important;
  flex-direction: row !important;
  flex-wrap: nowrap !important;
  align-items: center !important;
  justify-content: flex-end !important;
  gap: 10px !important;
  flex: 0 0 auto !important;
  margin-left: auto !important;
}

#na-controls > * {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin: 0 !important;
}

#na-profile,
#na-model,
#na-new-profile,
#na-create-btn {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin: 0 !important;
}

#na-profile {
  width: 160px !important;
  min-width: 160px !important;
  max-width: 160px !important;
}

#na-model {
  width: 250px !important;
  min-width: 250px !important;
  max-width: 250px !important;
}

#na-new-profile {
  width: 200px !important;
  min-width: 200px !important;
  max-width: 200px !important;
}

#na-create-btn {
  width: 112px !important;
  min-width: 112px !important;
  max-width: 112px !important;
}

#na-controls .wrap,
#na-controls .wrap-inner,
#na-controls input,
#na-controls textarea,
#na-controls .container,
#na-controls .secondary-wrap {
  background: #0F172A !important;
  border: 1px solid #2A3348 !important;
  border-radius: 12px !important;
  color: #F8FAFC !important;
  box-shadow: none !important;
  outline: none !important;
  min-height: 44px !important;
  height: 44px !important;
  font-size: 15px !important;
  line-height: 44px !important;
  padding: 0 12px !important;
  margin: 0 !important;
  box-sizing: border-box !important;
}

#na-controls .wrap {
  border: none !important;
  background: transparent !important;
  padding: 0 !important;
  height: auto !important;
  min-height: 0 !important;
}

#na-controls .wrap-inner {
  display: flex !important;
  align-items: center !important;
}

#na-controls textarea,
#na-controls input[type="text"] {
  display: flex !important;
  align-items: center !important;
  resize: none !important;
  padding-top: 0 !important;
  padding-bottom: 0 !important;
}

#na-controls button,
#na-create-btn button,
#na-create-btn {
  height: 44px !important;
  min-height: 44px !important;
  border-radius: 12px !important;
  font-size: 15px !important;
  margin: 0 !important;
}

#na-main {
  gap: 14px !important;
  align-items: stretch !important;
}

#na-chatbot, #na-graph {
  border-radius: 16px !important;
  border: 1px solid #2A3348 !important;
  background: #0B1220 !important;
  overflow: hidden !important;
  height: 780px !important;
  min-height: 780px !important;
}

#na-chatbot,
#na-chatbot > .block,
#na-chatbot .block {
  border: 1px solid #2A3348 !important;
  background: #0B1220 !important;
  box-shadow: none !important;
}

#na-chatbot .bubble-wrap,
#na-chatbot .message-wrap,
#na-chatbot > div {
  background: #0B1220 !important;
}

#na-chatbot .bot, #na-chatbot [data-testid="bot"] {
  background: #111827 !important;
  border: 1px solid #2A3348 !important;
  border-radius: 14px !important;
  color: #E2E8F0 !important;
  font-size: 15px !important;
}

#na-chatbot .user, #na-chatbot [data-testid="user"] {
  background: #172033 !important;
  border: 1px solid #2A3348 !important;
  border-radius: 14px !important;
  color: #E2E8F0 !important;
  font-size: 15px !important;
}

#na-composer {
  gap: 10px !important;
  align-items: stretch !important;
}

#na-composer .block,
#na-composer > div {
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
  font-size: 15px !important;
}

#na-composer button {
  border-radius: 12px !important;
  min-height: 56px !important;
  max-width: 160px !important;
  font-size: 15px !important;
}

.prose, .prose *, .markdown-body, .markdown-body * {
  color: #E2E8F0 !important;
  font-size: 15px !important;
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
  font-size: 15px !important;
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
            with gr.Row(elem_id="na-header"):
                gr.Markdown("# Агент цитирований", elem_id="na-title")
                with gr.Row(elem_id="na-controls"):
                    profile = gr.Dropdown(
                        choices=_profile_choices(),
                        value="default",
                        show_label=False,
                        container=False,
                        interactive=True,
                        elem_id="na-profile",
                        filterable=False,
                    )
                    model = gr.Dropdown(
                        choices=CHEAP_MODELS,
                        value=default_model,
                        show_label=False,
                        container=False,
                        interactive=True,
                        elem_id="na-model",
                        filterable=False,
                    )
                    new_profile = gr.Textbox(
                        show_label=False,
                        container=False,
                        placeholder="Создать профиль",
                        lines=1,
                        max_lines=1,
                        elem_id="na-new-profile",
                    )
                    create_btn = gr.Button(
                        "Создать",
                        variant="secondary",
                        elem_id="na-create-btn",
                    )

            with gr.Row(elem_id="na-main", equal_height=True):
                chatbot = gr.Chatbot(
                    elem_id="na-chatbot",
                    show_label=False,
                    container=False,
                    height=780,
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
        text_size=gr.themes.sizes.text_lg,
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
        input_border_width="1px",
        input_border_width_dark="1px",
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
