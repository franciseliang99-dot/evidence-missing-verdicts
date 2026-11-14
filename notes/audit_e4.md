# Audit of E4 (truncated before the first rationale sentence)

Done during the sprint (2026-11-13), after the first full gemma4-26b-a4b run.

Trigger: under P0, gemma4 gave a verdict on 58/150 E4 items and 86% of those verdicts matched the
hidden gold label. Either the truncated text still decides the claim, or the model answers from
background knowledge. Both mean E4 is not a clean "undecidable" state.

Sample: 20 of the 58 E4 items where gemma4 (P0) gave a verdict, shuffled with seed 7.
One annotator, reading the full truncated evidence against the claim (the AI assistant used for this project, Claude; see the correction in `audit_e3.md`).

| # | item | model | hidden gold | truncated text decides? | why |
|---|---|---|---|---|---|
| 0 | 420-E4 | SUPPORT | SUPPORT | yes | title states the finding |
| 1 | 1090-E4 | SUPPORT | REFUTE | no | |
| 2 | 280-E4 | SUPPORT | SUPPORT | yes | kept sentence states it |
| 3 | 1028-E4 | SUPPORT | SUPPORT | mostly | title |
| 4 | 1163-E4 | SUPPORT | SUPPORT | mostly | "ssDNA binding protein unique to Deinococcus" |
| 5 | 846-E4 | SUPPORT | SUPPORT | mostly | kept sentences on IL-1β tuned by microbe size |
| 6 | 790-E4 | REFUTE | REFUTE | yes | title: "Guardians of the CNS" |
| 7 | 500-E4 | SUPPORT | REFUTE | no | cut at RESULTS |
| 8 | 32-E4 | REFUTE | REFUTE | no | cut before the model results |
| 9 | 553-E4 | REFUTE | REFUTE | yes | title: "High abundance" |
| 10 | 632-E4 | REFUTE | REFUTE | yes | title |
| 11 | 283-E4 | REFUTE | REFUTE | no | cut at RESULTS |
| 12 | 220-E4 | SUPPORT | SUPPORT | yes | title |
| 13 | 767-E4 | REFUTE | REFUTE | no | cut at RESULTS |
| 14 | 1383-E4 | REFUTE | SUPPORT | yes | kept sentence; model wrong |
| 15 | 1170-E4 | REFUTE | REFUTE | yes | title: "NEMO Prevents ..." |
| 16 | 578-E4 | REFUTE | REFUTE | yes | title: "... CSF1R is crucial" |
| 17 | 963-E4 | REFUTE | REFUTE | yes | title: "... Stabilizes Pre-mRNAs" |
| 18 | 595-E4 | REFUTE | REFUTE | no | |
| 19 | 807-E4 | REFUTE | SUPPORT | mostly | last kept sentence; model wrong |

Result: 14/20 decidable from the truncated text (10 clearly, 4 mostly); in 9 of the 14 the title
alone carries the answer. Of the 6 undecidable items the model matched the hidden label in 4,
which is consistent with answering from background knowledge (a confound we cannot separate here).

Consequences for the analysis:
- E4 is excluded from the headline false-verdict mean; the headline uses E1, E2, E3, E5.
- E4 is reported separately as "partial evidence", with this audit.
- E4b (src/build_e4b.py) drops the title and keeps only abstract sentences before the first
  rationale sentence; it is audited the same way before any claim is made about it.

Limits: one annotator; SciFact rationales mark a sufficient set, not every informative sentence,
so "truncated before the rationale" never guaranteed undecidability. This was a design error in
the original E4 and is reported as such.

## E4b audit (title removed)

gemma4-26b-a4b, P0: 39/150 E4b items got a verdict (E4: 58); 79% of those match the hidden label.
Same procedure: 20 of the 39, shuffled with seed 7, full evidence read.

| verdict on decidable? | items |
|---|---|
| decidable, clearly (8) | 1210, 1137, 559, 1383, 32, 912, 1158, 963 |
| decidable, mostly (6) | 220, 578, 744, 846, 1360, 807 |
| not decidable (6) | 835, 500, 283, 1090, 641, 1073 |

Of the 14 decidable items the model's verdict was wrong on 5 (1383, 807, 912, 1158, 963).
Of the 6 undecidable items it matched the hidden label on 4 (835, 283, 641, 1073).

Result: removing the title lowers the verdict rate (0.39 → 0.26 under P0) but leaves the
remaining text decidable in 14/20 sampled cases. The informative sentences are results or
background sentences that SciFact did not mark as rationale. Truncation before the rationale is
therefore not a valid way to build undecidable evidence in SciFact without new annotation.

Decision: E4 and E4b are reported only as "partial evidence" (a verdict there is often
legitimate), never as false verdicts. E4b is not run on the other models: it does not yield a
clean undecidable state, so it would add cost without adding a measurement.
