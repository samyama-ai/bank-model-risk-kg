"""GraphRAG over regulation — explainable, source-traced governance Q&A.

A natural-language governance question goes in; the answer comes back grounded in
(1) the most semantically relevant regulatory clauses (vector retrieval over
RegulatoryRequirement.text) and (2) the graph facts attached to those clauses —
which models they govern, which controls satisfy them, and which models carry open
findings under them. The "citation" is the retrieved clause + the graph traversal:
deterministic and replayable, the opposite of a free-text LLM guess.

Usage:
    python -m etl.graphrag "How must we independently validate models?"
    python -m etl.graphrag "transparency and human oversight of AI systems" --k 3
"""
from __future__ import annotations

import argparse

from rich.console import Console

from etl.embed import embed_query
from etl.sg_client import SamyamaClient

console = Console()


def _scalar_rows(client, cypher):
    return client.query(cypher).records


def answer(client: SamyamaClient, question: str, k: int = 3) -> None:
    qv = embed_query(question)
    hits = client.vector_search("RegulatoryRequirement", "embedding", qv, k=k)
    if not hits:
        console.print("[red]No regulatory clauses indexed — run the loader with embeddings first.[/red]")
        return

    console.print(f"\n[bold]Q:[/bold] {question}\n")
    console.print(f"[dim]Retrieved the {len(hits)} most relevant regulatory clauses "
                  f"(cosine similarity over clause text), then grounded each in the graph:[/dim]\n")

    for h in hits:
        # /api/vector-search returns the internal node id; after a snapshot import
        # the inline properties come back empty (columnar storage), so resolve the
        # clause's properties by id() via Cypher — robust pre- and post-import.
        nid = h["node"]["id"]
        meta = client.query(
            f"MATCH (r:RegulatoryRequirement) WHERE id(r) = {nid} "
            f"RETURN r.id, r.framework, r.clause, r.title, r.text").records
        if not meta:
            continue
        rid, fw, clause, title, text = meta[0]
        props = {"id": rid, "framework": fw, "clause": clause, "title": title, "text": text or ""}
        score = h.get("score", 0.0)
        console.print(f"[bold cyan]{fw} {clause}[/bold cyan] — {title}  "
                      f"[dim](similarity {score:.2f})[/dim]")
        console.print(f"   [italic]{props.get('text','')[:200]}…[/italic]")

        gov = _scalar_rows(client,
            f'MATCH (m:Model)-[:GOVERNED_BY]->(r:RegulatoryRequirement) WHERE r.id = "{rid}" '
            f'RETURN count(DISTINCT m)')
        n_models = gov[0][0] if gov else 0

        ctrls = _scalar_rows(client,
            f'MATCH (c:Control)-[:SATISFIES]->(r:RegulatoryRequirement) WHERE r.id = "{rid}" '
            f'RETURN c.name AS name, c.status AS status ORDER BY name')

        gaps = _scalar_rows(client,
            f'MATCH (m:Model)-[:GOVERNED_BY]->(r:RegulatoryRequirement) WHERE r.id = "{rid}" '
            f'MATCH (m)-[:VALIDATED_BY]->(:Validation)-[:RAISED]->(f:ValidationFinding) '
            f'WHERE f.status = "Open" OR f.status = "Overdue" '
            f'RETURN m.name AS model, count(f) AS open ORDER BY open DESC LIMIT 3')

        console.print(f"   [green]governs[/green] {n_models} models   "
                      f"[green]satisfied by controls:[/green] "
                      f"{', '.join(f'{n} ({s})' for n, s in ctrls) or '—'}")
        if gaps:
            g = "; ".join(f"{m} ({o} open)" for m, o in gaps)
            console.print(f"   [yellow]models with open/overdue findings under it:[/yellow] {g}")
        console.print()

    console.print("[dim]Every line above is traceable: the clause came from vector retrieval; "
                  "the counts came from graph traversals an auditor can re-run.[/dim]\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="GraphRAG over the regulation corpus")
    ap.add_argument("question", help="A governance question in natural language")
    ap.add_argument("--url", default="http://127.0.0.1:8080")
    ap.add_argument("--graph", default="bank")
    ap.add_argument("--k", type=int, default=3, help="Number of clauses to retrieve")
    args = ap.parse_args()
    answer(SamyamaClient(args.url, args.graph), args.question, k=args.k)
