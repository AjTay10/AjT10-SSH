#!/usr/bin/env python3
"""kg — a tiny knowledge graph you actually keep, in one JSON file.

Notes rot because they are lists. A graph survives because the edges carry the
reasoning. Use this to track accounts, creators, topics, campaigns, sources and
claims, then ask it who matters and what connects to what.

    python3 tools/kg.py add   --id mrbeast --type creator --name "MrBeast" \\
        --attr platform=youtube --attr subs=340000000
    python3 tools/kg.py link  --from mrbeast --to retention_editing --rel uses \\
        --weight 3 --note "hard cut every 1.5s"
    python3 tools/kg.py query --type creator --attr platform=youtube
    python3 tools/kg.py neighbors --id mrbeast --depth 2
    python3 tools/kg.py path      --from mrbeast --to shorts_strategy
    python3 tools/kg.py central   --top 15
    python3 tools/kg.py clusters
    python3 tools/kg.py mermaid   --focus mrbeast --depth 2 > graph.mmd
    python3 tools/kg.py stats

Store defaults to .claude/data/graph.json (override with --store or KG_STORE).
Deterministic: no randomness anywhere, so two runs give the same answer.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict, deque

DEFAULT_STORE = os.environ.get("KG_STORE", ".claude/data/graph.json")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,79}$")


class KGError(ValueError):
    pass


def load(path):
    if not os.path.exists(path):
        return {"nodes": {}, "edges": []}
    try:
        with open(path, encoding="utf-8") as fh:
            g = json.load(fh)
    except json.JSONDecodeError as e:
        raise KGError(f"{path} is not valid JSON ({e}). Fix or move it aside.")
    if not isinstance(g, dict) or "nodes" not in g or "edges" not in g:
        raise KGError(f"{path} is not a graph file (needs 'nodes' and 'edges')")
    g.setdefault("nodes", {})
    g.setdefault("edges", [])
    return g


def save(path, g):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(g, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, path)   # atomic: a crash mid-write never truncates the graph


def kv(pairs):
    out = {}
    for p in pairs or []:
        if "=" not in p:
            raise KGError(f"--attr must be key=value, got {p!r}")
        k, v = p.split("=", 1)
        k = k.strip()
        if not k:
            raise KGError(f"--attr has an empty key: {p!r}")
        out[k] = v.strip()
    return out


def adj(g, directed=False):
    a = defaultdict(list)
    for e in g["edges"]:
        a[e["from"]].append((e["to"], e))
        if not directed:
            a[e["to"]].append((e["from"], e))
    return a


def check_id(i):
    if not ID_RE.match(i or ""):
        raise KGError(
            f"bad id {i!r}: use letters, digits, _ . : - (max 80 chars, no spaces)")
    return i


# --------------------------------------------------------------------------

def cmd_add(a):
    g = load(a.store)
    nid = check_id(a.id)
    node = g["nodes"].get(nid, {})
    node["type"] = a.type or node.get("type", "thing")
    node["name"] = a.name or node.get("name", nid)
    attrs = node.get("attrs", {})
    attrs.update(kv(a.attr))
    node["attrs"] = attrs
    if a.note:
        notes = node.get("notes", [])
        notes.append(a.note)
        node["notes"] = notes
    existed = nid in g["nodes"]
    g["nodes"][nid] = node
    save(a.store, g)
    print(f"{'updated' if existed else 'added'} {nid} ({node['type']})")
    return 0


def cmd_link(a):
    g = load(a.store)
    src, dst = check_id(getattr(a, "from")), check_id(a.to)
    if src == dst and not a.allow_self:
        raise KGError("refusing a self-loop; pass --allow-self if you mean it")
    for nid in (src, dst):
        if nid not in g["nodes"]:
            g["nodes"][nid] = {"type": "thing", "name": nid, "attrs": {},
                               "auto": True}
    for e in g["edges"]:
        if e["from"] == src and e["to"] == dst and e["rel"] == a.rel:
            e["weight"] = a.weight
            if a.note:
                e["note"] = a.note
            save(a.store, g)
            print(f"updated edge {src} -[{a.rel}]-> {dst}")
            return 0
    edge = {"from": src, "to": dst, "rel": a.rel, "weight": a.weight}
    if a.note:
        edge["note"] = a.note
    g["edges"].append(edge)
    save(a.store, g)
    print(f"linked {src} -[{a.rel}]-> {dst}")
    return 0


def cmd_rm(a):
    g = load(a.store)
    if a.id not in g["nodes"]:
        raise KGError(f"no node {a.id!r}")
    del g["nodes"][a.id]
    before = len(g["edges"])
    g["edges"] = [e for e in g["edges"] if a.id not in (e["from"], e["to"])]
    save(a.store, g)
    print(f"removed {a.id} and {before - len(g['edges'])} edge(s)")
    return 0


def cmd_query(a):
    g = load(a.store)
    want = kv(a.attr)
    hits = []
    for nid, n in g["nodes"].items():
        if a.type and n.get("type") != a.type:
            continue
        if a.text:
            hay = " ".join([nid, n.get("name", ""), json.dumps(n.get("attrs", {})),
                            " ".join(n.get("notes", []))]).lower()
            if a.text.lower() not in hay:
                continue
        if any(str(n.get("attrs", {}).get(k, "")).lower() != v.lower()
               for k, v in want.items()):
            continue
        hits.append((nid, n))
    hits.sort()
    if a.json:
        print(json.dumps({k: v for k, v in hits}, indent=2, ensure_ascii=False))
        return 0
    if not hits:
        print("no matches")
        return 0
    for nid, n in hits:
        attrs = " ".join(f"{k}={v}" for k, v in sorted(n.get("attrs", {}).items()))
        print(f"{nid:<28}{n.get('type',''):<14}{n.get('name','')[:28]:<30}{attrs}")
    print(f"\n{len(hits)} node(s)")
    return 0


def cmd_neighbors(a):
    g = load(a.store)
    if a.id not in g["nodes"]:
        raise KGError(f"no node {a.id!r}")
    A = adj(g)
    seen, out = {a.id: 0}, []
    q = deque([(a.id, 0)])
    while q:
        cur, d = q.popleft()
        if d >= a.depth:
            continue
        for nb, e in sorted(A[cur], key=lambda p: p[0]):
            if nb not in seen:
                seen[nb] = d + 1
                out.append((d + 1, cur, e["rel"], nb))
                q.append((nb, d + 1))
    if a.json:
        print(json.dumps([{"depth": d, "from": f, "rel": r, "to": t}
                          for d, f, r, t in out], indent=2))
        return 0
    for d, f, r, t in out:
        name = g["nodes"].get(t, {}).get("name", t)
        print(f"{'  '*d}{'└─' if d else ''}[{r}] {t}  ({name})")
    print(f"\n{len(out)} node(s) within depth {a.depth}")
    return 0


def cmd_path(a):
    g = load(a.store)
    src, dst = getattr(a, "from"), a.to
    for nid in (src, dst):
        if nid not in g["nodes"]:
            raise KGError(f"no node {nid!r}")
    A = adj(g)
    prev, q = {src: None}, deque([src])
    while q:
        cur = q.popleft()
        if cur == dst:
            break
        for nb, e in sorted(A[cur], key=lambda p: p[0]):
            if nb not in prev:
                prev[nb] = (cur, e["rel"])
                q.append(nb)
    if dst not in prev:
        print(f"no path between {src} and {dst}")
        return 1
    chain, cur = [], dst
    while cur is not None and prev[cur] is not None:
        p, rel = prev[cur]
        chain.append((p, rel, cur))
        cur = p
    chain.reverse()
    if a.json:
        print(json.dumps([{"from": f, "rel": r, "to": t} for f, r, t in chain], indent=2))
        return 0
    print(src)
    for f, r, t in chain:
        print(f"  -[{r}]-> {t}")
    print(f"\n{len(chain)} hop(s)")
    return 0


def _betweenness(g):
    """Brandes' algorithm, unweighted. Deterministic ordering throughout."""
    nodes = sorted(g["nodes"])
    A = adj(g)
    bc = {n: 0.0 for n in nodes}
    for s in nodes:
        stack, preds = [], {n: [] for n in nodes}
        sigma = {n: 0.0 for n in nodes}
        dist = {n: -1 for n in nodes}
        sigma[s], dist[s] = 1.0, 0
        q = deque([s])
        while q:
            v = q.popleft()
            stack.append(v)
            for w, _ in sorted(A[v], key=lambda p: p[0]):
                if dist[w] < 0:
                    dist[w] = dist[v] + 1
                    q.append(w)
                if dist[w] == dist[v] + 1:
                    sigma[w] += sigma[v]
                    preds[w].append(v)
        delta = {n: 0.0 for n in nodes}
        while stack:
            w = stack.pop()
            for v in preds[w]:
                delta[v] += (sigma[v] / sigma[w]) * (1 + delta[w]) if sigma[w] else 0
            if w != s:
                bc[w] += delta[w]
    n = len(nodes)
    # Undirected: every pair is walked from both endpoints, so halve before
    # normalizing. Without the halving, scores exceed 1.0 and stop being
    # comparable across graphs of different sizes.
    scale = 1.0 / ((n - 1) * (n - 2)) if n > 2 else 1.0
    return {k: v * scale for k, v in bc.items()}


