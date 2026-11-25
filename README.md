# Evidence-Grounded, Calibrated, Selective Root-Cause Triage of Bug Reports

## Current documentation

- [Data notes](docs/final/DATA_NOTES.md) · [RQ2 results](docs/final/RQ2_RESULTS.md) · [RQ3 results](docs/final/RQ3_RESULTS.md)
- [RQ4 guide and final links](docs/final/RQ4_README.md) · [RQ4 primary table](results/rq4/final/table_primary.csv)

Historical feasibility notes and superseded drafts are under `docs/archive/`.

## How to reproduce

Run these commands from the repository root in Windows PowerShell. The
environment uses Python, pandas, NumPy, SciPy, scikit-learn,
sentence-transformers, and the other packages pinned or listed in
`requirements.txt`.

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

# Existing completed annotation inputs are required for RQ2.
python src\rq2_reliability.py
python src\rq2_eval.py
python src\rq2_diagnostics.py
python -m pytest -q tests
```

RQ2 inputs under `data/interim/` are `sufficiency_labels.csv` (201 human
annotations), `pilot_A.csv` (independent Human B overlap), `pilot_B.csv`
(GPT-6), and `pilot_C.csv` (Claude Haiku 5.5). The annotation sheet builder is
only for creating a new blank sheet; do not rerun it over completed labels.

RQ2 uses seed 42, five project-grouped outer folds, and the frozen
`all-MiniLM-L6-v2` encoder with title plus cleaned description only. The
archived issue text has not been verified as a filing-time snapshot. The
dataset contains 369 gold reports across 61 projects; the 201-report
annotation sample spans 47 projects and is stratified by root-cause class.

Expected RQ2 outputs include `results/rq2_oof.csv`,
`results/rq2_evaluation_subset.csv`,
`results/rq2_diagnostic_summary.csv`,
`results/rq2_embedding_truncation_audit_corrected.csv`, and the other
diagnostic CSVs documented in
[`docs/final/RQ2_RESULTS.md`](docs/final/RQ2_RESULTS.md).

RQ3 completed classical and nested hybrid OOF outputs are organized under
`results/rq3/tables/`. Reproduce them with:

```powershell
.venv\Scripts\python.exe src\rq3_classical.py
.venv\Scripts\python.exe src\rq3_hybrid.py
```

See [`docs/final/RQ3_RESULTS.md`](docs/final/RQ3_RESULTS.md) for the verified tables,
input boundaries, and pending SetFit/zero-shot LLM comparisons. No RQ3 figures
are currently archived.

## RQ4 frozen result

RQ4 is **FROZEN — QUALIFIED RETROSPECTIVE RESULT**. The audited comparison
does not establish a beneficial policy or deployable clarification agent.
Start with the [RQ4 README](docs/final/RQ4_README.md) and its
[four-row primary table](results/rq4/final/table_primary.csv). Reproduce only
the derived report with
`.venv\Scripts\python.exe scripts\rq4_finalize_report.py`; this does not
retrain models or rerun selectors.

# Overview

This project investigates automated root-cause classification of software bug reports using Machine Learning and Natural Language Processing (NLP).

The goal is to understand how different information fields in bug reports contribute to root-cause diagnosis, how models handle incomplete or insufficient information, and whether their predictions can be supported by identifiable diagnostic evidence.

The project also explores evidence-grounded diagnosis by examining whether models can identify relevant evidence in bug reports and whether providing additional diagnostic information improves classification performance.

# Research Questions

Our project investigates four main research questions:

**RQ1 – Field Importance**

How important are individual bug-report fields, such as titles and descriptions, for root-cause classification?

**RQ2 – Sufficiency and Selective Abstention**

Can a model identify when a bug report contains insufficient information for a reliable diagnosis and abstain from making uncertain predictions?

**RQ3 – Model Comparison**

How do traditional machine learning approaches, few-shot learning methods, and large language models compare in root-cause classification?

**RQ4 – Evidence-Grounded Earned Diagnosis**

Can models identify decisive diagnostic evidence, faithfully support their predictions with evidence from bug reports, and improve their diagnosis when important missing information is restored?

# Dataset

The project uses the Amadeus GitHub Bug Dataset.

The manually labelled subset contains three root-cause categories:

The original labelled CSV files contain 371 rows. After removing duplicate issue URLs, 369 unique bug reports remain.

The primary textual fields used in our initial experiments are:

- Bug report title
- Bug report description

Additional GitHub issue information and comment history may be investigated separately, subject to data availability and leakage controls.

# Methodology

The project is organized around four research questions:

- **RQ1:** Field ablation experiments, including leave-one-out and leave-one-in analysis.
- **RQ2:** Sufficiency annotation, classification, confidence calibration, and selective prediction.
- **RQ3:** Comparison of completed TF-IDF/classical and hybrid models, with
	SetFit and zero-shot LLM comparisons planned but not yet available.
- **RQ4:** Identification and evaluation of decisive diagnostic evidence, citation faithfulness, and counterfactual information restoration.

# Team

**CSI 5187 – Software Engineering Research Project**


- Vineela (300493522)
- Swarna  (300561282) 
- Nidhi   (300518170) 