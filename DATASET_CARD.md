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

## Freshness

**Refresh cadence:** none — this is a static, seeded synthetic generator
(`etl/generate.py`, `SEED = 42`), not a pull from a live upstream, so there is
nothing to refresh on a calendar. The graph is fully reproducible from the seed:
running the generator today produces byte-identical structure to running it on
2026-07-31. One caveat worth stating plainly: the 12 `RegulatoryRequirement` nodes
are short, hand-authored paraphrases of five real frameworks (SR 11-7, Basel III,
IFRS 9, ECB TRIM, EU AI Act) hardcoded as a fixed list in `etl/generate.py`. They are
not pulled from those regulators' own publications and will not reflect future
amendments to the real rules unless someone edits the generator by hand.

**Data as of:** the generator's logic (`etl/generate.py`) was last changed
2026-07-31 (`git log -1 --format=%ad -- etl/generate.py`); this dataset card was last
updated 2026-08-15 (`git log -1 --format=%ad -- DATASET_CARD.md`). Because output is
deterministic from `SEED = 42`, "data as of" for this repo means the date its
generation logic was last edited, not a fetch or snapshot date — there is no upstream
capture to date.

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

## Citation

Please cite this repository if you use it. See [`CITATION.cff`](CITATION.cff) for
machine-readable metadata (CFF 1.2.0).

```bibtex
@misc{bank_model_risk_kg_2026,
  title        = {Bank Model-Risk Knowledge Graph},
  author       = {Samyama},
  year         = {2026},
  howpublished = {\url{https://git.samyama.ai/Samyama.ai/bank-model-risk-kg}}
}
```

**No DOI.** This release has not been deposited to Zenodo, so there is no DOI to
cite. Getting one is open work — it requires a human to make the Zenodo deposit
(KG-06).
