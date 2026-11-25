# RQ4 v2 Source Audit

## Scope and verdict

This audit covers the existing v1/v2 source and saved artifacts only. No
training, baseline rerun, selector rerun, or output regeneration was performed
for this audit.

**Overall: QUALIFY — retrospective information-restoration experiment only.**
The saved v2 predictions reconcile to 295 unique reports, 58 projects, five
project-separated folds, and 16 conditions. V2 does not use a supervised
selector on held-out unit text or test labels. However, units are synthetically
withheld from an archived report; eligibility, field type, and character
length come from that complete report. This is metadata-visible retrospective
masking, not a demonstrated real-time acquisition interface. The old v1
targeted selector did inspect held-out candidate text and is invalid for
acquisition-policy claims.

The result remains subject to edited-description and source-overlap limitations. See the exact evidence and consequences below.

## Checks

| Check | Verdict | Source evidence and saved-output verification | Consequence |
|---|---|---|---|
| Cohort / project folds | **PASS** | `src/rq4_v2/baselines.py`, `main`: lines 54–64 form the no-comments eligible cohort and five `StratifiedGroupKFold` splits. `results/rq4/v2/fold_map.csv` exactly matches saved prediction URL/project/fold rows: 295 unique reports, 58 projects, five folds, and no project split across folds. | Report the evaluated cohort as 295 reports from 58 projects, not the full gold set. |
| Comments in primary v2 conditions | **PASS, with inventory qualification** | `src/rq4_v2/baselines.py`, `robust_units`: lines 21–26 removes `comments_model`; `robust_remove`: lines 29–38 constructs the visible-withheld input from title/description and removes only robust units. Candidate text and every condition are built from `robust_units` in `main`, lines 77–128. Saved primary cohort contains zero comments candidates. | Comments are excluded from v2 inference and conditions. The broad `results/rq4/v2/unit_audit.csv` and the manifest’s original-v1 inventory intentionally retain comment rows; they are not the v2 candidate set. |
| Hidden-unit selector — v1 | **FAIL (historical method)** | `src/rq4_reveal.py`, `targeted_unit`: lines 49–67 fit a text classifier on training candidate text/labels, then pass held-out candidate text to `decision_function` (line 64). `main` invokes it for each test report at lines 99–103. | v1 targeted results are archive/debug evidence only; do not claim a valid acquisition policy. |
| Hidden-unit selector — v2 | **QUALIFY** | `src/rq4_v2/baselines.py`, lines 77–128 selects with random choice (B1), unit character lengths (B2/B3), source-field type and training-unit counts (B3/B4). No candidate text, embedding, test label, correctness, or restored margin is used to rank v2 test candidates. Unit existence/type/length nevertheless derive from the complete archived report; the simulated requester is given this metadata before selection. | Call v2 retrospective, metadata-visible text restoration. Do not describe the selectors as deployable policies or as evidence for an interactive clarification system. |
| B2 unit selection and B5 equivalence | **PASS by source construction; output trace qualified** | `src/rq4_v2/baselines.py`, line 86 sets `length_id` to the shortest eligible unit. Lines 117 and 123 both restore `available[length_id]` for B2 and B5. Saved prediction output confirms identical predictions for all 295 URLs. `control_match_audit.csv` stores B2 unit ID/length but no separate B5 unit ID or per-condition input hash. | B2 is a **shortest-unit** control, not a general closest-length match. B5 is not a reproduction of the v1 selector; exclude it from valid policy comparisons. Its same input follows from source construction, while per-row B5 input hashes were not archived. |
| B3 distinct same-type match | **QUALIFY** | `src/rq4_v2/baselines.py`, lines 90–99 excludes `length_target_id`, restricts to the same `unit_type`, and chooses the available candidate with nearest character length to B2’s shortest unit. Lines 118–121 use B0 if no match. Saved `control_match_audit.csv`: 252/295 match; all 252 matched IDs are description paragraphs; 43 fall back to B0 and their B3 predictions equal B0. Absolute character delta: median 30.5, IQR 10.0–80.75, maximum 1,912. | Describe B3 as a **same-type / nearest-available-length description control when matchable**, with 43 no-reveal fallbacks. It is not uniformly length-matched. |
| B4 train-derived type preference | **PASS for label separation; QUALIFY for metadata realism** | `src/rq4_v2/baselines.py`, lines 68–76 derives the preferred field type from outer-training unit counts only; lines 101–108 applies the type to held-out candidates with a deterministic fallback. | Not a label-aware test selector. Its type/count metadata still comes from retrospective unit extraction. |
| Identical fold classifiers | **PASS** | `src/rq4_v2/baselines.py`, lines 64–67 fits one classifier per outer fold on `withheld_train` and training labels. Lines 116–138 create each condition and call `model.predict` without refitting. Each saved row carries `model_id=linear_svc_<fold>` (line 136); grouping saved output by URL yields exactly one project, fold, label, and model ID across conditions. | State explicitly that each fold model was trained on withheld-text training reports and reused across B0, B1, B2, B3, B4, B5, and REF. |
| Test labels in action selection | **PASS for v2 action rules** | V2 action construction at `src/rq4_v2/baselines.py`, lines 68–128 uses unit metadata, seeded random selection, or training type counts; held-out `root_cause` is used as the prediction record at line 137 and is not an action-selection argument. It is used in training labels only for outer-training rows at line 67. | The label is retained for evaluation; no test-label-conditioned v2 unit choice was found. |
| Code/stack provenance and overlap | **QUALIFY** | `src/clean.py`, `clean_text`: lines 39–47 extracts stack/exception and code/indented blocks from the description; lines 56–58 joins extracted text. `src/build_processed.py`, lines 84–85 renames those derived fields to `code_text` and `stack_text`. V2 `unit_entries` adds description paragraphs plus these excerpts (`src/rq4_v2/audit.py`, lines 20–31); `clean_overlap_flags`, lines 43–49 flags substring containment. For the 295-report no-comments cohort, the audit inventory has 2,105 units; 368 units are flagged across 146 reports. The flags include 292 description, 33 code, and 43 stack unit rows. Direct substring checks found 94 code and 63 stack unit strings that are not exact substrings of the raw description; `unit_entries` stores offset 0 when `.find` fails, so those offsets are not reliable source locations. An exact unit-string removal check found no candidate unit still present in the constructed withheld text. | Code/stack are excerpts from the same archived description, not independent evidence sources. Overlap flags indicate containment, not 368 proven independent passages. Their exact offsets are not fully reconstructed. The descriptions may have been edited after filing. |
| Comment timestamps | **QUALIFY; excluded from v2 inference** | `src/build_processed.py`, `prefix_comments`: lines 35–45 parses comment time and retains comments before `fix_authored`, falling back to `closed`; lines 54–55 orders retained comments. `src/finalize_gold.py`, lines 19–32 applies fix-revealing phrase masking to the comment field. These cutoffs do not prove an exact filing-time snapshot. | No comments are used in primary v2 inference; do not generalize this cutoff to filing-time provenance. |
| Audit table comment rows | **QUALIFY** | `src/rq4_v2/audit.py`, lines 34–39 includes comments when `include_comments=True`; `main`, lines 59–76 writes that broader audit table, while lines 88–90 separately builds the robust no-comments manifest. The saved broad unit audit includes 187 `comments_model` rows overall. | Keep the distinction visible: `unit_audit.csv` is a broader provenance inventory; the v2 inference candidate list is the robust no-comments subset. |
| Original v1/v2 artifacts | **PASS for non-overwrite** | Archived v1 outputs remain at `results/rq4/`; v2 files remain at `results/rq4/v2/`. Their SHA-256 values and producing scripts/commands are listed in the [RQ4_ARTIFACT_REGISTER.md](../rq4/RQ4_ARTIFACT_REGISTER.md). | Preserve both directories as archival. Do not use the v1 targeted score as evidence of policy benefit. |

