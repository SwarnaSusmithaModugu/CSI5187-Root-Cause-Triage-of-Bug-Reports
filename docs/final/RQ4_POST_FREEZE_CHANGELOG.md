# RQ4 Post-Freeze Cleanup Changelog

The checksum paths below record the post-freeze reporting cleanup before the
later documentation-only reorganization. Frozen RQ4 result and source paths
were not moved.

## Baseline snapshot

- Branch: `rq3-structural-corrected`
- Revision: `dcf9a752116317161d90992046e8134d25c7877f`
- Baseline RQ4 finalizer: **PASS**; 16 conditions, 4,720 rows, 295 reports,
  58 projects, five folds, 252 B3 matches, 43 fallbacks, 28 registered hashes
  verified, no training.
- Baseline `python -m pytest -q tests`: **17 passed**.
- Baseline `git diff --check`: **clean**.
- The worktree already contained untracked RQ4 scripts, tests, and result
  artifacts, plus unrelated RQ2/RQ3 work. No branch switch, move, or archival
  input edit is part of this cleanup.
- Before-state primary table had six rows: the four full-cohort conditions
  plus two 252-report descriptive rows. This cleanup moves only those two
  descriptive rows into a separate supplementary table.

## Baseline document, script, test, and report SHA-256

These are exact pre-edit workspace bytes, captured after the baseline
finalizer and test run and before cleanup edits.

| Path | Bytes | Baseline SHA-256 |
|---|---:|---|
| `docs/rq4/RQ4_ARTIFACT_REGISTER.md` | 7608 | `7c3752a25cc26a612cb32c106f6351dabbf704504b2f3585449a44aedf1fdade` |
| `docs/rq4/RQ4_V2_SOURCE_AUDIT.md` | 10397 | `b846718f88ba87db84d1f0152733dee66b1fbb363971514cb409580b62de7e88` |
| `docs/rq4/FINAL_RQ4_DECISION.md` | 4677 | `8895a84d9ce504db4d6755e82f279e76111ae756d36f2cea8174ea9f26f4a9ca` |
| `docs/rq4/RQ4_README.md` | 2743 | `b0ab6a10b4acaa5b2e6c81bf1946e5bc9299c7330b17da898970da875e764ba5` |
| `docs/RQ4_FEASIBILITY.md` | 3017 | `9b9fa97f27f44adaed82c3883abf53226279ac1d2b65bb416578cf0a0e80de32` |
| `docs/DATA_NOTES.md` | 15897 | `667c91d4557eb5c7e183da4405e21f8f1d247b9c2d2c05d211e150227cfc0b52` |
| `README.md` | 4696 | `e870578972334f4caaa56c18c74539d572fdee1b4658cba8a608c170eb972786` |
| `scripts/rq4_finalize_report.py` | 26770 | `f7fd2868d4b6b20b8a18fc2009eb0d066665163ad65a9a8abd9d36dfdb7c167b` |
| `tests/test_rq4_finalize_report.py` | 4915 | `5b76d07510820138dd0aa76f0594ea5a8d2399c6d60574abbcd2ae6003a328fb` |
| `results/rq4/final/validation.json` | 405 | `9ef44c4d2330325a7a3119aedfd79bd5d607bb29e041e8317c25690fb7e86daf` |
| `results/rq4/final/provenance.json` | 1790 | `0b97b0666f81b155b27aaf3615a7db864ca618e13deaaef211544f28c7c1670a` |
| `results/rq4/final/table_primary.csv` | 1634 | `620506b5768f2e38931a47e2a47fbba3dc6d61b034ee027dbaf156860b324fc5` |
| `results/rq4/final/table_supplementary.csv` | 1353 | `c88a76a719ffbd0886489b50728fd549449762522c58b0b89c56c57f2e86847f` |
| `results/rq4/final/table_classwise.csv` | 857 | `8aa43d266bd8bcf785e0d31b5a3e5b52ca50ac84067d62cb420b046adc101318` |
| `results/rq4/final/table_invalid_debug.csv` | 361 | `91a455069b3abf83e637b484042ca5ceec3364abf74d855e16a07a57e25a92f9` |
| `results/rq4/final/cohort_and_controls.csv` | 1257 | `12e5f1eac40e3f197d67a47abafcaf72865778445b0dd1f23e293cf95ed0dba5` |
| `results/rq4/final/paired_outcomes.csv` | 29508 | `9bf525db6e215d1e37e8e52c5248d78df5e60891153467faa2012e296df61f5f` |
| `results/rq4/final/bootstrap_ci.csv` | 247 | `fea1681779b0e5e0d4ca0e72baee12dbdaee1c747a158f4ad09afacb089b69ff` |

