"""CLI interface for Cortex — interact with the knowledge system from the terminal."""

import argparse
import json
import sys
from cortex import knowledge_store
from cortex.learner import ingest, identify_gaps, suggest_next_topics
from cortex.reflect import reflect, synthesize
from cortex.tasks import generate_tasks, save_task_queue, next_task


def _print_json(data: dict | list, compact: bool = False):
    """Pretty-print JSON data."""
    indent = None if compact else 2
    print(json.dumps(data, indent=indent, default=str))


def cmd_learn(args):
    """Ingest a new piece of knowledge."""
    tags = [t.strip() for t in args.tags.split(",")] if args.tags else []
    result = ingest(
        content=args.content,
        domain=args.domain,
        tags=tags,
        source=args.source or "",
        confidence=args.confidence,
    )
    action = result["action"]
    entry = result["entry"]

    if action == "reinforced":
        print(f"Reinforced existing entry {entry['id']} (confidence: {entry['confidence']})")
    else:
        print(f"Learned: {entry['id']} [{entry['domain']}]")
        conns = result.get("connections_found", 0)
        if conns:
            print(f"  Found {conns} connection(s) to existing knowledge")


def cmd_search(args):
    """Search the knowledge base."""
    results = knowledge_store.search(args.query)
    if not results:
        print("No matches found.")
        return

    print(f"Found {len(results)} result(s):\n")
    for entry in results:
        print(f"  [{entry['id']}] ({entry['domain']}) conf={entry.get('confidence', '?')}")
        print(f"    {entry['content'][:120]}")
        if entry.get("tags"):
            print(f"    tags: {', '.join(entry['tags'])}")
        print()


def cmd_list(args):
    """List entries in the knowledge base."""
    entries = knowledge_store.list_all(domain=args.domain, tag=args.tag)
    if not entries:
        print("Knowledge base is empty." if not args.domain else f"No entries in domain '{args.domain}'.")
        return

    print(f"{len(entries)} entries:\n")
    for entry in entries:
        reinforced = f" +{entry['reinforced']}x" if entry.get("reinforced") else ""
        conns = len(entry.get("connections", []))
        print(f"  [{entry['id']}] {entry['domain']:<15} conf={entry.get('confidence', 0):.2f}{reinforced}  conns={conns}")
        print(f"    {entry['content'][:100]}")
        print()


def cmd_get(args):
    """Get a specific entry by ID."""
    entry = knowledge_store.get(args.id)
    if entry is None:
        print(f"Entry '{args.id}' not found.")
        sys.exit(1)
    _print_json(entry)


def cmd_gaps(args):
    """Show knowledge gaps and suggested next topics."""
    gaps = identify_gaps()
    suggestions = suggest_next_topics()

    print("=== Knowledge Gaps ===\n")
    if not gaps:
        print("  No gaps identified.\n")
    else:
        for gap in gaps:
            print(f"  [{gap['type']}] {gap['message']}")
        print()

    print("=== Suggested Next Topics ===\n")
    for s in suggestions:
        print(f"  -> {s}")
    print()


def cmd_reflect(args):
    """Run a reflection pass over the knowledge base."""
    print("Running reflection...\n")
    result = reflect()

    print(f"=== Reflection — {result['timestamp'][:10]} ===\n")

    state = result.get("state", {})
    if state:
        print(f"  Entries: {state.get('total_entries', 0)}")
        print(f"  Avg confidence: {state.get('avg_confidence', 0)}")
        domains = state.get("domains", {})
        if domains:
            print(f"  Domains: {', '.join(f'{k}({v})' for k, v in domains.items())}")
        print()

    growth = result.get("growth", {})
    if growth:
        print(f"  Growth since last reflection: +{growth.get('entries_added_since_last', '?')} entries")
        print()

    clusters = result.get("strongest_clusters", [])
    if clusters:
        print("  Strongest clusters:")
        for c in clusters:
            print(f"    [{c['hub_id']}] {c['domain']} — {c['connection_count']} connections")
        print()

    recs = result.get("recommendations", [])
    if recs:
        print("  Recommendations:")
        for r in recs:
            print(f"    -> {r}")
        print()


def cmd_synthesize(args):
    """Synthesize knowledge into higher-level understanding."""
    print(f"Synthesizing{'  domain=' + args.domain if args.domain else ' all domains'}...\n")
    result = synthesize(domain=args.domain)

    if "error" in result:
        print(f"  {result['error']}")
        return

    maturity = result.get("maturity", {})
    print(f"  Maturity: {maturity.get('level', '?')} (score: {maturity.get('score', 0)})")
    print(f"  Total entries in scope: {result.get('total_entries', 0)}")
    print()

    for domain, summary in result.get("domain_summaries", {}).items():
        print(f"  --- {domain} ---")
        print(f"    Entries: {summary['entry_count']}, Avg confidence: {summary['avg_confidence']}")
        if summary.get("top_themes"):
            print(f"    Themes: {', '.join(summary['top_themes'])}")
        print(f"    Anchor: {summary['anchor_concept']['content']}")
        print()

    cross = result.get("cross_domain_connections", [])
    if cross:
        print("  Cross-domain connections:")
        for c in cross:
            print(f"    {c['from']['domain']} -> {c['to']['domain']}")
        print()


