# RQ4 Artifact Register

## Snapshot and preservation

- Repository `HEAD`: `dcf9a752116317161d90992046e8134d25c7877f`
- Branch: `rq3-structural-corrected`
- RQ4 source and result files were untracked in the worktree at the time of
  this register; the SHA-256 values below identify the actual audited bytes.
- v1 files under `results/rq4/` are historical archival artifacts. v2 files
  under `results/rq4/v2/` are preserved as generated. No existing artifact was
  moved, deleted, or overwritten for this register.
- File hashes are SHA-256 of exact workspace bytes, not Git blob identifiers.
- Commands below are provenance for files already present; they were not
  re-executed to produce this register.

## Result inventory

| Path | Purpose / status | Producing script and command | SHA-256 |
|---|---|---|---|
| `results/rq4/feasibility.csv` | Original 369-report feasibility inventory; historical | `src/rq4_feasibility.py`; `.venv\Scripts\python.exe -m src.rq4_feasibility` | `9f9c24d94a375307aa51a0a9dd0ee61515a319d745de190e66da10d8e63ffaa8` |
| `results/rq4/rq4_reveal_predictions.csv` | v1 report-condition predictions; invalid targeted-selection policy is historical only | `src/rq4_reveal.py`; `.venv\Scripts\python.exe -m src.rq4_reveal` | `b398b1f634e32c3670f0a281bf58eabed05250e3bf0512517c8e6a215c63cd8e` |
| `results/rq4/rq4_results.csv` | v1 summary metrics; historical only | `src/rq4_reveal.py`; `.venv\Scripts\python.exe -m src.rq4_reveal` | `6755abd6c6853c11ce06649eeb916794dfc63bcb64ba3a6ac70f54a30f080f9f` |
| `results/rq4/v2/audit.md` | Earlier generated audit note; supporting artifact, not source proof | `src/rq4_v2/audit.py`; `.venv\Scripts\python.exe -m src.rq4_v2.audit` | `7a3190b81580026b36a4fa2470407799cac85c585dd8ccc4e40adf0fd1bdeb9d` |
| `results/rq4/v2/experiment_protocol.md` | Earlier v2 protocol note | `src/rq4_v2/audit.py`; `.venv\Scripts\python.exe -m src.rq4_v2.audit` | `9a3e6d96eaee27d5bb0e047a7b88f60000f968945eb46d4fee97ab6929d49b03` |
| `results/rq4/v2/interpretation.md` | Earlier v2 baseline interpretation; source audit supersedes its unsupported policy wording where applicable | `src/rq4_v2/interpret.py`; `.venv\Scripts\python.exe -m src.rq4_v2.interpret` | `5efb9a136c1018e559ace49f42b8ad0d3b481162970d8df605b906d40a9f6e0d` |
| `results/rq4/v2/unit_manifest_v2.csv` | Per-report original/robust candidate counts and IDs | `src/rq4_v2/audit.py`; `.venv\Scripts\python.exe -m src.rq4_v2.audit` | `c29560d7f721dfbcee542b4d87e1b45bed28a9f54caccb4bf91f10ab21aeb574` |
| `results/rq4/v2/unit_audit.csv` | Per-unit text hashes, lengths, source fields, and containment flags; broader audit inventory also includes comments | `src/rq4_v2/audit.py`; `.venv\Scripts\python.exe -m src.rq4_v2.audit` | `04f320fa7f70897a6bc07cff19900d49e383029ab8a64015a62c0de350b8f29c` |
| `results/rq4/v2/control_match_audit.csv` | B2/B3 unit IDs and match/length metadata | `src/rq4_v2/baselines.py`; `.venv\Scripts\python.exe -m src.rq4_v2.baselines` | `c4863dc429ad7ae74f6d54522cfcfdcd9ae7aa2fbde2701645365c71b96b694b` |
| `results/rq4/v2/fold_map.csv` | URL/project-to-test-fold mapping for 295 robust-cohort reports | `src/rq4_v2/audit.py`; `.venv\Scripts\python.exe -m src.rq4_v2.audit` | `4dbd585a64b239d8702f31590fef2c48a611781704590b9a76f36abdb7cb4da3` |
| `results/rq4/v2/reveal_predictions.csv` | Saved predictions for B0, ten B1 seeds, B2, B3, B4, B5 reference, and REF | `src/rq4_v2/baselines.py`; `.venv\Scripts\python.exe -m src.rq4_v2.baselines` | `a5a9ef241959250dbf2420b565c0efac3dc8678f4005ba0fc1e1ca305743ee47` |
| `results/rq4/v2/metrics.csv` | Per-condition summary metrics from saved predictions | `src/rq4_v2/evaluate.py`; `.venv\Scripts\python.exe -m src.rq4_v2.evaluate` | `37a2c02f2d5a9f0615f7e54f372ef0751462ceff2ac570939abccbfdb3bc5052` |
| `results/rq4/v2/paired_differences.csv` | B3-versus-B0 per-report correctness changes | `src/rq4_v2/evaluate.py`; `.venv\Scripts\python.exe -m src.rq4_v2.evaluate` | `a2ef0c131db84460c67bd0da6fe406b857ec4fca8f3e11ba73d08b0f98dae221` |
| `results/rq4/v2/bootstrap_ci.csv` | 5,000-resample paired project-cluster B3-minus-B0 interval | `src/rq4_v2/evaluate.py`; `.venv\Scripts\python.exe -m src.rq4_v2.evaluate` | `fea1681779b0e5e0d4ca0e72baee12dbdaee1c747a158f4ad09afacb089b69ff` |
| `results/rq4/v2/subgroup_metrics.csv` | Per-condition class-subset summaries; do not treat single-class subset macro-F1 as full-cohort class F1 | `src/rq4_v2/evaluate.py`; `.venv\Scripts\python.exe -m src.rq4_v2.evaluate` | `5026ffe3ead8fd63587a2fd0b093ec602fb91c8f06b20dea5fe746a790fa0859` |
| `results/rq4/v2/run_manifest.json` | Dataset/fold hashes and v2 cohort metadata | `src/rq4_v2/audit.py`; `.venv\Scripts\python.exe -m src.rq4_v2.audit` | `d856efb4a3e55c808ea594b64c1df91288a0bff5fcd4a2d7f2b70b2ad72a4cd8` |
| `results/rq4/v2/policy_features_schema.json` | Declared visible/excluded policy feature schema; declaration is not evidence that a selector used it | `src/rq4_v2/interpret.py`; `.venv\Scripts\python.exe -m src.rq4_v2.interpret` | `d6777b26f26bdc1e40cbc4f4ffa48935edfd4bea7d5df3e2827d4f68e6653285` |