def cmd_central(a):
    g = load(a.store)
    if not g["nodes"]:
        print("graph is empty")
        return 0
    A = adj(g)
    deg = {n: len(A[n]) for n in g["nodes"]}
    wdeg = {n: sum(e.get("weight", 1) for _, e in A[n]) for n in g["nodes"]}
    bc = _betweenness(g) if len(g["nodes"]) <= 800 else {n: 0.0 for n in g["nodes"]}
    rows = sorted(g["nodes"], key=lambda n: (-deg[n], -bc[n], n))[:a.top]
    if a.json:
        print(json.dumps([{"id": n, "degree": deg[n], "weighted_degree": wdeg[n],
                           "betweenness": round(bc[n], 5),
                           "type": g["nodes"][n].get("type")} for n in rows], indent=2))
        return 0
    print(f"{'node':<28}{'type':<14}{'deg':>5}{'wdeg':>7}{'between':>10}")
    print("-" * 64)
    for n in rows:
        print(f"{n[:27]:<28}{str(g['nodes'][n].get('type',''))[:13]:<14}"
              f"{deg[n]:>5}{wdeg[n]:>7.0f}{bc[n]:>10.4f}")
    bridges = [n for n in rows if bc[n] > 0 and deg[n] <= 3]
    if bridges:
        print(f"\nbridges (low degree, high betweenness — fragile single points "
              f"of connection): {', '.join(bridges[:5])}")
    return 0


