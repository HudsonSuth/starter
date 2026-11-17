"""File-backed agent memory — agent writes exact statements; no LLM inference."""

from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from ..authorship import agent_author, normalize_authored_by


@dataclass
class MemoryRecord:
    id: str
    memory: str
    created_at: float
    authored_by: str
    user_id: str | None = None
    agent_id: str | None = None
    session_id: str | None = None
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryRecord:
        return cls(
            id=data["id"],
            memory=data["memory"],
            created_at=float(data["created_at"]),
            authored_by=data["authored_by"],
            user_id=data.get("user_id"),
            agent_id=data.get("agent_id"),
            session_id=data.get("session_id"),
            tags=list(data.get("tags") or []),
        )


class FileMemoryStore:
    """OpenSearch Memory Tools–shaped API over a JSONL directory.

    Rules-only: the caller supplies the statement; nothing is extracted by a model.
    """

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "memories.jsonl"

    def _read_all(self) -> list[MemoryRecord]:
        if not self.index_path.exists():
            return []
        out: list[MemoryRecord] = []
        for line in self.index_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            out.append(MemoryRecord.from_dict(json.loads(line)))
        return out

    def _write_all(self, records: list[MemoryRecord]) -> None:
        tmp = self.index_path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            for rec in records:
                fh.write(json.dumps(rec.to_dict(), ensure_ascii=False) + "\n")
        tmp.replace(self.index_path)

    def save(
        self,
        memory: str,
        *,
        bot_name: str | None = None,
        authored_by: str | None = None,
        user_id: str | None = None,
        agent_id: str | None = None,
        session_id: str | None = None,
        tags: str | list[str] | None = None,
    ) -> MemoryRecord:
        text = (memory or "").strip()
        if not text:
            raise ValueError("memory is required")
        tag_list: list[str]
        if tags is None:
            tag_list = []
        elif isinstance(tags, str):
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        else:
            tag_list = [str(t).strip() for t in tags if str(t).strip()]

        author = normalize_authored_by(
            authored_by or (agent_author(bot_name) if bot_name else None) or agent_id,
            default_bot=bot_name or agent_id or "memory",
        )
        rec = MemoryRecord(
            id=str(uuid.uuid4()),
            memory=text,
            created_at=time.time(),
            authored_by=author,
            user_id=user_id,
            agent_id=agent_id or (author.split("/", 1)[-1] if author.startswith("grokbot/") else None),
            session_id=session_id,
            tags=tag_list,
        )
        records = self._read_all()
        records.append(rec)
        self._write_all(records)
        return rec

    def search(
        self,
        query: str,
        *,
        user_id: str | None = None,
        agent_id: str | None = None,
        session_id: str | None = None,
        tags: str | None = None,
        size: int = 10,
    ) -> list[MemoryRecord]:
        size = max(1, min(int(size or 10), 100))
        wanted_tags = {t.strip() for t in (tags or "").split(",") if t.strip()}
        q = (query or "").strip()
        records = self._read_all()

        def ok(rec: MemoryRecord) -> bool:
            if user_id and rec.user_id != user_id:
                return False
            if agent_id and rec.agent_id != agent_id:
                return False
            if session_id and rec.session_id != session_id:
                return False
            if wanted_tags and not wanted_tags.issubset(set(rec.tags)):
                return False
            return True

        filtered = [r for r in records if ok(r)]
        if q == "*" or q == "":
            filtered.sort(key=lambda r: r.created_at, reverse=True)
            return filtered[:size]

        # Rules-only lexical match (no embeddings / paid models).
        terms = [t for t in re.split(r"\W+", q.lower()) if t]
        scored: list[tuple[int, MemoryRecord]] = []
        for rec in filtered:
            hay = rec.memory.lower()
            score = sum(1 for t in terms if t in hay)
            if score:
                scored.append((score, rec))
        scored.sort(key=lambda x: (x[0], x[1].created_at), reverse=True)
        return [r for _, r in scored[:size]]

    def delete(self, memory_id: str) -> bool:
        records = self._read_all()
        kept = [r for r in records if r.id != memory_id]
        if len(kept) == len(records):
            return False
        self._write_all(kept)
        return True
