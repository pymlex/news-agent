import html
import json
import uuid


from models.schemas import ProvenanceGraph, TrustLevel


TRUST_COLORS = {
    TrustLevel.VERY_HIGH: {
        "background": "#3B82F6",
        "border": "#93C5FD",
        "highlight": "#60A5FA",
        "font": "#F8FAFC",
    },
    TrustLevel.HIGH: {
        "background": "#2563EB",
        "border": "#60A5FA",
        "highlight": "#3B82F6",
        "font": "#F8FAFC",
    },
    TrustLevel.MEDIUM: {
        "background": "#1E3A8A",
        "border": "#3B82F6",
        "highlight": "#2563EB",
        "font": "#E2E8F0",
    },
    TrustLevel.LOW: {
        "background": "#9A3412",
        "border": "#FB923C",
        "highlight": "#C2410C",
        "font": "#FFEDD5",
    },
    TrustLevel.VERY_LOW: {
        "background": "#9F1239",
        "border": "#FB7185",
        "highlight": "#BE123C",
        "font": "#FFE4E6",
    },
}


KIND_SHAPES = {
    "outlet": "box",
    "article": "ellipse",
    "event": "diamond",
    "expert": "dot",
    "claim": "triangle",
}


def score_to_level(score: float) -> TrustLevel:
    """Map a continuous trust score to a discrete colour band."""

    if score >= 0.85:
        return TrustLevel.VERY_HIGH
    if score >= 0.7:
        return TrustLevel.HIGH
    if score >= 0.45:
        return TrustLevel.MEDIUM
    if score >= 0.25:
        return TrustLevel.LOW
    return TrustLevel.VERY_LOW


def render_graph_html(graph: ProvenanceGraph, height: int = 700) -> str:
    """Build a self-contained interactive HTML widget for a provenance graph.

    Args:
        graph: Provenance graph with nodes and citation edges.
        height: Pixel height of the canvas.

    Returns:
        HTML string embedding vis-network with a dark blue theme.
    """

    nodes_payload = []
    for node in graph.nodes:
        level = node.trust_level or score_to_level(node.trust_score)
        colors = TRUST_COLORS[level]
        shape = KIND_SHAPES.get(node.kind.value, "ellipse")
        title_bits = [
            f"<b>{html.escape(node.label)}</b>",
            f"type: {html.escape(node.kind.value)}",
            f"trust: {node.trust_score:.2f} ({html.escape(level.value)})",
        ]
        if node.url:
            title_bits.append(html.escape(node.url))
        nodes_payload.append(
            {
                "id": node.id,
                "label": node.label[:72],
                "shape": shape,
                "title": "<br>".join(title_bits),
                "url": node.url,
                "color": {
                    "background": colors["background"],
                    "border": colors["border"],
                    "highlight": {
                        "background": colors["highlight"],
                        "border": colors["border"],
                    },
                },
                "font": {
                    "color": colors["font"],
                    "face": "Manrope, Segoe UI, sans-serif",
                },
                "borderWidth": 2,
                "margin": 12,
            }
        )

    edges_payload = []
    for edge in graph.edges:
        edges_payload.append(
            {
                "from": edge.source,
                "to": edge.target,
                "arrows": "to",
                "label": edge.kind.value,
                "title": html.escape(edge.evidence or edge.kind.value),
                "color": {"color": "#64748B", "highlight": "#60A5FA"},
                "font": {"color": "#94A3B8", "strokeWidth": 0, "size": 11},
                "smooth": {"type": "cubicBezier"},
                "width": 1.5 + float(edge.weight),
            }
        )

    canvas_id = f"graph_{uuid.uuid4().hex[:10]}"
    nodes_json = json.dumps(nodes_payload, ensure_ascii=False)
    edges_json = json.dumps(edges_payload, ensure_ascii=False)
    title = html.escape(graph.title or "Provenance graph")

    return f"""
<div class="na-graph-shell" style="
  font-family: Manrope, 'Segoe UI', sans-serif;
  background: linear-gradient(165deg, #0B1220 0%, #111827 48%, #0F172A 100%);
  border-radius: 24px;
  padding: 18px;
  border: 1px solid #2A3348;
  box-shadow: 0 18px 40px rgba(2, 6, 23, 0.55);
  color: #E2E8F0;
">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@500;700&display=swap" rel="stylesheet">
  <div style="display:flex; justify-content:space-between; align-items:center; gap:12px; margin-bottom:12px;">
    <div>
      <div style="font-size:13px; letter-spacing:0.08em; text-transform:uppercase; color:#60A5FA; font-weight:700;">Provenance</div>
      <div style="font-size:20px; font-weight:700; color:#F8FAFC;">{title}</div>
    </div>
    <div style="display:flex; gap:8px; flex-wrap:wrap;">
      <span style="background:#3B82F6; color:#F8FAFC; border-radius:999px; padding:6px 12px; font-size:12px;">very trusted</span>
      <span style="background:#2563EB; color:#F8FAFC; border-radius:999px; padding:6px 12px; font-size:12px;">trusted</span>
      <span style="background:#1E3A8A; color:#E2E8F0; border-radius:999px; padding:6px 12px; font-size:12px;">ok</span>
      <span style="background:#9A3412; color:#FFEDD5; border-radius:999px; padding:6px 12px; font-size:12px;">weak</span>
      <span style="background:#9F1239; color:#FFE4E6; border-radius:999px; padding:6px 12px; font-size:12px;">untrusted</span>
    </div>
  </div>
  <div id="{canvas_id}" style="height:{height}px; border-radius:20px; background:rgba(2,6,23,0.72); border:1px solid #2A3348;"></div>
</div>
<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
<script>
(() => {{
  const container = document.getElementById("{canvas_id}");
  const nodes = new vis.DataSet({nodes_json});
  const edges = new vis.DataSet({edges_json});
  const network = new vis.Network(container, {{nodes, edges}}, {{
    interaction: {{ hover: true, tooltipDelay: 80, navigationButtons: true, keyboard: true }},
    physics: {{
      solver: "forceAtlas2Based",
      forceAtlas2Based: {{ gravitationalConstant: -42, springLength: 140, springConstant: 0.06 }},
      stabilization: {{ iterations: 120 }}
    }},
    nodes: {{
      shapeProperties: {{ borderRadius: 16 }},
      shadow: {{ enabled: true, color: "rgba(37,99,235,0.35)", size: 14, x: 0, y: 6 }}
    }},
    edges: {{
      font: {{ size: 11, color: "#94A3B8", strokeWidth: 0, face: "Manrope" }},
      selectionWidth: 2
    }}
  }});
  network.on("doubleClick", (params) => {{
    if (!params.nodes.length) return;
    const node = nodes.get(params.nodes[0]);
    if (node && node.url) window.open(node.url, "_blank");
  }});
}})();
</script>
"""
