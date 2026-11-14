# When the evidence is missing: false "verified" verdicts in LLM fact-checking

Apart Research — AI × Epistemics Research Sprint (13–15 Nov 2026), Track 1 (Model Epistemics & Decision-Making Evals).

**Question.** When a verification pipeline cannot get usable evidence, how often does the model still answer
SUPPORT / REFUTE instead of NOT_ENOUGH_INFO — and how much can a simple structural constraint cut that, at what cost?

**Preexisting work.** None of the code, data or results here existed before the sprint; everything in this
repository was written on 13–15 Nov 2026. The idea that "could not check" must never be reported as "checked"
comes from the author's earlier day-to-day practice building verification tooling; no code from that work is used.

## Setup
- Claims: 150 SciFact claims (75 SUPPORT, 75 CONTRADICT) from the train+dev splits, each with a single-label rationale
  whose first sentence is at index ≥ 2 of the abstract.
- Six evidence states per claim: E0 gold abstract · E1 empty retrieval · E2 error string · E3 on-topic non-cited abstract
  (TF-IDF nearest neighbour) · E4 gold abstract truncated before the first rationale sentence · E5 the claim echoed back.
- Protocols: P0 plain prompt · P1 explicit licence to abstain · P2 the model must copy the deciding sentence; a deterministic
  checker downgrades to NOT_ENOUGH_INFO unless the quote is in the evidence and is not a restatement of the claim
  (variants P2raw = no checker, P2+overlap = also requires shared content words with the claim, computed offline).
- Models (all local, temperature 0): gemma4-26b-a4b (llama.cpp), gemma2:9b, qwen3.5 (9.7B) and gemma2:2b (Ollama).

## Results
The report is `report/report.pdf` (source `report/report.html`). Headline numbers are in Table 1 of the report and in
`results/summary.json`; paired bootstrap differences, checker rejection reasons and label directions are in
`results/analysis.json`. Raw model outputs (every call, including failed attempts that were later retried) are in
`results/raw/`. Item audits are in `notes/audit_e3.md` and `notes/audit_e4.md`.

## Reproduce
```
# SciFact release: https://scifact.s3-us-west-2.amazonaws.com/release/latest/data.tar.gz
python3 src/build_items.py --data <scifact>/data --out data/items.jsonl
python3 src/build_e4b.py --corpus <scifact>/data/corpus.jsonl --items data/items.jsonl --out data/items_e4b.jsonl
python3 src/run.py --model ollama:gemma2:2b --items data/items.jsonl --out results/raw/ollama_gemma2_2b.jsonl
python3 src/score.py          # -> results/summary.json and markdown tables
python3 src/analyze.py        # -> results/analysis.json and figures/tradeoff.svg
python3 src/make_tables.py --write report/report.html   # Tables 1-2 in the report
```
`run.py` is resumable: re-running the same command skips item/protocol pairs that already succeeded; scoring uses the
last successful output per pair. Backends are read from `~/.config/apart-epistemics/backends.json` (see `src/backends.py`).

## Licence
Code: MIT (see `LICENSE`). Data: see below.

## Data licences
SciFact claims and annotations: CC BY 4.0. Abstracts: S2ORC, ODC-By 1.0. Wadden et al., "Fact or Fiction: Verifying
Scientific Claims", EMNLP 2020. `data/items.jsonl` is a derived subset and keeps those terms.
