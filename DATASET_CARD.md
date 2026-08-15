---
license: apache-2.0
pretty_name: Bank Model-Risk Knowledge Graph
tags:
  - knowledge-graph
  - samyama
  - property-graph
  - finance
  - risk
language:
  - en
size_categories:
  - n<1K
---

# Dataset Card for `bank-model-risk-kg`

**520 nodes. ~2.4K edges. A synthetic bank's entire model-risk inventory as a graph — models, the data and assumptions behind them, their validations and findings, the regulations that govern them, and the submissions and decisions they drive.**

> Part of the **Samyama** ecosystem. This card describes the dataset; the repository
> holds the loader and source-data specifics.

## Structure

**12 node labels** — Model (80), Validation (136), ValidationFinding (173), Person (28),
Feature (24), RegulatoryRequirement (16), DataSource (15), Assumption (12), Control (12),
Decision (10), BusinessUnit (8), Submission (6)

**17 edge types** — OWNED_BY, DEVELOPED_BY, BELONGS_TO, MEMBER_OF, DEPENDS_ON,
USES_FEATURE, DERIVED_FROM, MAKES_ASSUMPTION, GOVERNED_BY, SATISFIES, CONTROLLED_BY,
EVIDENCES, VALIDATED_BY, PERFORMED_BY, RAISED, FEEDS, USED_IN

Full details: **[docs/schema.md](docs/schema.md)**.

## Provenance and licence

Apache 2.0. All data is synthetic and generated; it represents no real institution.

## Reproducing

The loader in this repository rebuilds the graph from the upstream source. See the
README's Quick Start for the snapshot download and the from-source build.

## Known limitations

- Counts here are those stated by the repository README at the time this card was
  written; they are not re-measured by the card.
- Where a field above says *not recorded*, that is a gap in this repository rather
  than a property of the data.

## Links

| | |
|---|---|
| Samyama Graph | [github.com/samyama-ai/samyama-graph](https://github.com/samyama-ai/samyama-graph) |
| The Book | [samyama-ai.github.io/samyama-graph-book](https://samyama-ai.github.io/samyama-graph-book/) |
| Contact | [samyama.dev/contact](https://samyama.dev/contact) |
