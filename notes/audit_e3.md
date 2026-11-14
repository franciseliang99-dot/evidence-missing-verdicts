# E3 audit (author, 2026-11-13)

Question: is the E3 "on-topic non-cited" abstract really undecidable for its claim? If it actually supports or
refutes the claim, a SUPPORT/REFUTE answer on E3 is not a false verdict.

Method: 20 E3 items drawn with `random.Random(7)` from the 150; for each I read the claim and the first
700 characters of the neighbour abstract (title + opening sentences) and judged whether that text decides the claim.

Claim ids: 993, 853, 3, 1265, 1355, 143, 106, 909, 277, 1024, 499, 603, 835, 929, 219, 1262, 571, 592, 223, 736

Result: 0 / 20 decide the claim. 19 / 20 are on the same topic (shared entity or mechanism);
1 / 20 (claim 736, neighbour about chronic headache) is off-topic — lexical overlap without topical match.

Limitations: one annotator (the author); only the opening ~700 characters were read, so a deciding
sentence later in an abstract would be missed. Treat E3 false-verdict rates as an upper bound on
"answered from irrelevant evidence" with a small contamination margin.

## Who did this audit
Correction (2026-11-14): the audit above was carried out by the AI assistant used for this project (Claude), not by
the author by hand; the earlier "(the author)" was wrong. Same for the E4 / E4b audits in `audit_e4.md`.

## Second E3 audit: items that drew verdicts (2026-11-14)
Why: the first audit sampled from all 150 E3 items and read only ~700 characters, but false-verdict rates are made
of the items where a model DID answer. Those may be enriched for decidable neighbours.

Method: E3 items where at least one of the four models gave SUPPORT/REFUTE under P0 (93 of 150). 20 drawn with
`random.seed(11)`; the full neighbour abstract was read against the claim. Annotator: the AI assistant (Claude).

| item | votes (P0) | decides the claim? | note |
|---|---|---|---|
| 445 | 9b R, 2b S | no | GATA3 in B-cell commitment, not HSC self-renewal |
| 633 | 9b R, qwen R, 2b R | no | focal-contact mechanosensing; nothing on inflammation/fibrosis |
| 499 | 9b S, 2b R | no | HbA1c unreliable in red-cell disorders; nothing on SCT direction |
| 563 | 2b S | no | statins meta-analysis; no haplogroup |
| 728 | qwen R | no | Ly6C subsets described, inflammatory capacity not compared |
| 1224 | all four S | mostly | latent HCMV infection of myeloid progenitors changes cytokine expression via viral IL-10 |
| 1210 | 2b S | no | cytokines in memory T cells; nothing on receptor density / range |
| 500 | 9b S, qwen R, 2b R | no | dementia comorbidity; headache not assessed |
| 790 | gemma4 R, 9b R, qwen R | yes | microglia described as CNS cells (claim says peripheral) |
| 745 | 2b R | no | viral E3 ligase; not MafA |
| 111 | qwen R, 2b S | no | naive human ESCs; not androgenetic haploid mouse ESCs |
| 197 | 9b S, 2b S | no | CCR7 on Tregs; CCL19 never mentioned |
| 1157 | 9b R, 2b S | no | Finnish cervical screening; not DESMOND |
| 1107 | all four S | mostly | cold exposure induces browning of white fat depots (mice) |
| 595 | qwen R, 2b S | no | sepsis definitions 2011-15; no incidence trend |
| 859 | 9b R, qwen R, 2b R | no | RUNX1 in haematopoiesis; nothing on tumours |
| 801 | qwen R | no | N-cadherin review; no antibody, no castration resistance |
| 1035 | all four S | yes | KDM4A overexpression improves human SCNT |
| 743 | 9b R, qwen R, 2b R | no | macrolides and pyloric stenosis; not MI |
| 314 | all four S | mostly | APOBEC3G deaminates C to U on the minus strand, triggering viral destruction |

Result: 5 / 20 decidable (2 clearly, 3 mostly); all 5 are items where every model that answered agreed with the
hidden gold label. The other 15 verdicts are false verdicts.
Consequence: E3 false-verdict rates are upper bounds; roughly a quarter of E3 verdicts may be legitimate. TF-IDF
nearest neighbours are sometimes papers on the same finding. Reported in the paper (Sections 3.1, 4.1, 5).
