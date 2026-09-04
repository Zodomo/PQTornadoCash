# PQTC Next-Generation Research Package

This package is a research handoff for the PQ Tornado Classic project after the v0.3 engineering report.

## Files

- `PQTC_NEXT_GENERATION_RESEARCH_PLAN.md` — normative research directive, experiment definitions, measurement standards, gates, and final deliverables.
- `NEXT_GENERATION_RESEARCH_REPORT_TEMPLATE.md` — required structure for the report returned after the spikes.
- `benchmark-run.schema.json` — machine-readable schema for every benchmark run.
- `candidate-summary-template.csv` — one-row-per-candidate summary template.
- `security-terms-template.csv` — term-by-term security accounting template.
- `gas-results-template.csv` — complete transaction and scenario-gas template.

## Intended workflow

1. Freeze and reproduce v0.3.
2. Complete the research spikes in the plan, stopping candidates at their gates.
3. Preserve raw run records and generated artifacts.
4. Fill `NEXT_GENERATION_RESEARCH_REPORT_TEMPLATE.md`.
5. Return the report and evidence bundle for review before drafting a new engineering specification.

This package does not authorize deployment or a new custody build.
