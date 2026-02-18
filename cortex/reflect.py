"""Reflection engine — synthesizes knowledge, finds patterns, and generates meta-insights."""

import json
from datetime import datetime, timezone
from pathlib import Path
from cortex import knowledge_store
from cortex.learner import find_connections, identify_gaps


REFLECTIONS_DIR = Path(__file__).resolve().parent.parent / "knowledge_base" / "reflections"
SYNTHESES_DIR = Path(__file__).resolve().parent.parent / "knowledge_base" / "syntheses"


def _save_reflection(reflection: dict, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = directory / f"{timestamp}.json"
    with open(path, "w") as f:
        json.dump(reflection, f, indent=2)
    return path


def reflect() -> dict:
    """Run a full reflection pass over the knowledge base.

    Produces a structured report:
    - Current state (stats, domain distribution)
    - Knowledge gaps
    - Strongest clusters (well-connected, high-confidence areas)
    - Growth trajectory (what's improved since last reflection)
    - Recommended next actions
    """
    stats = knowledge_store.stats() if knowledge_store.list_all() else {}
    gaps = identify_gaps()
    all_entries = knowledge_store.list_all()

    # Find strongest knowledge clusters (entries with most connections)
    clusters = []
    for entry in all_entries:
        connections = entry.get("connections", [])
        if len(connections) >= 2:
            clusters.append({
                "hub_id": entry["id"],
                "domain": entry["domain"],
                "connection_count": len(connections),
                "confidence": entry.get("confidence", 0),
                "content_preview": entry["content"][:100],
            })
    clusters.sort(key=lambda c: c["connection_count"], reverse=True)

    # Find most reliable knowledge (high confidence + reinforced)
    reliable = sorted(
        all_entries,
        key=lambda e: e.get("confidence", 0) * (1 + e.get("reinforced", 0)),
        reverse=True,
    )[:5]

    # Load previous reflections to track growth
    previous = load_reflections(limit=1)
    growth = {}
    if previous:
        prev = previous[0]
        prev_total = prev.get("state", {}).get("total_entries", 0)
        growth = {
            "entries_added_since_last": stats.get("total_entries", 0) - prev_total,
            "previous_reflection": prev.get("timestamp", "unknown"),
        }

    reflection = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "state": stats,
        "gaps": gaps,
        "strongest_clusters": clusters[:5],
        "most_reliable": [
            {"id": e["id"], "domain": e["domain"],
             "confidence": e.get("confidence", 0),
             "reinforced": e.get("reinforced", 0),
             "preview": e["content"][:80]}
            for e in reliable
        ],
        "growth": growth,
        "recommendations": _generate_recommendations(stats, gaps, clusters),
    }

    _save_reflection(reflection, REFLECTIONS_DIR)
    return reflection


def synthesize(domain: str | None = None) -> dict:
    """Synthesize knowledge within a domain (or across all domains) into a coherent summary.

    This is the key "getting smarter" operation — it takes individual facts
    and produces higher-level understanding.
    """
    if domain:
        entries = knowledge_store.list_all(domain=domain)
    else:
        entries = knowledge_store.list_all()

    if not entries:
        return {"error": "No entries to synthesize."}

    # Group by domain
    by_domain: dict[str, list[dict]] = {}
    for entry in entries:
        d = entry["domain"]
        by_domain.setdefault(d, []).append(entry)

    # Build synthesis
    domain_summaries = {}
    for d, domain_entries in by_domain.items():
        # Sort by confidence descending
        domain_entries.sort(key=lambda e: e.get("confidence", 0), reverse=True)

        key_facts = [e["content"] for e in domain_entries[:10]]
        avg_confidence = sum(e.get("confidence", 0) for e in domain_entries) / len(domain_entries)

        # Find the most connected entry as the "anchor" concept
        anchor = max(domain_entries, key=lambda e: len(e.get("connections", [])))

        # Collect all tags for theme extraction
        all_tags = []
        for e in domain_entries:
            all_tags.extend(e.get("tags", []))
        tag_freq: dict[str, int] = {}
        for t in all_tags:
            tag_freq[t] = tag_freq.get(t, 0) + 1
        top_themes = sorted(tag_freq, key=tag_freq.get, reverse=True)[:5]

        domain_summaries[d] = {
            "entry_count": len(domain_entries),
            "avg_confidence": round(avg_confidence, 3),
            "top_themes": top_themes,
            "anchor_concept": {
                "id": anchor["id"],
                "content": anchor["content"][:120],
            },
            "key_facts": key_facts,
        }

    # Cross-domain connections
    cross_domain = []
    for entry in entries:
        for conn_id in entry.get("connections", []):
            connected = knowledge_store.get(conn_id)
            if connected and connected["domain"] != entry["domain"]:
                cross_domain.append({
                    "from": {"id": entry["id"], "domain": entry["domain"]},
                    "to": {"id": connected["id"], "domain": connected["domain"]},
                })

    synthesis = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scope": domain or "all",
        "total_entries": len(entries),
        "domain_summaries": domain_summaries,
        "cross_domain_connections": cross_domain[:20],
        "maturity": _assess_maturity(entries),
    }

    _save_reflection(synthesis, SYNTHESES_DIR)
    return synthesis


