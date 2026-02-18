"""Learner — ingests new information, finds connections, identifies knowledge gaps."""

from difflib import SequenceMatcher
from cortex import knowledge_store


def _similarity(a: str, b: str) -> float:
    """Quick string similarity score between 0 and 1."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _tag_overlap(tags_a: list[str], tags_b: list[str]) -> float:
    """Jaccard similarity between two tag sets."""
    if not tags_a and not tags_b:
        return 0.0
    set_a, set_b = set(tags_a), set(tags_b)
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) if union else 0.0


def ingest(content: str, domain: str, tags: list[str] | None = None,
           source: str = "", confidence: float = 0.7) -> dict:
    """Learn something new — store it and automatically find connections.

    If the knowledge closely matches an existing entry, reinforce that
    entry instead of creating a duplicate.
    """
    tags = tags or []

    # Check for near-duplicates first
    existing = knowledge_store.list_all(domain=domain)
    for entry in existing:
        sim = _similarity(content, entry["content"])
        if sim > 0.85:
            # Reinforce rather than duplicate
            knowledge_store.reinforce(entry["id"])
            # Merge in any new tags
            merged_tags = list(set(entry.get("tags", []) + tags))
            knowledge_store.update(entry["id"], tags=merged_tags)
            return {"action": "reinforced", "entry": knowledge_store.get(entry["id"])}

    # New knowledge — store it
    entry = knowledge_store.add(content, domain, tags, source, confidence)

    # Find and record connections to existing entries
    connections = find_connections(entry["id"])
    if connections:
        knowledge_store.update(entry["id"], connections=[c["id"] for c in connections])

    return {"action": "created", "entry": entry, "connections_found": len(connections)}


def find_connections(entry_id: str, threshold: float = 0.3) -> list[dict]:
    """Find entries related to the given entry based on content + tag overlap.

    Returns a list of related entries sorted by relevance score.
    """
    target = knowledge_store.get(entry_id)
    if target is None:
        return []

    all_entries = knowledge_store.list_all()
    scored = []

    for entry in all_entries:
        if entry["id"] == entry_id:
            continue

        # Weighted scoring: content similarity + tag overlap + same domain bonus
        content_score = _similarity(target["content"], entry["content"])
        tag_score = _tag_overlap(target.get("tags", []), entry.get("tags", []))
        domain_bonus = 0.15 if target["domain"] == entry["domain"] else 0.0

        relevance = (content_score * 0.5) + (tag_score * 0.35) + domain_bonus

        if relevance >= threshold:
            scored.append({**entry, "_relevance": round(relevance, 3)})

    scored.sort(key=lambda e: e["_relevance"], reverse=True)
    return scored[:10]


def identify_gaps() -> list[dict]:
    """Analyze the knowledge base and identify areas that need more depth.

    Looks for:
    - Domains with few entries
    - Entries with low confidence that haven't been reinforced
    - Clusters of connected entries that lack a synthesis
    """
    all_entries = knowledge_store.list_all()
    if not all_entries:
        return [{"type": "empty", "message": "Knowledge base is empty. Start learning."}]

    gaps = []

    # 1. Thin domains (fewer than 3 entries)
    domain_counts: dict[str, int] = {}
    for entry in all_entries:
        d = entry["domain"]
        domain_counts[d] = domain_counts.get(d, 0) + 1

    for domain, count in domain_counts.items():
        if count < 3:
            gaps.append({
                "type": "thin_domain",
                "domain": domain,
                "count": count,
                "message": f"Domain '{domain}' has only {count} entry(ies). Needs more depth.",
            })

    # 2. Low-confidence, unreinforced entries
    for entry in all_entries:
        if entry.get("confidence", 0) < 0.5 and entry.get("reinforced", 0) == 0:
            gaps.append({
                "type": "low_confidence",
                "entry_id": entry["id"],
                "domain": entry["domain"],
                "confidence": entry["confidence"],
                "message": f"Entry '{entry['id']}' in '{entry['domain']}' has low confidence "
                           f"({entry['confidence']}) and zero reinforcement. Needs verification.",
            })

    # 3. Isolated entries (no connections)
    for entry in all_entries:
        if not entry.get("connections"):
            gaps.append({
                "type": "isolated",
                "entry_id": entry["id"],
                "domain": entry["domain"],
                "message": f"Entry '{entry['id']}' has no connections. May be an outlier or "
                           f"a seed for a new knowledge cluster.",
            })

    return gaps


def suggest_next_topics() -> list[str]:
    """Based on current gaps and domain coverage, suggest what to learn next."""
    gaps = identify_gaps()
    suggestions = []

    thin_domains = [g for g in gaps if g["type"] == "thin_domain"]
    for g in thin_domains:
        suggestions.append(f"Deepen knowledge in '{g['domain']}' (only {g['count']} entries)")

    low_conf = [g for g in gaps if g["type"] == "low_confidence"]
    if low_conf:
        suggestions.append(
            f"Verify {len(low_conf)} low-confidence entries — seek confirming sources"
        )

    isolated = [g for g in gaps if g["type"] == "isolated"]
    if isolated:
        suggestions.append(
            f"Connect {len(isolated)} isolated entries — look for cross-domain relationships"
        )

    # If knowledge base is mature, push toward synthesis
    all_entries = knowledge_store.list_all()
    if len(all_entries) >= 10:
        domains = knowledge_store.domains()
        if len(domains) >= 3:
            suggestions.append(
                "Knowledge base has breadth — consider running a reflection/synthesis pass"
            )

    return suggestions if suggestions else ["Knowledge base looks healthy. Keep learning."]
