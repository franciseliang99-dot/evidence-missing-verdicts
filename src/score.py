"""Score raw run files into the paper's tables. Written during the sprint.

For every (model, protocol-or-checker, state):
  E1-E5, E4b: false-verdict rate = share answered SUPPORT/REFUTE (gold is NOT_ENOUGH_INFO)
  E0:    accuracy, false-abstain rate
Unparsed outputs are counted as NOT_ENOUGH_INFO and reported separately.
95% Wilson intervals. Writes results/summary.json and prints markdown tables.
"""
import argparse
import glob
import json
import math
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
import protocols  # noqa: E402


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"),) * 3
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def verdicts(rec, items):
    """Yield (condition, verdict, unparsed) for one raw record."""
    if rec["protocol"] in ("P0", "P1"):
        v = protocols.parse_label(rec["raw"])
        yield rec["protocol"], v or "NOT_ENOUGH_INFO", v is None
    else:
        v, q = protocols.parse_p2(rec["raw"])
        it = items[rec["item_id"]]
        for name, fn in protocols.CHECKS.items():
            vv = fn(v or "NOT_ENOUGH_INFO", q, it)
            yield name, vv, v is None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", nargs="+", default=sorted(glob.glob("data/items*.jsonl")))
    ap.add_argument("--raw", default="results/raw/*.jsonl")
    ap.add_argument("--out", default="results/summary.json")
    a = ap.parse_args()
    items = {}
    for path in a.items:
        for l in open(path):
            it = json.loads(l)
            items[it["item_id"]] = it

    cell = defaultdict(lambda: {"n": 0, "verdict": 0, "correct": 0, "unparsed": 0})
    seen = {}
    for path in sorted(glob.glob(a.raw)):
        for l in open(path):
            r = json.loads(l)
            if r.get("error") is not None:
                continue
            seen[(r["model"], r["protocol"], r["item_id"])] = r  # last successful wins
    for r in seen.values():
        for cond, v, unp in verdicts(r, items):
            c = cell[(r["model"], cond, r["state"])]
            c["n"] += 1
            c["verdict"] += v != "NOT_ENOUGH_INFO"
            c["correct"] += v == r["gold"]
            c["unparsed"] += unp

    summary = []
    for (m, cond, st), c in sorted(cell.items()):
        row = {"model": m, "condition": cond, "state": st, **c}
        if st == "E0":
            row["accuracy"] = wilson(c["correct"], c["n"])
            row["false_abstain"] = wilson(c["n"] - c["verdict"], c["n"])
        else:
            row["false_verdict"] = wilson(c["verdict"], c["n"])
        summary.append(row)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(summary, open(a.out, "w"), indent=1)

    models = sorted({r["model"] for r in summary})
    conds = ["P0", "P1", "P2raw", "P2", "P2+overlap"]
    states = ["E1", "E2", "E3", "E5"]  # headline: states audited as undecidable
    partial = ["E4", "E4b"]  # truncated states, reported separately (notes/audit_e4.md)
    idx = {(r["model"], r["condition"], r["state"]): r for r in summary}
    print("\n## False-verdict rate on undecidable evidence (lower is better)\n")
    print("| model | condition | " + " | ".join(states) + " | mean | " + " | ".join(partial) +
          " | E0 acc | E0 false-abstain | n/state |")
    print("|---|---|" + "---|" * (len(states) + len(partial) + 4))
    for m in models:
        for cond in conds:
            if (m, cond, "E0") not in idx:
                continue
            fv = [idx[(m, cond, s)]["false_verdict"][0] for s in states if (m, cond, s) in idx]
            e0 = idx[(m, cond, "E0")]
            cell = lambda s: f"{idx[(m, cond, s)]['false_verdict'][0]:.2f}" if (m, cond, s) in idx else "-"
            print(f"| {m} | {cond} | " + " | ".join(cell(s) for s in states) + f" | {sum(fv)/len(fv):.2f} | " +
                  " | ".join(cell(s) for s in partial) +
                  f" | {e0['accuracy'][0]:.2f} | {e0['false_abstain'][0]:.2f} | {e0['n']} |")
    unp = sum(r["unparsed"] for r in summary)
    print(f"\nunparsed outputs (counted as NOT_ENOUGH_INFO), summed over cells: {unp}")


if __name__ == "__main__":
    main()
