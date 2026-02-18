# Cortex

Recursive knowledge system for AI-assisted learning and decision-making.

Cortex gives Claude (or any AI assistant) a persistent, structured memory that compounds over time. It stores individual learnings, automatically finds connections between them, identifies knowledge gaps, and synthesizes higher-level understanding through reflection.

## How It Works

1. **Learn** — Ingest facts, insights, and observations into structured entries
2. **Connect** — Automatically finds relationships between entries based on content, tags, and domains
3. **Reflect** — Periodic reflection passes analyze the full knowledge base, spotting gaps and clusters
4. **Synthesize** — Combines individual entries into domain-level understanding
5. **Repeat** — Each cycle builds on the last, reinforcing strong knowledge and flagging weak areas

## Usage

```bash
# Learn something new
python -m cortex.cli learn "Coral bleaching accelerates above 1.5C warming" -d climate -t "ocean,coral,temperature"

# Search existing knowledge
python -m cortex.cli search "coral"

# See what's in the knowledge base
python -m cortex.cli list
python -m cortex.cli list -d climate

# Identify gaps — what needs more depth
python -m cortex.cli gaps

# Run a reflection pass
python -m cortex.cli reflect

# Synthesize knowledge into higher-level understanding
python -m cortex.cli synthesize
python -m cortex.cli synthesize -d climate

# Stats
python -m cortex.cli stats
```

## Architecture

```
cortex/
  __init__.py          # Package init
  knowledge_store.py   # CRUD for knowledge entries (JSON file-based)
  learner.py           # Ingestion, deduplication, connection-finding, gap analysis
  reflect.py           # Reflection engine, synthesis, maturity scoring
  cli.py               # Command-line interface

knowledge_base/
  entries/             # Individual knowledge entries (JSON)
  reflections/         # Reflection pass outputs
  syntheses/           # Synthesis outputs
```

## Knowledge Entries

Each entry is a JSON file containing:

- **content** — the actual fact or insight
- **domain** — top-level category (climate, biodiversity, security, etc.)
- **tags** — finer-grained labels for connection-finding
- **confidence** — 0.0 to 1.0, how reliable this knowledge is
- **connections** — IDs of related entries (auto-discovered)
- **reinforced** — how many times this was confirmed from different sources

## Maturity Model

The system tracks knowledge base maturity across four levels:

| Level | Score | Meaning |
|---|---|---|
| Nascent | 0-25 | Just getting started |
| Developing | 25-50 | Building breadth, low connectivity |
| Proficient | 50-75 | Good coverage, connections forming |
| Expert | 75-100 | Deep, well-connected, reinforced knowledge |

## Design Principles

- **File-based** — everything is JSON on disk, git-friendly, no database required
- **Zero dependencies** — pure Python stdlib, runs anywhere
- **Compounding** — knowledge reinforcement and connection-finding mean the system gets more valuable over time
- **Transparent** — every entry, reflection, and synthesis is readable JSON you can inspect
