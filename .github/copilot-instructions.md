# Project guardrails

1. Never edit anything under `data/raw/`. Raw data is read-only.
2. Never fabricate a number, a label, a comment, or a file. If something is missing, stop and report it.
3. Do not install packages beyond `requirements.txt`. If one is needed, stop and ask.
4. Never print, log, or commit the GitHub token. It lives only in `.env`.
5. Never drop rows silently. Flag them in a column and report counts. The team decides what to remove.
6. Print real outputs (counts, headers, sample rows) and paste them into `docs/DATA_NOTES.md`. Do not summarize from memory.
7. If an expected number differs (369, 122/121/126), stop and report the difference before continuing.

Gold labels are the 369 hand-labeled reports. They are the only data we train and test on.
