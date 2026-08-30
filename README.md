# Bank Model-Risk Knowledge Graph

**520 nodes. ~2.4K edges. A synthetic bank's entire model-risk inventory as a graph — models, the data and assumptions behind them, their validations and findings, the regulations that govern them, and the submissions and decisions they drive.**

> Part of the **Samyama** ecosystem — loaded into and queried via the graph engine at [samyama-ai/samyama-graph](https://github.com/samyama-ai/samyama-graph).
> This repo holds the generator, loader and governance queries for the KG.

<a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache_2.0-blue" alt="License"></a>
<a href="https://huggingface.co/datasets/VaidhyaMegha/bank-model-risk-kg"><img src="https://img.shields.io/badge/%F0%9F%A4%97%20dataset-VaidhyaMegha%2Fbank--model--risk--kg-yellow" alt="HuggingFace dataset"></a>

**The graph is published as a dataset** — you do not have to run the generator:
**[huggingface.co/datasets/VaidhyaMegha/bank-model-risk-kg](https://huggingface.co/datasets/VaidhyaMegha/bank-model-risk-kg)**
(`v1.0`). All 520 nodes and 2,391 edges as node/edge CSVs, plus `bank-model-risk.sgsnap`.

```python
from datasets import load_dataset
models = load_dataset("VaidhyaMegha/bank-model-risk-kg", "model", revision="v1.0")
```

> Everything is published — nothing is held back. The data is **entirely synthetic** and
> Apache-2.0, so there is no upstream source, no third-party terms and nothing to redact.
> The dataset was produced by running the generator and loader in this repo against an empty
> engine; the result matched the committed snapshot exactly, confirming the `SEED = 42`
> reproducibility claim.

---

Model risk is a graph problem. SR 11-7, Basel, IFRS 9, ECB TRIM and the EU AI Act all
demand the same thing: trace a model's full lineage — data → assumptions → validation →
regulation → the submissions and decisions it drives — and explain *why*. Tables and
documents don't make that a first-class, auditable query. A graph does.

So we built a synthetic-but-realistic model-risk inventory and asked:

> *"If the Core Banking Ledger changes, which regulatory submissions are exposed — and through how many models?"*

```cypher
MATCH (ds:DataSource)<-[:DEPENDS_ON]-(m:Model)-[:FEEDS]->(s:Submission)
WHERE ds.name = "Core Banking Ledger"
RETURN s.name AS submission, count(DISTINCT m) AS models_affected
ORDER BY models_affected DESC
```

| submission | models_affected |
|------------|-----------------|
| ICAAP 2026 | 20 |
| DFAST 2026 | 13 |
| Pillar 3 Disclosure 2026 | 13 |
| CCAR 2026 | 7 |
| IFRS9 ECL Q2 2026 | 5 |
| AML SAR Program | 3 |

The quarter-long change-impact exercise becomes one query. **[See all 8 governance queries →](queries/governance-queries.cypher)**

> ⚠️ **Synthetic data.** Everything is generated from a fixed seed in `etl/generate.py` —
> no real institution, no PII, no proprietary model. It is a *demonstration of the engine
> and the schema*, not a deployed bank system.

---

## Schema

**12 node labels** — Model (80), Validation (136), ValidationFinding (173), Person (28),
Feature (24), RegulatoryRequirement (16), DataSource (15), Assumption (12), Control (12),
Decision (10), BusinessUnit (8), Submission (6)

**17 edge types** — OWNED_BY, DEVELOPED_BY, BELONGS_TO, MEMBER_OF, DEPENDS_ON,
USES_FEATURE, DERIVED_FROM, MAKES_ASSUMPTION, GOVERNED_BY, SATISFIES, CONTROLLED_BY,
EVIDENCES, VALIDATED_BY, PERFORMED_BY, RAISED, FEEDS, USED_IN

Full details: **[docs/schema.md](docs/schema.md)**.

## Documentation

New here? Start with the guides:

| Guide | What it covers |
|-------|----------------|
| **[GETTING_STARTED.md](GETTING_STARTED.md)** | prerequisites (Python ≥ 3.10) · install · run the engine (Docker) · load the graph · first query · GraphRAG |
| **[docs/QUERYING.md](docs/QUERYING.md)** | ask questions via the **HTTP API**, the **Samyama CLI**, GraphRAG, or (optional) MCP |
| [docs/schema.md](docs/schema.md) | full node/edge schema |

## Quick Start

**Full walkthrough → [GETTING_STARTED.md](GETTING_STARTED.md).** Needs **Python ≥ 3.10** and **Docker**.

### Load from the committed snapshot (recommended)

```bash
pip install -r requirements.txt
docker run --rm -p 8080:8080 -p 6379:6379 public.ecr.aws/f9f6l5u4/samyama-graph:1.1.0

# create the tenant and import the committed snapshot (85 KB; includes the regulation HNSW index)
curl -X POST http://localhost:8080/api/tenants -H 'Content-Type: application/json' -d '{"id":"bank","name":"Bank Model-Risk KG"}'
curl -X POST http://localhost:8080/api/tenants/bank/snapshot/import -F "file=@data/bank-model-risk.sgsnap"
```

### Build from source (generate + load)

```bash
git clone https://github.com/samyama-ai/bank-model-risk-kg.git && cd bank-model-risk-kg
pip install -r requirements.txt          # or: pip install -e ".[dev]" for tests

curl -X POST http://localhost:8080/api/tenants -H 'Content-Type: application/json' -d '{"id":"bank","name":"Bank Model-Risk KG"}'
python -m etl.loader --url http://localhost:8080                                  # generate (fixed seed) + load → bank
python -m etl.loader --url http://localhost:8080 --export data/bank-model-risk.sgsnap
```

## Example governance queries

```cypher
-- Governance gaps on critical models: open High findings on Tier-1 production models
MATCH (m:Model)-[:VALIDATED_BY]->(:Validation)-[:RAISED]->(f:ValidationFinding)
WHERE m.tier = 1 AND m.status = "Production" AND f.severity = "High" AND f.status = "Open"
RETURN m.name, f.category, f.title

-- Model explainability: the features and source systems behind an AML model's decisions
MATCH (m:Model)-[:USES_FEATURE]->(f:Feature)-[:DERIVED_FROM]->(ds:DataSource)
WHERE m.category = "AML Transaction Monitoring"
RETURN m.name, collect(DISTINCT f.name) AS features, collect(DISTINCT ds.name) AS sources
```

All 8 ship in **[queries/governance-queries.cypher](queries/governance-queries.cypher)** and are
gated in CI-style validation (each must return rows).

## GraphRAG over regulation (explainable, source-traced Q&A)

Each `RegulatoryRequirement` carries its obligation text, embedded with
`all-MiniLM-L6-v2` (384-dim, via [fastembed](https://github.com/qdrant/fastembed) — no torch)
into a Samyama HNSW vector index. A natural-language governance question is embedded,
the most relevant clauses are retrieved by cosine similarity, and each is then
**grounded in the graph** — which models it governs, which controls satisfy it, which
models carry open findings under it. The answer is deterministic and citable: the
clause comes from vector retrieval, the counts from graph traversals an auditor can re-run.

```bash
# with a Samyama server running and the KG loaded (see below)
python -m etl.graphrag "How must we independently validate models and challenge them?"
```
```
SR 11-7 III — Independent model validation with effective challenge   (similarity 0.77)
   governs 53 models   satisfied by controls: Annual independent validation (Needs improvement), …
   models with open/overdue findings under it: LLM Adverse-Media Screening · CRE #42 (5 open); …
```

The loader builds this automatically: it creates the vector index, then embeds and
indexes every requirement (`python -m etl.loader … ` — pass `--no-embed` to skip).
The exported snapshot carries the HNSW index, so an importing server can vector-search
immediately. After a snapshot import, node properties are read back via Cypher by id
(columnar storage returns empty inline props on the search response) — handled in `etl/graphrag.py`.

## Tests

```bash
pytest          # structural + determinism invariants for the generator (no server needed)
```

## Known engine note

The loader does **not** issue `CREATE INDEX` hints. On the current engine build, an index
created on a label *before* its nodes are inserted causes equality lookups (`WHERE n.prop = …`
and inline `{prop: …}`) to route to an empty index scan and return zero rows. The KG is small
(~500 nodes), so label-scan + `WHERE` filter is correct and fast. (Tracked upstream.)

## Links

| | |
|---|---|
| Samyama Graph | [github.com/samyama-ai/samyama-graph](https://github.com/samyama-ai/samyama-graph) |
| The Book | [samyama-ai.github.io/samyama-graph-book](https://samyama-ai.github.io/samyama-graph-book/) |
| Contact | [samyama.dev/contact](https://samyama.dev/contact) |

## License

Apache 2.0. All data is synthetic and generated; it represents no real institution.
