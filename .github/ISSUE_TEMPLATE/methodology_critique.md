---
name: Methodology critique
about: Challenge a statistical or experimental-design choice
title: "[METHOD] "
labels: methodology, needs-triage
---

## Which claim or choice are you challenging?
<!-- Cite the report section (e.g. §6.5), the cell ID ({variant}_{category}), or the LIMITATIONS.md item. -->

## What is wrong with it?
<!-- Be specific. "The CI overlap test is too conservative for cell c_sensitive_disclosure" beats "the stats seem off". -->

## What is the correct treatment, in your view?
<!-- e.g. "Use Fisher's exact two-proportion test per cell; here is the recomputation for cell X." -->

## Evidence / recomputation
<!-- Point to the CSV row in report/security_audit_matrix.csv, or paste your computation. -->

## Does this change a conclusion?
- [ ] Yes — it flips a win/regression call
- [ ] Partially — it weakens a claim but doesn't flip it
- [ ] No — it's a rigor improvement only
