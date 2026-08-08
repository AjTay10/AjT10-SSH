---
name: knowledge-graph
description: Build and query a persistent knowledge graph of entities and relationships — creators, competitors, topics, campaigns, sources, claims — using tools/kg.py. Use when the user wants to map a space, track competitors or a niche over time, find connections, ask "who is connected to", "what am I missing", "map this out", or when research keeps rediscovering the same things. Also use to produce a mermaid diagram of a domain.
---

# Knowledge graph

Notes are lists, and lists rot because they lose the *why*. A graph keeps the
reasoning in the edges, which means the answer to "how is X related to Y"
survives past the session that discovered it.

Backed by `tools/kg.py` — one JSON file, deterministic, no dependencies.

## When a graph beats a document

Use a graph when the questions are relational: who connects to whom, what is
central, what is missing, what clusters together. Use a document when the
content is narrative. Most competitive and research work is relational and
gets forced into documents anyway, which is why the second pass repeats the
first.

## Model it before you build it

Decide the node types and relation verbs up front, and keep them small. A
graph with 40 relation types is a graph nobody can query.

A good starting schema for audience and market work:

```
node types    creator, brand, platform, topic, format, tactic, source,
              claim, campaign, audience
relations     competes_with, uses, posts_on, covers, cites, contradicts,
              inspired_by, owns, targets, monetizes_via
```

Rule: an edge should read as a sentence. `mrbeast -[uses]-> retention_editing`
reads. `mrbeast -[related_to]-> retention_editing` does not, and stores nothing.

## Commands

```bash
# Entities
python3 tools/kg.py add --id mkbhd --type creator --name "MKBHD" \
    --attr platform=youtube --attr niche=tech --attr subs=20000000

# Relationships carry the reasoning in --note
python3 tools/kg.py link --from mkbhd --to studio_quality --rel uses --weight 3 \
    --note "production value is the moat; competitors can't match capex"

# Ask questions
python3 tools/kg.py query --type creator --attr niche=tech
python3 tools/kg.py query --text "retention"          # full-text across notes
python3 tools/kg.py neighbors --id mkbhd --depth 2
python3 tools/kg.py path --from mkbhd --to newsletter # how are these connected?
python3 tools/kg.py central --top 20                  # what actually matters
python3 tools/kg.py clusters                          # natural groupings
python3 tools/kg.py stats                             # health check
python3 tools/kg.py mermaid --focus mkbhd --depth 2 > map.mmd
```

Store defaults to `.claude/data/graph.json`; override with `--store` or
`KG_STORE` to keep separate graphs per project.

## Reading the analysis

**`central`** ranks by degree and betweenness. The two disagree in the most
interesting way:

- **High degree, low betweenness** — a hub inside one cluster. Popular, but
  removing it changes little; the cluster stays connected.
- **Low degree, high betweenness** — a *bridge*. Few connections, but they are
  the only path between clusters. These are the highest-leverage and the most
  fragile nodes in any map: a single creator connecting two otherwise separate
  niches, one format that carries between platforms, one source everything
  cites. `central` calls these out explicitly.

**`clusters`** uses label propagation. Clusters that match your mental model
confirm nothing. Clusters that *cross* your mental categories are the finding —
they mean two things you treat as separate are structurally the same thing.

**`stats`** reports orphans and auto-created nodes. Orphans are notes, not
knowledge: either connect them or delete them. Auto-created nodes (made
implicitly by `link`) still lack a type and are your to-do list.

## The workflow that pays off

1. **Dump wide, sloppily.** During research, `link` liberally. `link`
   auto-creates missing nodes, so never break flow to define one first.
2. **Type the auto-created nodes afterward.** `kg.py stats` lists them.
3. **Ask the relational questions.** `central`, `clusters`, `path`.
4. **Look for the absent edge.** The real payoff. Scan for pairs that *should*
   be connected and are not — two competitors in one niche who have never
   mentioned each other, a format nobody in your space uses that dominates an
   adjacent one. Gaps are opportunities; a document cannot show you a gap.
5. **Render it.** `mermaid` output drops directly into an Artifact or a
   markdown file and renders natively.

## Hygiene

- **IDs are stable slugs, never display names.** `mkbhd`, not `MKBHD`. Names
  change; you will re-add the same entity three times otherwise.
- **Put the reasoning in `--note` on the edge.** An edge without a note is a
  fact you will not be able to evaluate in six months.
- **Use `--weight` for strength**, not for importance: 3 for a documented
  relationship, 1 for a suspected one. Then weighted degree means something.
- **Commit the graph file.** It is the accumulated asset; regenerating it
  costs more than everything else in this repo combined.

## Related

- `deep-research` — the research process that feeds the graph
- `competitor-recon` — the competitive-mapping application of it
