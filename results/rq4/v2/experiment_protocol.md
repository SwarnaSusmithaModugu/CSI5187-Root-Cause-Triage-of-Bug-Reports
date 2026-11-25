# RQ4 v2 Experiment Protocol

Primary robust cohort excludes `comments_model`. Candidate units are coherent
description paragraphs and source-linked code/stack extracts. The visible state
is title plus remaining description text, unit type, unit index, unit count,
and length metadata. Hidden candidate text, embeddings, labels, correctness,
restored margins, and outcomes are never selector features.

B0 is withheld. B1 is one reveal chosen uniformly by predeclared seeds.
B2 is closest length. B3 is same-type plus closest length. B4 is a training-derived
field-type preference with deterministic fallback. B5 is the historical v1
method and is marked invalid for test-time selection. REF restores all allowed
source units.

All conditions share each report's one outer-fold fitted withheld LinearSVC.
