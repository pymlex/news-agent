import html


import gradio as gr


from agent.orchestrator import agent
from utils.config import Settings, settings
from utils.db import db
from utils.zveno import CHEAP_MODELS


CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@500;600;700&display=swap');

html, body, .gradio-container {
  background: #0B1220 !important;
  color: #E2E8F0 !important;
  font-family: Manrope, 'Segoe UI', sans-serif !important;
  font-size: 16px !important;
}

.gradio-container {
  max-width: 1860px !important;
  margin: 0 auto !important;
  padding: 16px 24px !important;
}

footer {
  display: none !important;
}

#na-app {
  gap: 14px !important;
}

#na-header-html {
  width: 100% !important;
}

#na-header-html .block,
#na-header-html .form {
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin: 0 !important;
}

.na-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  width: 100%;
  min-height: 52px;
}

.na-bar h1 {
  margin: 0;
  font-size: 30px;
  line-height: 1.2;
  color: #F8FAFC;
  font-weight: 700;
  white-space: nowrap;
}

.na-bar-controls {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.na-bar select,
.na-bar input[type="text"] {
  height: 42px;
  border: 1px solid #334155;
  background: #111827;
  color: #F8FAFC;
  border-radius: 10px;
  padding: 0 12px;
  font-size: 15px;
  font-family: inherit;
  outline: none;
  box-sizing: border-box;
}

.na-bar select#na-sel-profile {
  width: 170px;
}

.na-bar select#na-sel-model {
  width: 270px;
}

.na-bar input#na-inp-profile {
  width: 210px;
}

.na-bar button#na-btn-create {
  height: 42px;
  min-width: 120px;
  border: 1px solid #334155;
  background: #1E293B;
  color: #E2E8F0;
  border-radius: 10px;
  font-size: 15px;
  font-family: inherit;
  cursor: pointer;
  padding: 0 14px;
}

.na-bar button#na-btn-create:hover {
  background: #334155;
}

#na-hidden {
  display: none !important;
  height: 0 !important;
  overflow: hidden !important;
}

#na-main {
  gap: 14px !important;
}

#na-chatbot,
#na-graph {
  border: 1px solid #334155 !important;
  border-radius: 14px !important;
  background: #111827 !important;
  min-height: 760px !important;
}

#na-composer {
  gap: 10px !important;
  align-items: stretch !important;
}

#na-composer .block,
#na-composer .form {
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
  padding: 0 !important;
}

#na-composer textarea {
  border: 1px solid #334155 !important;
  background: #111827 !important;
  border-radius: 12px !important;
  color: #F8FAFC !important;
  font-size: 15px !important;
  min-height: 56px !important;
}

#na-composer button {
  min-height: 56px !important;
  border-radius: 12px !important;
  font-size: 15px !important;
}

.prose, .markdown-body, .prose *, .markdown-body * {
  color: #E2E8F0 !important;
  font-size: 15px !important;
}
"""


HEADER_JS = """
() => {
  const findTextarea = (elemId) => {
    const root = document.getElementById(elemId);
    if (!root) return null;
    return root.querySelector('textarea') || root.querySelector('input');
  };

  const sync = (selectId, boxId) => {
    const sel = document.getElementById(selectId);
    const box = findTextarea(boxId);
    if (!sel || !box) return;
    if (box.value !== sel.value) {
      box.value = sel.value;
      box.dispatchEvent(new Event('input', { bubbles: true }));
    }
  };

  const wire = () => {
    const profileSel = document.getElementById('na-sel-profile');
    const modelSel = document.getElementById('na-sel-model');
    const createInp = document.getElementById('na-inp-profile');
    const createBtn = document.getElementById('na-btn-create');
    if (!profileSel || !modelSel || !createInp || !createBtn) return;

    if (!profileSel.dataset.wired) {
      profileSel.dataset.wired = '1';
      profileSel.addEventListener('change', () => sync('na-sel-profile', 'na-profile-box'));
    }
    if (!modelSel.dataset.wired) {
      modelSel.dataset.wired = '1';
      modelSel.addEventListener('change', () => sync('na-sel-model', 'na-model-box'));
    }
    if (!createInp.dataset.wired) {
      createInp.dataset.wired = '1';
      createInp.addEventListener('input', () => {
        const box = findTextarea('na-new-profile-box');
        if (!box) return;
        box.value = createInp.value;
        box.dispatchEvent(new Event('input', { bubbles: true }));
      });
    }
    if (!createBtn.dataset.wired) {
      createBtn.dataset.wired = '1';
      createBtn.addEventListener('click', () => {
        const box = findTextarea('na-new-profile-box');
        if (box) {
          box.value = createInp.value;
          box.dispatchEvent(new Event('input', { bubbles: true }));
        }
        const hiddenBtn = document.querySelector('#na-hidden-create button');
        if (hiddenBtn) hiddenBtn.click();
      });
    }

    sync('na-sel-profile', 'na-profile-box');
    sync('na-sel-model', 'na-model-box');
  };

  wire();
  setInterval(wire, 800);
}
"""


def _profile_choices() -> list[str]:
    names = [p.name for p in db.list_profiles()]
    if "default" not in names:
        names = ["default", *names]
    return names


def render_header(profile_name: str, model_name: str) -> str:
    """Render a flat HTML toolbar with native selects."""

    profiles = _profile_choices()
    profile_options = []
    for name in profiles:
        selected = " selected" if name == profile_name else ""
        profile_options.append(
            f'<option value="{html.escape(name)}"{selected}>{html.escape(name)}</option>'
        )
    model_options = []
    for name in CHEAP_MODELS:
        selected = " selected" if name == model_name else ""
        model_options.append(
            f'<option value="{html.escape(name)}"{selected}>{html.escape(name)}</option>'
        )
    return f"""
