# Contributing to PayChat Security Lab

Thanks for considering a contribution. This is a finished academic capstone (a red-team security
evaluation of three LLM architectures for a conversational payments marketplace), released for
**critique and independent validation** — not as a definitive audit. Adversarial, well-reasoned
feedback is the most valuable thing you can give it.

> The full report is in `report/SECURITY_AUDIT.md` (Portuguese). Known weaknesses we already invite
> challenge on are listed in `LIMITATIONS.md`. The structured evaluation playbook is in
> `docs/EVALUATION.md`.

## Ways to contribute

We use three issue templates, one per kind of contribution:

1. **Methodology critique** — you think a statistical or experimental-design choice is wrong
   (significance testing, sample size, the priority score, the central "non-commutativity" claim).
   Start here if you have a stats or research-methods background. See `LIMITATIONS.md` items 1–7.

2. **Red-team / break a defense** — you found (or want to attempt) a payload that defeats Variant C's
   `Llama Guard → ReAct → Presidio` pipeline in a way the threat model does not already cover. The
   highest-value target is the **Scenario 3 side-channel exfiltration** (`LIMITATIONS.md` item 3):
   turn the single constructed proof into a measured success rate over a payload battery.

3. **Reproduction report** — you re-ran the 3×7 matrix (or the no-API analysis chain) from a clean
   clone and want to report per-cell deltas. Note: for black-box providers, success means **"within
   the 95% CI"**, not identical numbers (`LIMITATIONS.md` item 8).

## Ground rules

- **Be specific and falsifiable.** "This seems off" is hard to act on; "cell `b_pi_direct`'s CI is
  computed wrong, here's the recomputation" is gold.
- **Cite evidence.** Point to the cell ID (`{variant}_{category}`), the CSV row, or the payload.
- **Reproduce the no-API analysis chain first** when in doubt: re-run `notebooks/00_audit_report.ipynb`
  over the committed CSVs (`report/security_audit_matrix.csv`, `report/audit_counts.csv`) — this
  regenerates every figure/table without spending tokens. (Raw per-attack evidence under `evidence/`
  is gitignored; only the aggregated CSVs are public.)
- **Scope.** Training-time attacks (backdoor, poisoning), multimodal attacks, and production-grade
  marketplace concerns are explicitly out of scope (see report §2.3). Contributions extending these
  are welcome but should be labeled as scope extensions, not gaps.

## Evidence schema

New attack payloads added to `red_team/harness.py` must follow the existing evidence record schema
(`{ id, timestamp, variant, category, technique, payload, response, success_flag, trace }`) so that
the notebook-driven analysis chain can consume them. PRs that break the schema will be asked to conform.

## Recognition

Substantive, well-founded contributions that refute or strengthen a claim will be credited in the repo.
There is no CLA. The code is MIT; the report and derived assets are CC BY 4.0 (`report/LICENSE`).

## Where to discuss

Open an issue with the right template, or use GitHub Discussions for open-ended methodology questions.
For the broader LLM-security community, this project is also brought to the OWASP GenAI Security Project
(Red Teaming initiative) and the usual venues (r/netsec, Show HN).