def cmd_clusters(a):
    """Label propagation with deterministic tie-breaking."""
    g = load(a.store)
    nodes = sorted(g["nodes"])
    if not nodes:
        print("graph is empty")
        return 0
    A = adj(g)
    label = {n: n for n in nodes}
    for _ in range(30):
        changed = False
        for n in nodes:
            if not A[n]:
                continue
            tally = defaultdict(float)
            for nb, e in A[n]:
                tally[label[nb]] += float(e.get("weight", 1) or 1)
            best = sorted(tally.items(), key=lambda kv_: (-kv_[1], kv_[0]))[0][0]
            if best != label[n]:
                label[n] = best
                changed = True
        if not changed:
            break
    groups = defaultdict(list)
    for n in nodes:
        groups[label[n]].append(n)
    ordered = sorted(groups.values(), key=lambda v: (-len(v), v[0]))
    if a.json:
        print(json.dumps(ordered, indent=2))
        return 0
    for i, grp in enumerate(ordered, 1):
        names = ", ".join(g["nodes"][n].get("name", n) for n in grp[:8])
        more = f" (+{len(grp)-8})" if len(grp) > 8 else ""
        print(f"cluster {i} [{len(grp)}]: {names}{more}")
    singles = sum(1 for grp in ordered if len(grp) == 1)
    print(f"\n{len(ordered)} cluster(s); {singles} isolated node(s)")
    return 0


