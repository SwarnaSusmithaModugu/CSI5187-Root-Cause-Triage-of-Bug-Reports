# Evidence-Grounded, Calibrated, Selective Root-Cause Triage of Bug Reports

## How to reproduce

Setup and reproduction steps will be documented after the dataset has been verified.

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
- **RQ3:** Comparison of TF-IDF with Linear SVM, SetFit, and an open-weight large language model.
- **RQ4:** Identification and evaluation of decisive diagnostic evidence, citation faithfulness, and counterfactual information restoration.

# Team

**CSI 5187 – Software Engineering Research Project**


- Vineela (300493522)
- Swarna  (300561282) 
- Nidhi   (300518170) 