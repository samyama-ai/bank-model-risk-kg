# Getting Started — Bank Model-Risk Knowledge Graph

From `git clone` to your first answer. The snapshot is **committed in the repo** (`data/bank-model-risk.sgsnap`),
so the fastest path needs no download or generation.

---

## 1. Prerequisites

- **Python ≥ 3.10**
- **git**
- **Docker** — to run the Samyama engine (HTTP `:8080`, RESP `:6379`).

This repo talks to the engine over HTTP through its own `etl/sg_client.py`; it does **not** need the
`samyama` SDK. The only third-party deps are `requests`, `rich`, and `fastembed` (ONNX embeddings, no torch).

## 2. Install

```bash
git clone https://github.com/samyama-ai/bank-model-risk-kg.git
cd bank-model-risk-kg
python3 -m venv .venv && source .venv/bin/activate     # Python >= 3.10
pip install -r requirements.txt
```

## 3. Run the engine (Docker)

```bash
docker run --rm -p 8080:8080 -p 6379:6379 public.ecr.aws/f9f6l5u4/samyama-graph:1.1.0
```

## 4. Load the graph — into the `bank` tenant

### Option A — import the committed snapshot (recommended, ~seconds)
```bash
curl -X POST http://localhost:8080/api/tenants -H 'Content-Type: application/json' \
  -d '{"id":"bank","name":"Bank Model-Risk KG"}'
curl -X POST http://localhost:8080/api/tenants/bank/snapshot/import -F "file=@data/bank-model-risk.sgsnap"
```
*(85 KB; includes the regulation HNSW vector index, so GraphRAG works right after import.)*

### Option B — generate + load from source
```bash
curl -X POST http://localhost:8080/api/tenants -H 'Content-Type: application/json' \
  -d '{"id":"bank","name":"Bank Model-Risk KG"}'
python -m etl.loader --url http://localhost:8080                                  # generate (fixed seed) + load → bank
python -m etl.loader --url http://localhost:8080 --export data/bank-model-risk.sgsnap   # ...and re-export the snapshot
```
*(The generator is deterministic — same seed, same graph. Pass `--no-embed` to skip the GraphRAG index.)*

## 5. Ask your first question

Change-impact — if the Core Banking Ledger changes, which submissions are exposed and through how many models:

```bash
curl -s -X POST http://localhost:8080/api/query -H 'Content-Type: application/json' -d '{
  "graph": "bank",
  "query": "MATCH (ds:DataSource)<-[:DEPENDS_ON]-(m:Model)-[:FEEDS]->(s:Submission) WHERE ds.name = \"Core Banking Ledger\" RETURN s.name AS submission, count(DISTINCT m) AS models ORDER BY models DESC LIMIT 5"
}'
# → ICAAP 2026 (20), DFAST 2026 (13), Pillar 3 Disclosure 2026 (13), CCAR 2026 (7), IFRS9 ECL Q2 2026 (5)
```

All 8 governance queries ship in **[queries/governance-queries.cypher](queries/governance-queries.cypher)**.

## 6. GraphRAG over regulation (explainable, source-traced Q&A)

```bash
python -m etl.graphrag "How must we independently validate models and challenge them?"   # --graph defaults to bank
```
Each `RegulatoryRequirement`'s obligation text is embedded (`all-MiniLM-L6-v2` via fastembed) into a Samyama
HNSW index; a question is embedded, the closest clauses retrieved, then **grounded in the graph** (which
models each governs, which controls satisfy it). Deterministic and citable. See the README for details.

## Next
- **[docs/QUERYING.md](docs/QUERYING.md)** — HTTP API, Samyama CLI, and (optional) MCP
- **[docs/schema.md](docs/schema.md)** — full node/edge schema