The immutable v1/v2 input inventory remains in
`RQ4_ARTIFACT_REGISTER.md`; this changelog does not replace or rewrite its
registered hashes.

## Approved scope and preservation

- Reporting-only changes: four-row 295-report primary table and a separate
  252-report descriptive matched-subset table, both derived from saved v2
  predictions.
- Supporting B2/B4 and all ten B1 seeds remain supplementary. B5 remains
  archive/debug-only; historical v1 targeted results remain invalid for
  acquisition-policy claims.
- Documentation changes are limited to RQ4 presentation, provenance
  boundaries, navigation, and proposed deprecations. RQ1-RQ3 definitions and
  assumptions are not changed.
- No historical source, script, prediction, fold, bootstrap, or registered
  input is deleted, moved, retrained, or overwritten.

## Post-change verification

- Finalizer command: `.venv\Scripts\python.exe scripts\rq4_finalize_report.py`
  — **PASS**; 16 conditions, 4,720 rows, 295 reports, 58 projects, five folds,
  252 B3 matches, 43 fallbacks, four primary rows, two 252-report descriptive
  rows, 28 registered hashes verified, no training.
- Independent post-generation hash check using `verify_register` — **PASS,
  28/28**.
- `.venv\Scripts\python.exe -m pytest -q tests` — **17 passed**.
- `.venv\Scripts\python.exe -m pytest -q tests\test_rq4_finalize_report.py`
  — **1 passed**.
- `git diff --check` — **clean**.
- The final primary values match the baseline values; only the two descriptive
  matched-subset rows moved to `table_matchable_subset.csv`. B1 seed summary,
  B2/B4 values, paired outcomes, classwise values, and preserved bootstrap did
  not change. B5 remains only in the invalid/debug table.
- No hash-registered v1/v2 source, script, or output was edited, moved, or
  deleted. The 28-entry register remains unchanged.

## Changed-file SHA-256 comparison

