# Split SDD Package

This folder contains the split version of the original Scopus analytics SDD.

The package is divided into three execution-oriented requirement files:

1. `01-analytics-foundation.md`
2. `02-network-analytics.md`
3. `03-reporting-and-interactive-delivery.md`

## Purpose

The split is intentional.

The original SDD combined:

- deterministic bibliometric parsing
- graph/network computation
- reporting and presentation UX

Those concerns have different dependencies, test strategies, failure modes, and delivery contracts.

## Execution Rule

Implement in order.

- `01-analytics-foundation.md` is the prerequisite for the others.
- `02-network-analytics.md` depends on outputs from `01`.
- `03-reporting-and-interactive-delivery.md` depends on outputs from `01` and may optionally consume outputs from `02`.

## Boundary Rule

These documents define machine-oriented implementation contracts.

They are intended to be:

- explicit
- testable
- bounded
- reproducible

They are not brainstorming notes.

## Canonical Source

The original source draft remains:

- [.requirements/SDD-requirements.md](/d:/Development/Repositories/AI-models/Abstract-clasif/Abstracts_Classification_IA/.requirements/SDD-requirements.md)

The review that motivated the split remains:

- [.requirements/SDD-review-report.md](/d:/Development/Repositories/AI-models/Abstract-clasif/Abstracts_Classification_IA/.requirements/SDD-review-report.md)