def _assess_maturity(entries: list[dict]) -> dict:
    """Rate how mature/reliable the knowledge base is."""
    if not entries:
        return {"level": "empty", "score": 0}

    total = len(entries)
    avg_conf = sum(e.get("confidence", 0) for e in entries) / total
    reinforced_pct = sum(1 for e in entries if e.get("reinforced", 0) > 0) / total
    connected_pct = sum(1 for e in entries if e.get("connections")) / total

    score = (avg_conf * 40) + (reinforced_pct * 30) + (connected_pct * 20) + min(total / 100, 1) * 10
    score = round(score, 1)

    if score >= 75:
        level = "expert"
    elif score >= 50:
        level = "proficient"
    elif score >= 25:
        level = "developing"
    else:
        level = "nascent"

    return {
        "level": level,
        "score": score,
        "breakdown": {
            "avg_confidence": round(avg_conf, 3),
            "reinforced_pct": round(reinforced_pct, 3),
            "connected_pct": round(connected_pct, 3),
            "volume_factor": min(total / 100, 1.0),
        },
    }


def _generate_recommendations(stats: dict, gaps: list, clusters: list) -> list[str]:
    """Turn analysis into actionable next steps."""
    recs = []

    if not stats:
        return ["Start by ingesting knowledge. Use `cortex learn` to add your first entries."]

    total = stats.get("total_entries", 0)
    if total < 5:
        recs.append("Foundation phase: add at least 10 entries across 2-3 domains.")

    thin = [g for g in gaps if g["type"] == "thin_domain"]
    if thin:
        names = [g["domain"] for g in thin[:3]]
        recs.append(f"Deepen thin domains: {', '.join(names)}")

    low_conf = [g for g in gaps if g["type"] == "low_confidence"]
    if low_conf:
        recs.append(f"Verify {len(low_conf)} low-confidence entries with additional sources.")

    if not clusters and total >= 5:
        recs.append("No knowledge clusters yet. Look for cross-entry connections.")

    if total >= 15 and len(clusters) >= 2:
        recs.append("Ready for synthesis. Run `cortex synthesize` to build higher-level understanding.")

    return recs if recs else ["Knowledge base is in good shape. Continue expanding."]


def load_reflections(limit: int = 10) -> list[dict]:
    """Load recent reflections."""
    REFLECTIONS_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(REFLECTIONS_DIR.glob("*.json"), reverse=True)[:limit]
    results = []
    for f in files:
        with open(f) as fh:
            results.append(json.load(fh))
    return results


def load_syntheses(limit: int = 10) -> list[dict]:
    """Load recent syntheses."""
    SYNTHESES_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(SYNTHESES_DIR.glob("*.json"), reverse=True)[:limit]
    results = []
    for f in files:
        with open(f) as fh:
            results.append(json.load(fh))
    return results
