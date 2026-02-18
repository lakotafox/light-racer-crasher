"""Persistent knowledge store — CRUD operations for structured learning entries."""

import json
import os
import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path


KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "knowledge_base" / "entries"


def _entry_path(entry_id: str) -> Path:
    return KNOWLEDGE_DIR / f"{entry_id}.json"


def _generate_id(content: str) -> str:
    """Deterministic short ID from content + timestamp."""
    raw = f"{content}{time.time_ns()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def add(content: str, domain: str, tags: list[str] | None = None,
        source: str = "", confidence: float = 0.7) -> dict:
    """Store a new knowledge entry.

    Args:
        content: The actual insight or fact.
        domain: Top-level category (e.g. 'climate', 'biodiversity', 'security').
        tags: Optional finer-grained labels.
        source: Where this knowledge came from.
        confidence: 0.0–1.0 how reliable this knowledge is.

    Returns:
        The full entry dict including its generated ID.
    """
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)

    entry_id = _generate_id(content)
    entry = {
        "id": entry_id,
        "content": content,
        "domain": domain,
        "tags": tags or [],
        "source": source,
        "confidence": max(0.0, min(1.0, confidence)),
        "connections": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "access_count": 0,
        "reinforced": 0,
    }

    with open(_entry_path(entry_id), "w") as f:
        json.dump(entry, f, indent=2)

    return entry


def get(entry_id: str) -> dict | None:
    """Retrieve an entry by ID. Returns None if not found."""
    path = _entry_path(entry_id)
    if not path.exists():
        return None

    with open(path) as f:
        entry = json.load(f)

    # Track access
    entry["access_count"] += 1
    with open(path, "w") as f:
        json.dump(entry, f, indent=2)

    return entry


def update(entry_id: str, **kwargs) -> dict | None:
    """Update fields on an existing entry."""
    entry = get(entry_id)
    if entry is None:
        return None

    allowed = {"content", "domain", "tags", "source", "confidence", "connections"}
    for key, value in kwargs.items():
        if key in allowed:
            entry[key] = value

    entry["updated_at"] = datetime.now(timezone.utc).isoformat()

    with open(_entry_path(entry_id), "w") as f:
        json.dump(entry, f, indent=2)

    return entry


def reinforce(entry_id: str, boost: float = 0.05) -> dict | None:
    """Increase confidence when knowledge is confirmed from another source."""
    entry = get(entry_id)
    if entry is None:
        return None

    entry["reinforced"] += 1
    entry["confidence"] = min(1.0, entry["confidence"] + boost)
    entry["updated_at"] = datetime.now(timezone.utc).isoformat()

    with open(_entry_path(entry_id), "w") as f:
        json.dump(entry, f, indent=2)

    return entry


def delete(entry_id: str) -> bool:
    """Remove an entry. Returns True if it existed."""
    path = _entry_path(entry_id)
    if path.exists():
        path.unlink()
        return True
    return False


def list_all(domain: str | None = None, tag: str | None = None) -> list[dict]:
    """List entries, optionally filtered by domain or tag."""
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    entries = []

    for path in sorted(KNOWLEDGE_DIR.glob("*.json")):
        with open(path) as f:
            entry = json.load(f)

        if domain and entry.get("domain") != domain:
            continue
        if tag and tag not in entry.get("tags", []):
            continue

        entries.append(entry)

    return entries


def search(query: str) -> list[dict]:
    """Simple text search across all entries."""
    query_lower = query.lower()
    results = []

    for entry in list_all():
        text = f"{entry['content']} {entry['domain']} {' '.join(entry.get('tags', []))}"
        if query_lower in text.lower():
            results.append(entry)

    return results


def domains() -> list[str]:
    """List all unique domains in the knowledge base."""
    seen = set()
    for entry in list_all():
        seen.add(entry["domain"])
    return sorted(seen)


def stats() -> dict:
    """Return summary statistics about the knowledge base."""
    entries = list_all()
    if not entries:
        return {"total_entries": 0, "domains": [], "avg_confidence": 0.0}

    domain_counts: dict[str, int] = {}
    total_confidence = 0.0

    for entry in entries:
        d = entry["domain"]
        domain_counts[d] = domain_counts.get(d, 0) + 1
        total_confidence += entry.get("confidence", 0.0)

    return {
        "total_entries": len(entries),
        "domains": domain_counts,
        "avg_confidence": round(total_confidence / len(entries), 3),
        "most_accessed": max(entries, key=lambda e: e.get("access_count", 0))["id"],
        "most_reinforced": max(entries, key=lambda e: e.get("reinforced", 0))["id"],
    }
