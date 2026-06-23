"""Bank Model-Risk KG loader.

Generates the synthetic model-risk inventory (etl/generate.py) and loads it into
a running Samyama server over HTTP as Cypher CREATE statements. Idempotent only
on a fresh/ephemeral graph — it does not de-duplicate against existing data.

Usage:
    # start a server first, e.g.:
    #   ./target/release/samyama --host 127.0.0.1 --port 6379
    python -m etl.loader --url http://127.0.0.1:8080
    python -m etl.loader --url http://127.0.0.1:8080 --export bank-model-risk.sgsnap
"""
from __future__ import annotations

import argparse
import time

from etl.generate import generate
from etl.sg_client import SamyamaClient

GRAPH = "default"
NODE_BATCH = 100
EDGE_BATCH = 100

# NOTE: we deliberately do NOT pre-create CREATE INDEX hints. On this engine build,
# an index created on a label *before* its nodes are inserted makes subsequent
# equality lookups (both `WHERE n.prop = ...` and inline `{prop: ...}`) route to an
# empty index scan and return zero rows. The KG is small (~500 nodes), so label-scan
# + WHERE filter is correct and fast. (See README "Known engine note".)


# --- Cypher helpers (string-keyed, id-matched) ---------------------------
def _escape(v) -> str:
    return str(v).replace("\\", " ").replace('"', "'").replace("\n", " ").replace("\r", "")


def _prop_str(props: dict) -> str:
    parts = []
    for k, v in props.items():
        if v is None:
            continue
        if isinstance(v, bool):
            parts.append(f"{k}: {str(v).lower()}")
        elif isinstance(v, (int, float)):
            parts.append(f"{k}: {v}")
        else:
            parts.append(f'{k}: "{_escape(v)}"')
    return "{" + ", ".join(parts) + "}"


def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def _load_nodes(client, nodes):
    for batch in _chunks(nodes, NODE_BATCH):
        parts = [f"(:{label} {_prop_str(props)})" for label, props in batch]
        client.query(f"CREATE {', '.join(parts)}", GRAPH)


def _load_edges(client, edges):
    for batch in _chunks(edges, EDGE_BATCH):
        var_map: dict[tuple, str] = {}
        match_parts, where_parts, create_parts = [], [], []
        for sl, sid, rel, tl, tid, props in batch:
            for label, _id in ((sl, sid), (tl, tid)):
                key = (label, _id)
                if key not in var_map:
                    v = f"n{len(var_map)}"
                    var_map[key] = v
                    match_parts.append(f"({v}:{label})")
                    where_parts.append(f'{v}.id = "{_id}"')
            sv, tv = var_map[(sl, sid)], var_map[(tl, tid)]
            pp = f" {_prop_str(props)}" if props else ""
            create_parts.append(f"({sv})-[:{rel}{pp}]->({tv})")
        q = (f"MATCH {', '.join(match_parts)} "
             f"WHERE {' AND '.join(where_parts)} "
             f"CREATE {', '.join(create_parts)}")
        client.query(q, GRAPH)


def _embed_regulations(client, nodes):
    """GraphRAG retrieval layer: embed each RegulatoryRequirement.text and index it.

    Order matters — create the vector index FIRST, then SET embeddings so they
    auto-index (an index created after insert does not backfill on this build).
    """
    from etl.embed import embed_texts, DIM
    regs = [(p["id"], p["text"]) for label, p in nodes
            if label == "RegulatoryRequirement" and p.get("text")]
    client.create_vector_index("RegulatoryRequirement", "embedding", DIM, "cosine")
    print(f"created vector index RegulatoryRequirement.embedding ({DIM}-dim, cosine)", flush=True)
    vecs = embed_texts([t for _, t in regs])
    for (rid, _), vec in zip(regs, vecs):
        lit = "[" + ", ".join(f"{x:.6f}" for x in vec) + "]"
        client.query(f'MATCH (r:RegulatoryRequirement) WHERE r.id = "{rid}" '
                     f"SET r.embedding = {lit}", GRAPH)
    print(f"embedded + indexed {len(regs)} regulatory requirements", flush=True)


def load(client: SamyamaClient, export: str | None = None, embed: bool = True) -> dict:
    nodes, edges = generate()
    print(f"generated {len(nodes)} nodes, {len(edges)} edges", flush=True)

    t0 = time.time()
    _load_nodes(client, nodes)
    print(f"loaded nodes in {time.time()-t0:.1f}s", flush=True)
    t1 = time.time()
    _load_edges(client, edges)
    print(f"loaded edges in {time.time()-t1:.1f}s", flush=True)

    if embed:
        try:
            _embed_regulations(client, nodes)
        except RuntimeError as e:
            print(f"WARNING: skipping embeddings — {e}", flush=True)

    n, e = client.node_count(), client.edge_count()
    print(f"server reports: {n} nodes, {e} edges", flush=True)

    if export:
        client.export_snapshot(export)
        print(f"exported snapshot -> {export}", flush=True)
    return {"nodes": n, "edges": e}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Load the Bank Model-Risk KG into Samyama")
    ap.add_argument("--url", default="http://127.0.0.1:8080", help="Samyama HTTP base URL")
    ap.add_argument("--graph", default="default")
    ap.add_argument("--export", default=None, help="Path to write a .sgsnap snapshot after load")
    ap.add_argument("--no-embed", action="store_true", help="Skip the GraphRAG embedding step")
    args = ap.parse_args()
    client = SamyamaClient(args.url, args.graph)
    load(client, export=args.export, embed=not args.no_embed)