def cmd_mermaid(a):
    g = load(a.store)
    nodes, edges = set(g["nodes"]), g["edges"]
    if a.focus:
        if a.focus not in g["nodes"]:
            raise KGError(f"no node {a.focus!r}")
        A = adj(g)
        keep, q = {a.focus}, deque([(a.focus, 0)])
        while q:
            cur, d = q.popleft()
            if d >= a.depth:
                continue
            for nb, _ in A[cur]:
                if nb not in keep:
                    keep.add(nb)
                    q.append((nb, d + 1))
        nodes = keep
        edges = [e for e in edges if e["from"] in keep and e["to"] in keep]

    def safe(i):
        return re.sub(r"[^A-Za-z0-9_]", "_", i)

    lines = ["graph LR"]
    by_type = defaultdict(list)
    for n in sorted(nodes):
        by_type[g["nodes"][n].get("type", "thing")].append(n)
    for t, members in sorted(by_type.items()):
        lines.append(f'  subgraph {safe(t)}["{t}"]')
        for n in members:
            label = str(g["nodes"][n].get("name", n)).replace('"', "'")
            lines.append(f'    {safe(n)}["{label}"]')
        lines.append("  end")
    for e in edges:
        rel = str(e.get("rel", "")).replace('"', "'")
        lines.append(f'  {safe(e["from"])} -->|{rel}| {safe(e["to"])}')
    print("\n".join(lines))
    return 0


def cmd_stats(a):
    g = load(a.store)
    types = defaultdict(int)
    for n in g["nodes"].values():
        types[n.get("type", "thing")] += 1
    rels = defaultdict(int)
    for e in g["edges"]:
        rels[e.get("rel", "?")] += 1
    A = adj(g)
    orphans = [n for n in sorted(g["nodes"]) if not A[n]]
    auto = [n for n, v in sorted(g["nodes"].items()) if v.get("auto")]
    out = {"store": a.store, "nodes": len(g["nodes"]), "edges": len(g["edges"]),
           "types": dict(sorted(types.items())), "relations": dict(sorted(rels.items())),
           "orphans": orphans[:20], "orphan_count": len(orphans),
           "auto_created": auto[:20], "auto_created_count": len(auto)}
    if a.json:
        print(json.dumps(out, indent=2))
        return 0
    print(f"store   {a.store}")
    print(f"nodes   {out['nodes']}    edges {out['edges']}")
    print("types   " + ", ".join(f"{k}:{v}" for k, v in out["types"].items()))
    print("rels    " + ", ".join(f"{k}:{v}" for k, v in out["relations"].items()))
    if orphans:
        print(f"\n{len(orphans)} unconnected node(s) — an unlinked node is a note, "
              f"not knowledge: {', '.join(orphans[:8])}")
    if auto:
        print(f"{len(auto)} node(s) were auto-created by `link` and still have no "
              f"type: {', '.join(auto[:8])}")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="kg", description=__doc__.split("\n")[0])
    p.add_argument("--store", default=DEFAULT_STORE)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("add")
    s.add_argument("--id", required=True)
    s.add_argument("--type")
    s.add_argument("--name")
    s.add_argument("--attr", action="append")
    s.add_argument("--note")
    s.set_defaults(fn=cmd_add)

    s = sub.add_parser("link")
    s.add_argument("--from", required=True)
    s.add_argument("--to", required=True)
    s.add_argument("--rel", required=True)
    s.add_argument("--weight", type=float, default=1.0)
    s.add_argument("--note")
    s.add_argument("--allow-self", action="store_true")
    s.set_defaults(fn=cmd_link)

    s = sub.add_parser("rm")
    s.add_argument("--id", required=True)
    s.set_defaults(fn=cmd_rm)

    s = sub.add_parser("query")
    s.add_argument("--type")
    s.add_argument("--text")
    s.add_argument("--attr", action="append")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_query)

    s = sub.add_parser("neighbors")
    s.add_argument("--id", required=True)
    s.add_argument("--depth", type=int, default=1)
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_neighbors)

    s = sub.add_parser("path")
    s.add_argument("--from", required=True)
    s.add_argument("--to", required=True)
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_path)

    s = sub.add_parser("central")
    s.add_argument("--top", type=int, default=15)
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_central)

    s = sub.add_parser("clusters")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_clusters)

    s = sub.add_parser("mermaid")
    s.add_argument("--focus")
    s.add_argument("--depth", type=int, default=2)
    s.set_defaults(fn=cmd_mermaid)

    s = sub.add_parser("stats")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_stats)

    a = p.parse_args(argv)
    try:
        return a.fn(a)
    except (KGError, OSError) as e:
        print(f"kg: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