def cmd_stats(args):
    """Show knowledge base statistics."""
    entries = knowledge_store.list_all()
    if not entries:
        print("Knowledge base is empty.")
        return

    stats = knowledge_store.stats()
    _print_json(stats)


def cmd_tasks(args):
    """Generate and display prioritized research tasks."""
    tasks = generate_tasks()

    if not tasks:
        print("No tasks to generate. Knowledge base may be in good shape.")
        return

    if args.save:
        path = save_task_queue(tasks)
        print(f"Task queue saved to {path}\n")

    priority_labels = {1: "CRITICAL", 2: "HIGH", 3: "MEDIUM", 4: "LOW", 5: "WHEN READY"}
    action_labels = {
        "research": "RESEARCH",
        "verify": "VERIFY",
        "connect": "CONNECT",
        "deepen": "DEEPEN",
        "synthesize": "SYNTHESIZE",
    }

    print(f"=== Task Queue ({len(tasks)} tasks) ===\n")
    for i, task in enumerate(tasks, 1):
        pri = priority_labels.get(task["priority"], f"P{task['priority']}")
        act = action_labels.get(task["action"], task["action"].upper())
        domain = f" [{task['domain']}]" if task.get("domain") else ""
        print(f"  {i}. [{pri}] {act}{domain}")
        print(f"     {task['description']}")
        print(f"     Why: {task['reasoning']}")
        if task.get("tags"):
            print(f"     Related: {', '.join(task['tags'])}")
        print()


def cmd_next(args):
    """Show the single highest-priority task to work on next."""
    task = next_task()
    if task is None:
        print("No pending tasks. Knowledge base is in good shape.")
        return

    priority_labels = {1: "CRITICAL", 2: "HIGH", 3: "MEDIUM", 4: "LOW", 5: "WHEN READY"}
    pri = priority_labels.get(task["priority"], f"P{task['priority']}")

    print(f"=== Next Task [{pri}] ===\n")
    print(f"  Action:  {task['action'].upper()}")
    if task.get("domain"):
        print(f"  Domain:  {task['domain']}")
    print(f"  Task:    {task['description']}")
    print(f"  Why:     {task['reasoning']}")
    if task.get("tags"):
        print(f"  Related: {', '.join(task['tags'])}")
    print()


def cmd_delete(args):
    """Delete an entry."""
    if knowledge_store.delete(args.id):
        print(f"Deleted entry '{args.id}'.")
    else:
        print(f"Entry '{args.id}' not found.")


def main():
    parser = argparse.ArgumentParser(
        prog="cortex",
        description="Cortex — Recursive knowledge system for AI-assisted learning",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # learn
    p_learn = subparsers.add_parser("learn", help="Ingest new knowledge")
    p_learn.add_argument("content", help="The knowledge/insight to store")
    p_learn.add_argument("-d", "--domain", required=True, help="Knowledge domain (e.g. climate, biodiversity)")
    p_learn.add_argument("-t", "--tags", default="", help="Comma-separated tags")
    p_learn.add_argument("-s", "--source", default="", help="Where this knowledge came from")
    p_learn.add_argument("-c", "--confidence", type=float, default=0.7, help="Confidence 0.0-1.0 (default: 0.7)")
    p_learn.set_defaults(func=cmd_learn)

    # search
    p_search = subparsers.add_parser("search", help="Search the knowledge base")
    p_search.add_argument("query", help="Search query")
    p_search.set_defaults(func=cmd_search)

    # list
    p_list = subparsers.add_parser("list", help="List knowledge entries")
    p_list.add_argument("-d", "--domain", default=None, help="Filter by domain")
    p_list.add_argument("-t", "--tag", default=None, help="Filter by tag")
    p_list.set_defaults(func=cmd_list)

    # get
    p_get = subparsers.add_parser("get", help="Get a specific entry by ID")
    p_get.add_argument("id", help="Entry ID")
    p_get.set_defaults(func=cmd_get)

    # gaps
    p_gaps = subparsers.add_parser("gaps", help="Identify knowledge gaps")
    p_gaps.set_defaults(func=cmd_gaps)

    # reflect
    p_reflect = subparsers.add_parser("reflect", help="Run a reflection pass")
    p_reflect.set_defaults(func=cmd_reflect)

    # synthesize
    p_synth = subparsers.add_parser("synthesize", help="Synthesize knowledge into higher-level understanding")
    p_synth.add_argument("-d", "--domain", default=None, help="Limit to a specific domain")
    p_synth.set_defaults(func=cmd_synthesize)

    # stats
    p_stats = subparsers.add_parser("stats", help="Show knowledge base statistics")
    p_stats.set_defaults(func=cmd_stats)

    # tasks
    p_tasks = subparsers.add_parser("tasks", help="Generate prioritized research tasks")
    p_tasks.add_argument("--save", action="store_true", help="Save task queue to disk")
    p_tasks.set_defaults(func=cmd_tasks)

    # next
    p_next = subparsers.add_parser("next", help="Show the single highest-priority task")
    p_next.set_defaults(func=cmd_next)

    # delete
    p_del = subparsers.add_parser("delete", help="Delete an entry")
    p_del.add_argument("id", help="Entry ID to delete")
    p_del.set_defaults(func=cmd_delete)

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
