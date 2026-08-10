import gradio as gr


from agent.orchestrator import agent
from utils.config import settings
from utils.db import db
from utils.zveno import CHEAP_MODELS


CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@500;600;700&display=swap');

:root {
  --na-blue-950: #0B1F44;
  --na-blue-800: #1E3A8A;
  --na-blue-600: #2563EB;
  --na-blue-100: #DBEAFE;
  --na-blue-50: #EFF6FF;
  --na-radius: 22px;
}

.gradio-container {
  font-family: Manrope, 'Segoe UI', sans-serif !important;
  max-width: 1400px !important;
}

#na-app {
  background: linear-gradient(165deg, #EFF6FF 0%, #F8FAFC 42%, #DBEAFE 100%);
  border-radius: 28px;
  padding: 18px;
}

#na-title {
  color: var(--na-blue-950);
  font-weight: 700;
  letter-spacing: -0.02em;
}

#na-chatbot, #na-graph {
  border-radius: var(--na-radius) !important;
  border: 1px solid #BFDBFE !important;
  box-shadow: 0 16px 36px rgba(37, 99, 235, 0.10);
  background: rgba(255,255,255,0.78) !important;
}

#na-chatbot .message {
  border-radius: 18px !important;
}

#na-input textarea {
  border-radius: 18px !important;
  border: 1px solid #93C5FD !important;
}

button {
  border-radius: 16px !important;
}

.na-chip {
  display: inline-block;
  background: #2563EB;
  color: white;
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 12px;
  margin-right: 6px;
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
    demo.queue().launch(
        server_name=settings.gradio_server_name,
        server_port=settings.gradio_server_port,
        css=CUSTOM_CSS,
    )


if __name__ == "__main__":
    main()
