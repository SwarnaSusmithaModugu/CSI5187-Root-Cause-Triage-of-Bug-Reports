# RQ4 v2 Interpretation

## Phase 1 validity

The v1 targeted selector was retained as an invalid historical reference.
It read withheld candidate text and is not interpreted as a learnable policy.
Comments were excluded from the primary robust v2 cohort because filing-time
provenance cannot be established.

## Phase 2 baselines

- Robust cohort: 295 reports, 58 projects
- Same-type matchable subset: 252/295
- B0 withheld macro-F1: 0.598062
- B3 same-type control macro-F1: 0.607874
- Full-unit reference macro-F1: 0.627530
- Random reveal mean macro-F1: 0.609321 (range 0.591361-0.630819)
- Paired B3-vs-B0 changes: {'unchanged': 249, 'beneficial': 25, 'harmful': 21}
- Macro-F1 difference 95% project-bootstrap CI: [-0.036973, 0.049015]
- Accuracy difference 95% project-bootstrap CI: [-0.032111, 0.053628]

The baseline interval includes zero. The strict same-type control does not
demonstrate a reliable improvement over withheld prediction, and the full-unit
reference is only a retrospective information diagnostic, not a ceiling for
deployment.

## Phase 3 gate

**STOP: C-VOI NOT IMPLEMENTED.**

The mandatory gate requires a strong, stable same-type baseline result.
The interval includes zero and the v1 hidden-content selector is invalid, so
there is no justified basis for a learned selector.

This is a retrospective text-restoration study, not an active clarification
agent or external validation.
