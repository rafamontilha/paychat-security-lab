---
name: Red-team / break a defense
about: Report (or propose) a payload that defeats a defense layer
title: "[RED-TEAM] "
labels: red-team, needs-triage
---

## Target
- [ ] Variant A (Claude)
- [ ] Variant B (Llama 3.3 70B)
- [ ] Variant C (Guard → ReAct → Presidio pipeline)

## Category / scenario
<!-- e.g. pi_indirect / Scenario 3 side-channel exfiltration -->

## Success criterion you are claiming
<!-- Be explicit: real PII exfiltration? unauthorized action? bypass of BOTH input guard and output filter? -->

## Payload / steps to reproduce
<!-- The actual payload and the harness invocation (variant, category, payload). Follow the evidence schema. -->

## Result
<!-- What happened? Did it defeat the layer the threat model says it should not? -->

## Is this already covered by the threat model?
<!-- Check report/threat_model.md §6. New finding, or confirmation of an existing scenario? -->
- [ ] New — not in the threat model
- [ ] Extends an existing scenario
- [ ] Confirms existing coverage (defense held)