Expected v2 artifacts from the cleanup instructions are all present. The
source audit and current-facing RQ4 documents are organized under
`docs/final/`. This register remains at `docs/rq4/RQ4_ARTIFACT_REGISTER.md`
because the report finalizer reads that fixed path; its 28 registered input
records and hashes are unchanged.

## Frozen input CSV

| Path | Purpose | SHA-256 |
|---|---|---|
| `data/processed/gold_v1.csv` | Frozen 369-report input | `5ae3365e515e22ceb986859cb84c65a2b1d376872bd11a804033eeebf505da8e` |

## RQ4 source scripts

All commands are from the repository root. Script hashes identify the source
version inspected; untracked scripts are identified by their hashes rather
than by the repository `HEAD` alone.

| Script | Purpose / relevant outputs | SHA-256 |
|---|---|---|
| `src/rq4_reveal.py` | v1 extraction, masking, targeted selector, and predictions | `5ebf22e8b55b3b599b9e461d5a4bee56c38ed43087170b524da8888c95bad8f4` |
| `src/rq4_feasibility.py` | v1 feasibility cohort and manifest | `b712914a539a9761e7c6519b368414186bf792328aae6a8d036703f4991e76a4` |
| `src/rq4_v2/__init__.py` | Package marker | `8c580a06e0d34eca9c426b704a680ca9010ea64fe2678b08b01c98e667a4bec6` |
| `src/rq4_v2/audit.py` | v2 unit audit, manifest, fold map, protocol, audit note, run manifest | `5af1d886b513009a8776f2d50b84140839bd22e60ef1bbb00224954d61c78fd4` |
| `src/rq4_v2/baselines.py` | v2 cohort, selectors/controls, fold classifier, predictions, match audit | `5f64bb7172a814a7bc0e3c7a29b88fb728950b93d6c0e79d2b1db5e0086fce48` |
| `src/rq4_v2/evaluate.py` | v2 metrics, paired changes, bootstrap, subgroup outputs | `67e0b96612ec195645c9c36cae6d7e5b19a2ace5728660873b6af72abb37439e` |
| `src/rq4_v2/interpret.py` | Earlier v2 interpretation and policy schema | `f607adf266a7fc380dbff94ff1bca90a8b402a12b12f225663deb4e551e287ae` |
| `src/clean.py` | Original-description code and stack extraction | `1ac8bde2eb725e79c9adc01de9c77b233f9569a19bfa2b41e202e83075649742` |
| `src/build_processed.py` | Pre-fix comment cutoff and derived fields | `f2ed5b3ba1d4acc1535f44dea7c3d7fc45df91b62569e3a02c9cfd2a351d63fa` |
| `src/finalize_gold.py` | Comment leak masking and frozen gold write | `7454e04fdcf1b6bb7b34478557102cb45f3bac86db5060e54d66fc8811412ae6` |

## Preservation note

The v1 and v2 result files were not edited by this audit. Treat their current
bytes as archival. Since the result files and v2 scripts are untracked at the
recorded revision, preserve the working tree or separately archive these
registered bytes before any branch switch or cleanup.
