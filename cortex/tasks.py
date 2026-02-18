"""Task generator — produces structured, actionable research tasks from knowledge gaps."""

import json
from datetime import datetime, timezone
from pathlib import Path
from cortex import knowledge_store
from cortex.learner import identify_gaps, find_connections


TASKS_DIR = Path(__file__).resolve().parent.parent / "knowledge_base" / "tasks"


def generate_tasks() -> list[dict]:
    """Analyze the knowledge base and produce a prioritized task queue.

    Each task is a concrete action Claude can execute:
    - research: go learn about a specific topic
    - verify: find a second source for a low-confidence entry
    - connect: look for relationships between isolated entries
    - deepen: add more entries to a thin domain
    - synthesize: run a synthesis pass on a mature domain

    Tasks are ranked by priority (1 = highest).
    """
    gaps = identify_gaps()
    all_entries = knowledge_store.list_all()
    tasks = []
    priority = 1

    if not all_entries:
        tasks.append(_make_task(
            priority=1,
            action="research",
            target="any",
            description="Knowledge base is empty. Pick a domain and start ingesting foundational knowledge.",
            reasoning="Can't improve what doesn't exist yet.",
        ))
        return tasks

    # --- Priority 1: Verify low-confidence entries ---
    low_conf = [g for g in gaps if g["type"] == "low_confidence"]
    for gap in low_conf:
        entry = knowledge_store.get(gap["entry_id"])
        if entry:
            tasks.append(_make_task(
                priority=1,
                action="verify",
                target=entry["id"],
                domain=entry["domain"],
                description=f"Find a second source to confirm or refute: '{entry['content'][:100]}'",
                reasoning=f"Confidence is {entry['confidence']}, reinforced 0 times. "
                          f"Unreliable knowledge is worse than no knowledge.",
                tags=entry.get("tags", []),
            ))

    # --- Priority 2: Deepen thin domains ---
    thin = [g for g in gaps if g["type"] == "thin_domain"]
    for gap in thin:
        domain = gap["domain"]
        existing = knowledge_store.list_all(domain=domain)
        existing_tags = set()
        for e in existing:
            existing_tags.update(e.get("tags", []))

        tasks.append(_make_task(
            priority=2,
            action="deepen",
            target=domain,
            domain=domain,
            description=f"Add at least {3 - gap['count']} more entries to '{domain}'. "
                        f"Existing coverage: {', '.join(existing_tags) if existing_tags else 'minimal'}.",
            reasoning=f"Only {gap['count']} entry(ies). Need minimum 3 for meaningful connections.",
            tags=list(existing_tags),
        ))

    # --- Priority 3: Connect isolated entries ---
    isolated = [g for g in gaps if g["type"] == "isolated"]
    if isolated:
        # Group isolated entries by domain for batch connection tasks
        by_domain: dict[str, list[str]] = {}
        for gap in isolated:
            d = gap.get("domain", "unknown")
            by_domain.setdefault(d, []).append(gap["entry_id"])

        for domain, entry_ids in by_domain.items():
            # Check if there are entries in other domains that might bridge
            other_domains = [d for d in knowledge_store.domains() if d != domain]
            tasks.append(_make_task(
                priority=3,
                action="connect",
                target=entry_ids,
                domain=domain,
                description=f"Find bridging knowledge that connects {len(entry_ids)} isolated "
                            f"entry(ies) in '{domain}' to the wider knowledge graph.",
                reasoning="Isolated entries can't participate in synthesis. "
                          f"Potential bridges: {', '.join(other_domains) if other_domains else 'none yet'}.",
            ))

    # --- Priority 4: Cross-domain bridge research ---
    domains = knowledge_store.domains()
    if len(domains) >= 2:
        # Find domain pairs with no cross-connections
        for i, d1 in enumerate(domains):
            for d2 in domains[i + 1:]:
                has_bridge = False
                for entry in knowledge_store.list_all(domain=d1):
                    for conn_id in entry.get("connections", []):
                        conn = knowledge_store.get(conn_id)
                        if conn and conn["domain"] == d2:
                            has_bridge = True
                            break
                    if has_bridge:
                        break

                if not has_bridge:
                    tasks.append(_make_task(
                        priority=4,
                        action="research",
                        target=f"{d1}<->{d2}",
                        domain=f"{d1}, {d2}",
                        description=f"Research the relationship between '{d1}' and '{d2}'. "
                                    f"No cross-domain connections exist yet.",
                        reasoning="Cross-domain connections produce the most valuable insights. "
                                  "They're where synthesis generates genuinely new understanding.",
                    ))

    # --- Priority 5: Synthesis readiness check ---
    for domain in domains:
        domain_entries = knowledge_store.list_all(domain=domain)
        if len(domain_entries) >= 5:
            connected = sum(1 for e in domain_entries if e.get("connections"))
            avg_conf = sum(e.get("confidence", 0) for e in domain_entries) / len(domain_entries)
            if connected >= 3 and avg_conf >= 0.6:
                tasks.append(_make_task(
                    priority=5,
                    action="synthesize",
                    target=domain,
                    domain=domain,
                    description=f"Domain '{domain}' is ready for synthesis: {len(domain_entries)} entries, "
                                f"{connected} connected, avg confidence {avg_conf:.2f}.",
                    reasoning="Enough connected, reliable knowledge to produce higher-level understanding.",
                ))

    # Sort by priority
    tasks.sort(key=lambda t: t["priority"])
    return tasks


def _make_task(priority: int, action: str, target, description: str,
               reasoning: str, domain: str = "", tags: list[str] | None = None) -> dict:
    """Build a structured task dict."""
    return {
        "priority": priority,
        "action": action,
        "target": target,
        "domain": domain,
        "description": description,
        "reasoning": reasoning,
        "tags": tags or [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
    }


def save_task_queue(tasks: list[dict]) -> Path:
    """Persist the current task queue to disk."""
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = TASKS_DIR / f"queue_{timestamp}.json"
    with open(path, "w") as f:
        json.dump({"generated_at": datetime.now(timezone.utc).isoformat(),
                    "task_count": len(tasks), "tasks": tasks}, f, indent=2)
    return path


def load_latest_queue() -> list[dict]:
    """Load the most recent task queue."""
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(TASKS_DIR.glob("queue_*.json"), reverse=True)
    if not files:
        return []
    with open(files[0]) as f:
        data = json.load(f)
    return data.get("tasks", [])


def next_task() -> dict | None:
    """Get the highest-priority pending task."""
    tasks = generate_tasks()
    pending = [t for t in tasks if t["status"] == "pending"]
    return pending[0] if pending else None
