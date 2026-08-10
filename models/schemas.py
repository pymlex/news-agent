from datetime import datetime
from enum import Enum
from typing import Any


from pydantic import BaseModel, Field


class TrustLevel(str, Enum):
    """Discrete trust bands used for ranking and graph colouring."""

    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class NodeKind(str, Enum):
    """Kinds of vertices in the provenance graph."""

    OUTLET = "outlet"
    ARTICLE = "article"
    EVENT = "event"
    EXPERT = "expert"
    CLAIM = "claim"


class EdgeKind(str, Enum):
    """Kinds of directed citation or reinterpretation edges."""

    CITES = "cites"
    REPOSTS = "reposts"
    REINTERPRETS = "reinterprets"
    ATTRIBUTES = "attributes"
    MENTIONS = "mentions"


class SearchHit(BaseModel):
    """One web search result."""

    title: str
    url: str
    snippet: str = ""
    source: str = ""


class TrustedOutlet(BaseModel):
    """Trusted media outlet stored under a user profile."""

    name: str
    domain: str = ""
    url: str = ""
    weight: float = Field(ge=0.0, le=1.0, default=0.5)
    reason: str = ""
    topics: list[str] = Field(default_factory=list)
    trust_level: TrustLevel = TrustLevel.MEDIUM


class Profile(BaseModel):
    """User preference profile for trusted media and digests."""

    name: str
    preferences: str = ""
    region: str = ""
    topics: list[str] = Field(default_factory=list)


class GraphNode(BaseModel):
    """Vertex of the provenance graph."""

    id: str
    label: str
    kind: NodeKind
    url: str = ""
    trust_score: float = Field(ge=0.0, le=1.0, default=0.5)
    trust_level: TrustLevel = TrustLevel.MEDIUM
    meta: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """Directed relation between two graph nodes."""

    source: str
    target: str
    kind: EdgeKind
    weight: float = Field(ge=0.0, le=1.0, default=0.5)
    evidence: str = ""


class ProvenanceGraph(BaseModel):
    """Full provenance graph for one investigation."""

    title: str
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class StanceNote(BaseModel):
    """Explicit stance or assessment attributed to a source or expert."""

    actor: str
    position: str
    assessment: str = ""
    source_url: str = ""
    trust_score: float = Field(ge=0.0, le=1.0, default=0.5)


class SynthesizedNews(BaseModel):
    """Generated news text with visible sources and stance notes."""

    headline: str
    body_markdown: str
    sources: list[SearchHit] = Field(default_factory=list)
    stances: list[StanceNote] = Field(default_factory=list)
    graph: ProvenanceGraph | None = None


class DigestItem(BaseModel):
    """One item in a preference-based morning digest."""

    title: str
    summary: str
    url: str = ""
    outlet: str = ""
    trust_score: float = Field(ge=0.0, le=1.0, default=0.5)


class MorningDigest(BaseModel):
    """Morning digest tailored to a profile."""

    profile_name: str
    focus: str
    intro: str
    items: list[DigestItem] = Field(default_factory=list)
    markdown: str = ""


class AgentReply(BaseModel):
    """Structured agent response for the Gradio UI."""

    markdown: str
    graph_html: str = ""
    graph: ProvenanceGraph | None = None
