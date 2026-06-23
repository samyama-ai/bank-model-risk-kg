"""Structural + determinism tests for the synthetic generator.

These run with no server — they assert the generated graph has the shape the
showcase governance queries depend on, so a green test suite guarantees the DoD
gate (every query returns rows) will pass after loading.
"""
from collections import defaultdict

from etl.generate import generate


def _build():
    nodes, edges = generate()
    by_id = {props["id"]: (label, props) for label, props in nodes}
    out = defaultdict(list)  # (src_id, rel) -> [tgt_id]
    for sl, sid, rel, tl, tid, props in edges:
        out[(sid, rel)].append(tid)
    return nodes, edges, by_id, out


def test_deterministic():
    a_n, a_e = generate()
    b_n, b_e = generate()
    assert a_n == b_n and a_e == b_e


def test_unique_ids_and_valid_edges():
    nodes, edges, by_id, _ = _build()
    ids = [p["id"] for _, p in nodes]
    assert len(ids) == len(set(ids)), "node ids must be unique"
    for sl, sid, rel, tl, tid, _ in edges:
        assert sid in by_id and tid in by_id, f"dangling edge {sid}-{rel}->{tid}"
        assert by_id[sid][0] == sl and by_id[tid][0] == tl


def test_model_invariants():
    nodes, *_ = _build()
    models = [p for l, p in nodes if l == "Model"]
    assert len(models) >= 50
    for m in models:
        assert m["tier"] in (1, 2, 3)
        assert m["status"] in ("Production", "Development", "Retired")
        assert m["regulatory_use"] in (0, 1)


def test_anchor_entities_exist():
    nodes, *_ = _build()
    ds = {p["name"] for l, p in nodes if l == "DataSource"}
    subs = {p["name"] for l, p in nodes if l == "Submission"}
    fws = {p["framework"] for l, p in nodes if l == "RegulatoryRequirement"}
    cats = {p["category"] for l, p in nodes if l == "Model"}
    assert "Core Banking Ledger" in ds
    assert "CCAR 2026" in subs
    assert "SR 11-7" in fws
    assert "AML Transaction Monitoring" in cats


def test_blast_radius_connectivity():
    """Some model depends on Core Banking Ledger AND feeds a submission (Q1)."""
    nodes, edges, by_id, out = _build()
    ledger_id = next(p["id"] for l, p in nodes if l == "DataSource"
                     and p["name"] == "Core Banking Ledger")
    sub_ids = {p["id"] for l, p in nodes if l == "Submission"}
    hits = 0
    for l, p in nodes:
        if l != "Model":
            continue
        mid = p["id"]
        deps = out.get((mid, "DEPENDS_ON"), [])
        feeds = out.get((mid, "FEEDS"), [])
        if ledger_id in deps and any(t in sub_ids for t in feeds):
            hits += 1
    assert hits >= 1


def test_ccar_feed_chain():
    """At least one model reaches CCAR 2026 within 3 FEEDS hops (Q2)."""
    nodes, edges, by_id, out = _build()
    ccar = next(p["id"] for l, p in nodes if l == "Submission" and p["name"] == "CCAR 2026")

    def reaches(start, target, depth):
        if depth == 0:
            return False
        for t in out.get((start, "FEEDS"), []):
            if t == target or reaches(t, target, depth - 1):
                return True
        return False

    model_ids = [p["id"] for l, p in nodes if l == "Model"]
    assert any(reaches(m, ccar, 3) for m in model_ids)


def test_open_high_finding_on_tier1_production():
    """At least one Tier-1 production model has an Open High finding (Q3)."""
    nodes, edges, by_id, out = _build()
    found = False
    for l, p in nodes:
        if l == "Model" and p["tier"] == 1 and p["status"] == "Production":
            for vid in out.get((p["id"], "VALIDATED_BY"), []):
                for fid in out.get((vid, "RAISED"), []):
                    f = by_id[fid][1]
                    if f["severity"] == "High" and f["status"] == "Open":
                        found = True
    assert found