<div class="na-bar">
  <h1>Агент цитирований</h1>
  <div class="na-bar-controls">
    <select id="na-sel-profile">{''.join(profile_options)}</select>
    <select id="na-sel-model">{''.join(model_options)}</select>
    <input id="na-inp-profile" type="text" placeholder="Создать профиль" />
    <button id="na-btn-create" type="button">Создать</button>
  </div>
</div>
"""


def on_profile_change(profile_name: str) -> None:
    agent.set_profile(profile_name or "default")


def on_model_change(model_name: str) -> None:
    agent.set_model(model_name or CHEAP_MODELS[0])


def respond(
    message: str,
    history: list[dict],
    profile_name: str,
    model_name: str,
):
    agent.set_profile(profile_name or "default")
    agent.set_model(model_name or CHEAP_MODELS[0])
    reply = agent.handle(message)
    history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": reply.markdown},
    ]
    return history, reply.graph_html, ""


def run_digest(profile_name: str, model_name: str, history: list[dict]):
    agent.set_profile(profile_name or "default")
    agent.set_model(model_name or CHEAP_MODELS[0])
    reply = agent.handle("утренняя сводка по моим предпочтениям")
    history = history + [
        {"role": "user", "content": "утренняя сводка"},
        {"role": "assistant", "content": reply.markdown},
    ]
    return history, reply.graph_html


def create_profile(new_name: str, current: str, model_name: str):
    name = (new_name or "").strip() or current or "default"
    agent.set_profile(name)
    return (
        name,
        "",
        render_header(name, model_name or CHEAP_MODELS[0]),
    )


def build_ui() -> gr.Blocks:
    default_model = (
        settings.zvenoai_model
        if settings.zvenoai_model in CHEAP_MODELS
        else CHEAP_MODELS[0]
    )
    with gr.Blocks(fill_height=True) as demo:
        with gr.Column(elem_id="na-app"):
            header = gr.HTML(
                value=render_header("default", default_model),
                elem_id="na-header-html",
            )

            with gr.Row(elem_id="na-hidden"):
                profile = gr.Textbox(
                    value="default",
                    elem_id="na-profile-box",
                )
                model = gr.Textbox(
                    value=default_model,
                    elem_id="na-model-box",
                )
                new_profile = gr.Textbox(
                    value="",
                    elem_id="na-new-profile-box",
                )
                hidden_create = gr.Button("hidden-create", elem_id="na-hidden-create")

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
                    show_label=False,
                    container=False,
                    lines=2,
                    scale=6,
                )
                send_btn = gr.Button("Отправить", variant="primary", scale=1)
                digest_btn = gr.Button("Сводка", variant="secondary", scale=1)

            profile.change(on_profile_change, inputs=profile, outputs=None)
            model.change(on_model_change, inputs=model, outputs=None)
            hidden_create.click(
                create_profile,
                inputs=[new_profile, profile, model],
                outputs=[profile, new_profile, header],
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
    if not Settings().zvenoai_api_key.strip():
        print("WARNING: ZVENOAI_API_KEY is empty in .env")
    demo = build_ui()
    theme = gr.themes.Default(
        primary_hue="blue",
        secondary_hue="slate",
        neutral_hue="slate",
        font=[gr.themes.GoogleFont("Manrope"), "Segoe UI", "sans-serif"],
        text_size="lg",
    ).set(
        body_background_fill="#0B1220",
        body_background_fill_dark="#0B1220",
        background_fill_primary="#111827",
        background_fill_primary_dark="#111827",
        block_background_fill="#111827",
        block_background_fill_dark="#111827",
        block_border_width="0px",
        block_border_width_dark="0px",
        block_shadow="none",
        block_shadow_dark="none",
        body_text_color="#E2E8F0",
        body_text_color_dark="#E2E8F0",
        border_color_primary="#334155",
        border_color_primary_dark="#334155",
        input_background_fill="#111827",
        input_background_fill_dark="#111827",
        input_border_color="#334155",
        input_border_color_dark="#334155",
        button_primary_background_fill="#2563EB",
        button_primary_background_fill_dark="#2563EB",
        button_secondary_background_fill="#1E293B",
        button_secondary_background_fill_dark="#1E293B",
    )
    demo.queue().launch(
        server_name=settings.gradio_server_name,
        server_port=settings.gradio_server_port,
        css=CUSTOM_CSS,
        theme=theme,
        js=HEADER_JS,
    )


if __name__ == "__main__":
    main()
