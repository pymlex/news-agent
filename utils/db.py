import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


from models.schemas import (
    EdgeKind,
    GraphEdge,
    GraphNode,
    NodeKind,
    Profile,
    ProvenanceGraph,
    TrustLevel,
    TrustedOutlet,
)
from utils.config import settings


class NewsDatabase:
    """SQLite persistence for profiles, trusted outlets and provenance graphs."""

    def __init__(self, path: str | None = None) -> None:
        """Open or create the on-disk SQLite database.

        Args:
            path: Optional override for the database file path.
        """

        db_path = Path(path or settings.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.path = db_path
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()


    def _init_schema(self) -> None:
        """Create tables when the database is empty."""

        cur = self.conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                preferences TEXT NOT NULL DEFAULT '',
                region TEXT NOT NULL DEFAULT '',
                topics_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS trusted_media (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                domain TEXT NOT NULL DEFAULT '',
                url TEXT NOT NULL DEFAULT '',
                weight REAL NOT NULL DEFAULT 0.5,
                reason TEXT NOT NULL DEFAULT '',
                topics_json TEXT NOT NULL DEFAULT '[]',
                trust_level TEXT NOT NULL DEFAULT 'medium',
                created_at TEXT NOT NULL,
                FOREIGN KEY(profile_id) REFERENCES profiles(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS graphs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER,
                title TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(profile_id) REFERENCES profiles(id) ON DELETE SET NULL
            );

            CREATE INDEX IF NOT EXISTS idx_trusted_profile
                ON trusted_media(profile_id);
            CREATE INDEX IF NOT EXISTS idx_graphs_profile
                ON graphs(profile_id);
            """
        )
        self.conn.commit()


    def upsert_profile(self, profile: Profile) -> int:
        """Insert or update a preference profile.

        Args:
            profile: Profile payload.

        Returns:
            Database id of the profile.
        """

        now = datetime.utcnow().isoformat()
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO profiles (name, preferences, region, topics_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                preferences = excluded.preferences,
                region = excluded.region,
                topics_json = excluded.topics_json,
                updated_at = excluded.updated_at
            """,
            (
                profile.name,
                profile.preferences,
                profile.region,
                json.dumps(profile.topics, ensure_ascii=False),
                now,
                now,
            ),
        )
        self.conn.commit()
        return self.get_profile_id(profile.name)


    def get_profile_id(self, name: str) -> int:
        """Resolve profile name to database id.

        Args:
            name: Unique profile name.

        Returns:
            Integer profile id.
        """

        cur = self.conn.cursor()
        row = cur.execute(
            "SELECT id FROM profiles WHERE name = ?",
            (name,),
        ).fetchone()
        if row is None:
            return self.upsert_profile(Profile(name=name))
        return int(row["id"])


    def list_profiles(self) -> list[Profile]:
        """Return all stored profiles."""

        cur = self.conn.cursor()
        rows = cur.execute(
            "SELECT name, preferences, region, topics_json FROM profiles ORDER BY name"
        ).fetchall()
        result: list[Profile] = []
        for row in rows:
            result.append(
                Profile(
                    name=row["name"],
                    preferences=row["preferences"],
                    region=row["region"],
                    topics=json.loads(row["topics_json"]),
                )
            )
        return result


    def get_profile(self, name: str) -> Profile | None:
        """Load one profile by name."""

        cur = self.conn.cursor()
        row = cur.execute(
            """
            SELECT name, preferences, region, topics_json
            FROM profiles WHERE name = ?
            """,
            (name,),
        ).fetchone()
        if row is None:
            return None
        return Profile(
            name=row["name"],
            preferences=row["preferences"],
            region=row["region"],
            topics=json.loads(row["topics_json"]),
        )


    def replace_trusted_media(
        self,
        profile_name: str,
        outlets: list[TrustedOutlet],
    ) -> None:
        """Replace the trusted media list for a profile.

        Args:
            profile_name: Target profile.
            outlets: New trusted outlets with weights.
        """

        profile_id = self.get_profile_id(profile_name)
        now = datetime.utcnow().isoformat()
        cur = self.conn.cursor()
        cur.execute("DELETE FROM trusted_media WHERE profile_id = ?", (profile_id,))
        for outlet in outlets:
            cur.execute(
                """
                INSERT INTO trusted_media (
                    profile_id, name, domain, url, weight, reason,
                    topics_json, trust_level, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile_id,
                    outlet.name,
                    outlet.domain,
                    outlet.url,
                    outlet.weight,
                    outlet.reason,
                    json.dumps(outlet.topics, ensure_ascii=False),
                    outlet.trust_level.value,
                    now,
                ),
            )
        self.conn.commit()


    def list_trusted_media(self, profile_name: str) -> list[TrustedOutlet]:
        """List trusted outlets for a profile ordered by weight descending."""

        profile_id = self.get_profile_id(profile_name)
        cur = self.conn.cursor()
        rows = cur.execute(
            """
            SELECT name, domain, url, weight, reason, topics_json, trust_level
            FROM trusted_media
            WHERE profile_id = ?
            ORDER BY weight DESC, name ASC
            """,
            (profile_id,),
        ).fetchall()
        outlets: list[TrustedOutlet] = []
        for row in rows:
            outlets.append(
                TrustedOutlet(
                    name=row["name"],
                    domain=row["domain"],
                    url=row["url"],
                    weight=float(row["weight"]),
                    reason=row["reason"],
                    topics=json.loads(row["topics_json"]),
                    trust_level=TrustLevel(row["trust_level"]),
                )
            )
        return outlets


    def trust_by_domain(self, profile_name: str) -> dict[str, float]:
        """Map domain to trust weight for ranking search hits."""

        mapping: dict[str, float] = {}
        for outlet in self.list_trusted_media(profile_name):
            key = outlet.domain.strip().lower()
            if key:
                mapping[key] = max(mapping.get(key, 0.0), outlet.weight)
            name_key = outlet.name.strip().lower()
            if name_key:
                mapping[name_key] = max(mapping.get(name_key, 0.0), outlet.weight)
        return mapping


    def save_graph(
        self,
        graph: ProvenanceGraph,
        profile_name: str | None = None,
    ) -> int:
        """Persist a provenance graph payload.

        Args:
            graph: Graph to store.
            profile_name: Optional owning profile.

        Returns:
            Inserted graph row id.
        """

        profile_id = self.get_profile_id(profile_name) if profile_name else None
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO graphs (profile_id, title, payload_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                profile_id,
                graph.title,
                graph.model_dump_json(),
                datetime.utcnow().isoformat(),
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)


    def latest_graph(self, profile_name: str | None = None) -> ProvenanceGraph | None:
        """Load the most recent graph, optionally filtered by profile."""

        cur = self.conn.cursor()
        if profile_name:
            profile_id = self.get_profile_id(profile_name)
            row = cur.execute(
                """
                SELECT payload_json FROM graphs
                WHERE profile_id = ?
                ORDER BY id DESC LIMIT 1
                """,
                (profile_id,),
            ).fetchone()
        else:
            row = cur.execute(
                "SELECT payload_json FROM graphs ORDER BY id DESC LIMIT 1"
            ).fetchone()
        if row is None:
            return None
        payload: dict[str, Any] = json.loads(row["payload_json"])
        nodes = [
            GraphNode(
                id=n["id"],
                label=n["label"],
                kind=NodeKind(n["kind"]),
                url=n.get("url", ""),
                trust_score=float(n.get("trust_score", 0.5)),
                trust_level=TrustLevel(n.get("trust_level", "medium")),
                meta=n.get("meta", {}),
            )
            for n in payload.get("nodes", [])
        ]
        edges = [
            GraphEdge(
                source=e["source"],
                target=e["target"],
                kind=EdgeKind(e["kind"]),
                weight=float(e.get("weight", 0.5)),
                evidence=e.get("evidence", ""),
            )
            for e in payload.get("edges", [])
        ]
        return ProvenanceGraph(
            title=payload.get("title", ""),
            nodes=nodes,
            edges=edges,
            created_at=payload.get("created_at", ""),
        )


db = NewsDatabase()