| Path | Baseline SHA-256 | Post-change SHA-256 | Status |
|---|---|---|---|
| `docs/rq4/RQ4_ARTIFACT_REGISTER.md` | `7c3752a25cc26a612cb32c106f6351dabbf704504b2f3585449a44aedf1fdade` | `7c3752a25cc26a612cb32c106f6351dabbf704504b2f3585449a44aedf1fdade` | unchanged |
| `docs/rq4/RQ4_V2_SOURCE_AUDIT.md` | `b846718f88ba87db84d1f0152733dee66b1fbb363971514cb409580b62de7e88` | `b846718f88ba87db84d1f0152733dee66b1fbb363971514cb409580b62de7e88` | unchanged |
| `docs/rq4/FINAL_RQ4_DECISION.md` | `8895a84d9ce504db4d6755e82f279e76111ae756d36f2cea8174ea9f26f4a9ca` | `8895a84d9ce504db4d6755e82f279e76111ae756d36f2cea8174ea9f26f4a9ca` | unchanged |
| `docs/rq4/RQ4_README.md` | `b0ab6a10b4acaa5b2e6c81bf1946e5bc9299c7330b17da898970da875e764ba5` | `02d23aa1b86199054648f37aea850f36141bd350d0d9cde1021155275e96fe5b` | updated |
| `docs/rq4/RQ4_LEGACY_INVENTORY.md` | not present | `32b6dc7db4564a5cdfb3c15044151179daedd22980f4c70e7fc506c2df932878` | added |
| `docs/RQ4_FEASIBILITY.md` | `9b9fa97f27f44adaed82c3883abf53226279ac1d2b65bb416578cf0a0e80de32` | `1b0c062c7cdee495026253c837c61840a667359553fcf7845473fa623abad922` | updated |
| `docs/DATA_NOTES.md` | `667c91d4557eb5c7e183da4405e21f8f1d247b9c2d2c05d211e150227cfc0b52` | `b4a950b70385deabe80f41b6ce977c5015b7ada6b6497331466c170317f2992f` | appended RQ4 boundary section; earlier RQ1-RQ3 text retained |
| `README.md` | `e870578972334f4caaa56c18c74539d572fdee1b4658cba8a608c170eb972786` | `b6272be6923210fe45f88133a34378a1a664d99c0072d19a1ecd03a11b75d938` | added current RQ4 navigation |
| `scripts/rq4_finalize_report.py` | `f7fd2868d4b6b20b8a18fc2009eb0d066665163ad65a9a8abd9d36dfdb7c167b` | `3aa00cd89f149f5620a365235a3eecd515506bbeeb2c035e7ba1634f2904f9f3` | four-row primary and separate matched-subset output |
| `tests/test_rq4_finalize_report.py` | `5b76d07510820138dd0aa76f0594ea5a8d2399c6d60574abbcd2ae6003a328fb` | `c4a802b01019dc36084d5aecccde2d0b3f274c83e3b6dda8d7f7ac842e8919e5` | asserts table roles/cohorts, hashes, bootstrap, and archive safety |
| `results/rq4/final/validation.json` | `9ef44c4d2330325a7a3119aedfd79bd5d607bb29e041e8317c25690fb7e86daf` | `b4798c53c7bec07321d87c92a30ac616bb77550398a0887aaee3836a5732fa4c` | updated table acceptance fields |
| `results/rq4/final/provenance.json` | `0b97b0666f81b155b27aaf3615a7db864ca618e13deaaef211544f28c7c1670a` | `8b342d10e909708e0c6bffded17be5e769949d5becf35f6db6b8ca05dab8af0b` | updated finalizer hash |
| `results/rq4/final/table_primary.csv` | `620506b5768f2e38931a47e2a47fbba3dc6d61b034ee027dbaf156860b324fc5` | `66d2cd764d2cd2382cf942d76574cb6dae37ea27cdde8fdc76b56e6997e8fe79` | reduced from six to four 295-report rows |
| `results/rq4/final/table_matchable_subset.csv` | not present | `dd8a9620a5e0e52bf07eaedbb3a334333fb94aa2337e7c1e6cf03d87d08630fb` | added two descriptive 252-report rows |
| `results/rq4/final/table_supplementary.csv` | `c88a76a719ffbd0886489b50728fd549449762522c58b0b89c56c57f2e86847f` | `c88a76a719ffbd0886489b50728fd549449762522c58b0b89c56c57f2e86847f` | unchanged |
| `results/rq4/final/table_classwise.csv` | `8aa43d266bd8bcf785e0d31b5a3e5b52ca50ac84067d62cb420b046adc101318` | `8aa43d266bd8bcf785e0d31b5a3e5b52ca50ac84067d62cb420b046adc101318` | unchanged; full cohort |
| `results/rq4/final/table_invalid_debug.csv` | `91a455069b3abf83e637b484042ca5ceec3364abf74d855e16a07a57e25a92f9` | `91a455069b3abf83e637b484042ca5ceec3364abf74d855e16a07a57e25a92f9` | unchanged; B5 archive-only |
| `results/rq4/final/cohort_and_controls.csv` | `12e5f1eac40e3f197d67a47abafcaf72865778445b0dd1f23e293cf95ed0dba5` | `12e5f1eac40e3f197d67a47abafcaf72865778445b0dd1f23e293cf95ed0dba5` | unchanged |
| `results/rq4/final/paired_outcomes.csv` | `9bf525db6e215d1e37e8e52c5248d78df5e60891153467faa2012e296df61f5f` | `9bf525db6e215d1e37e8e52c5248d78df5e60891153467faa2012e296df61f5f` | unchanged |
| `results/rq4/final/bootstrap_ci.csv` | `fea1681779b0e5e0d4ca0e72baee12dbdaee1c747a158f4ad09afacb089b69ff` | `fea1681779b0e5e0d4ca0e72baee12dbdaee1c747a158f4ad09afacb089b69ff` | unchanged; preserved 5,000-resample result |

`RQ4_POST_FREEZE_CHANGELOG.md` is newly created and records its own baseline
and post-change inventory; its self-hash is intentionally not embedded in
this file to avoid a recursive checksum.
