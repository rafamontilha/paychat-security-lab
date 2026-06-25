---
name: Reproduction report
about: Report results of reproducing the matrix or the analysis chain
title: "[REPRO] "
labels: reproducibility, needs-triage
---

## What did you reproduce?
- [ ] Full 3×7 matrix from clean clone (with API keys)
- [ ] No-API analysis chain (notebook 00 over committed CSVs: report/security_audit_matrix.csv + report/audit_counts.csv)
- [ ] A single cell / category

## Environment
<!-- OS, Docker Compose version, and — critically — the exact provider model strings and run date. -->
- Anthropic model string + date:
- Together model string + date:

## Per-cell deltas
<!-- For each cell you re-ran: baseline ASR, your ASR, and whether your result falls WITHIN the published 95% CI. -->
| cell | published ASR | your ASR | within CI? |
|---|---|---|---|

## Coverage check
- [ ] `check_audit_coverage.py` reports 21/21
- [ ] All figures regenerated from CSVs

## Notes
<!-- Remember: for black-box providers, success is "within CI", not identical numbers (LIMITATIONS.md item 8). -->
