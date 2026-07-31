# Querying the Bank Model-Risk KG

Ways to ask the graph questions, once it's loaded into the `bank` tenant on a running engine
(see [GETTING_STARTED.md](../GETTING_STARTED.md)). The HTTP and CLI examples below were run live and
return real results.

> **Note:** after a snapshot import, whole-node / `properties(n)` returns can come back empty (columnar
> storage), but **explicit property access works** (`m.name`, `f.severity`, `ds.name`). Write queries with
> named properties. The KG is small (~500 nodes), so label-scan + `WHERE` is fast.

---

## 1. HTTP API (`POST /api/query`)

Change-impact — which submissions depend on the Core Banking Ledger, and through how many models:

```bash
curl -s -X POST http://localhost:8080/api/query -H 'Content-Type: application/json' -d '{
  "graph": "bank",
  "query": "MATCH (ds:DataSource)<-[:DEPENDS_ON]-(m:Model)-[:FEEDS]->(s:Submission) WHERE ds.name = \"Core Banking Ledger\" RETURN s.name AS submission, count(DISTINCT m) AS models ORDER BY models DESC LIMIT 5"
}'
```
```json
{"columns":["submission","models"],
 "records":[["ICAAP 2026",20],["DFAST 2026",13],["Pillar 3 Disclosure 2026",13],["CCAR 2026",7],["IFRS9 ECL Q2 2026",5]]}
```

## 2. Samyama CLI (Redis wire protocol, `:6379`)

Governance gaps — models carrying the most open, High-severity validation findings:

```bash
redis-cli -p 6379 GRAPH.QUERY bank \
  "MATCH (m:Model)-[:VALIDATED_BY]->(:Validation)-[:RAISED]->(f:ValidationFinding) WHERE f.severity = 'High' AND f.status = 'Open' RETURN m.name, count(f) AS open_high ORDER BY open_high DESC LIMIT 3"
# 1) "Next-Best-Product · SME #63"        2
# 2) "Credit Scorecard · Credit Card #41" 2
# 3) "PD · Credit Card #54"               2
```

## 3. GraphRAG over regulation (natural language)

```bash
python -m etl.graphrag "How must we independently validate models and challenge them?"
```
Vector-retrieves the most relevant `RegulatoryRequirement` clauses and grounds each in the graph
(models governed, controls satisfying it, open findings under it). See the README.

## 4. Claude, over MCP (optional)

This repo ships no bespoke MCP server and doesn't depend on the `samyama` SDK. To expose the tenant over
MCP, install the SDK separately and use its generic server:

```bash
pip install samyama
claude mcp add bank -- samyama-mcp-serve --url http://localhost:8080 --graph bank
```

---

## More queries
All 8 governance queries: **[queries/governance-queries.cypher](../queries/governance-queries.cypher)**.
Full schema: **[docs/schema.md](schema.md)**.