## B3 and B2/B5 verification

The saved outputs establish:

- B3 matchable: 252; no-match fallback: 43.
- Every successful B3 match is a `description_p*` unit. The code/stack fields
  each have only one candidate ID per report, so they cannot supply a distinct
  same-type alternative to themselves.
- The 43 fallback B3 predictions equal B0 predictions exactly.
- The B3-minus-B0 correctness changes are 25 beneficial, 21 harmful, and 249
  unchanged.
- B2 and B5 predictions are identical for 295/295 URLs. The source constructs
  them from the exact same `length_id`; the output does not serialize B5’s
  unit ID or a condition-specific text hash.

## Final status and minimal blockers

**QUALIFY — source audit supports a retrospective information-restoration
comparison only.**

1. Candidate eligibility, type, and length are available because the complete
   archived report is being synthetically masked; their realistic availability
   to an actual requester is unestablished.
2. The v1 targeted selector reads held-out candidate text and is invalid as a
   policy. V2 B5 duplicates B2 and must not be presented as a faithful v1
   selector comparison.
3. B3 is a description-only same-type match for 252 reports, with 43 B0
   fallbacks and substantial variation in length difference.
4. The broad unit audit retains comment rows and code/stack excerpts can
   overlap with description passages; comments must remain excluded from
   primary inference and overlap must not be described as independent evidence.
5. Archived description text is not verified as an exact filing-time snapshot.

No experiment or selector was rerun to prepare this audit. Do not proceed to
reporting/cleanup phases until the user approves this audit, as requested.
