"""Secondary analyses and figures. Written during the sprint.

  - direction of false verdicts (share SUPPORT vs REFUTE) per state
  - E4 leakage: when a model gives a verdict on the truncated abstract, does it match the hidden gold label?
  - P2 checker: which test rejected each verdict (no quote / not in evidence / restatement / no overlap)
  - paired bootstrap (resampling claims) for the change in mean false-verdict rate vs P0, and E0 cost
  - figure: trade-off between undecidable-evidence false verdicts and E0 false abstentions (SVG)
"""
import argparse
import re
import glob
import json
import os
import random
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
import protocols as P  # noqa: E402

UNDEC = ["E1", "E2", "E3", "E5"]  # headline: audited undecidable states
PARTIAL = ["E4", "E4b"]  # truncated states, reported separately (notes/audit_e4.md)
CONDS = ["P0", "P1", "P2raw", "P2", "P2+overlap"]


def load(items_paths, raw_glob):
    items = {}
    for path in items_paths:
        for l in open(path):
            it = json.loads(l)
            items[it["item_id"]] = it
    recs = {}
    for path in sorted(glob.glob(raw_glob)):
        for l in open(path):
            r = json.loads(l)
            if r.get("error") is None:
                recs[(r["model"], r["protocol"], r["item_id"])] = r
    # verdict table: V[model][cond][(claim_id, state)] = verdict
    V = defaultdict(lambda: defaultdict(dict))
    quotes = {}
    for (m, p, iid), r in recs.items():
        it = items[iid]
        key = (it["claim_id"], it["state"])
        if p in ("P0", "P1"):
            V[m][p][key] = P.parse_label(r["raw"]) or "NOT_ENOUGH_INFO"
        else:
            v, q = P.parse_p2(r["raw"])
            v = v or "NOT_ENOUGH_INFO"
            quotes[(m, key)] = (v, q)
            for name, fn in P.CHECKS.items():
                V[m][name][key] = fn(v, q, it)
    return items, V, quotes


def claim_stats(V, m, cond, claims):
    """Per-claim (mean false verdict over the UNDEC states, E0 abstained 0/1, E0 correct 0/1)."""
    out = {}
    for c in claims:
        fv = [V[m][cond][(c, s)] != "NOT_ENOUGH_INFO" for s in UNDEC if (c, s) in V[m][cond]]
        if len(fv) != len(UNDEC) or (c, "E0") not in V[m][cond]:
            continue
        out[c] = (sum(fv) / len(fv), V[m][cond][(c, "E0")] == "NOT_ENOUGH_INFO")
    return out


def bootstrap_diff(a, b, B=2000, seed=0):
    """a, b: dict claim -> value; paired over shared claims. Returns (mean diff b-a, lo, hi)."""
    ks = sorted(set(a) & set(b))
    if not ks:
        return None
    d = [b[k] - a[k] for k in ks]
    rng = random.Random(seed)
    means = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(B))
    return sum(d) / len(d), means[int(0.025 * B)], means[int(0.975 * B)], len(ks)


def svg_tradeoff(points, path):
    """points: list of (model, cond, x=E0 false-abstain, y=mean false verdict)."""
    W, H, L, T, R, Bm = 640, 420, 70, 30, 190, 55
    pw, ph = W - L - R, H - T - Bm
    colors = ["#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#8c564b"]
    shapes = {"P0": "circle", "P1": "square", "P2raw": "diamond", "P2": "triangle", "P2+overlap": "star"}
    order_pref = ["llamacpp:gemma4-26b-a4b", "ollama:gemma2:9b", "ollama:qwen3.5:latest", "ollama:gemma2:2b"]
    models = sorted({p[0] for p in points}, key=lambda m: (order_pref.index(m) if m in order_pref else 99, m))
    X = lambda x: L + x * pw
    Y = lambda y: T + (1 - y) * ph
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="Helvetica,Arial,sans-serif" font-size="12">',
         f'<rect x="{L}" y="{T}" width="{pw}" height="{ph}" fill="none" stroke="#333"/>']
    for t in [0, .2, .4, .6, .8, 1]:
        s.append(f'<line x1="{X(t)}" y1="{T+ph}" x2="{X(t)}" y2="{T+ph+5}" stroke="#333"/><text x="{X(t)}" y="{T+ph+18}" text-anchor="middle">{t:.1f}</text>')
        s.append(f'<line x1="{L-5}" y1="{Y(t)}" x2="{L}" y2="{Y(t)}" stroke="#333"/><text x="{L-8}" y="{Y(t)+4}" text-anchor="end">{t:.1f}</text>')
        s.append(f'<line x1="{L}" y1="{Y(t)}" x2="{L+pw}" y2="{Y(t)}" stroke="#eee"/>')
    s.append(f'<text x="{L+pw/2}" y="{H-12}" text-anchor="middle">False-abstention rate on gold evidence (E0)</text>')
    s.append(f'<text transform="translate(18,{T+ph/2}) rotate(-90)" text-anchor="middle">False-verdict rate, mean of E1, E2, E3, E5</text>')

    def mark(shape, x, y, c):
        if shape == "circle":
            return f'<circle cx="{x}" cy="{y}" r="5" fill="{c}"/>'
        if shape == "square":
            return f'<rect x="{x-4.5}" y="{y-4.5}" width="9" height="9" fill="{c}"/>'
        if shape == "diamond":
            return f'<polygon points="{x},{y-6} {x+6},{y} {x},{y+6} {x-6},{y}" fill="none" stroke="{c}" stroke-width="1.6"/>'
        if shape == "triangle":
            return f'<polygon points="{x},{y-6} {x+6},{y+5} {x-6},{y+5}" fill="{c}"/>'
        return f'<polygon points="{x},{y-7} {x+2},{y-2} {x+7},{y-2} {x+3},{y+2} {x+5},{y+7} {x},{y+4} {x-5},{y+7} {x-3},{y+2} {x-7},{y-2} {x-2},{y-2}" fill="{c}"/>'

    for mi, m in enumerate(models):
        c = colors[mi % len(colors)]
        pts = {p[1]: p for p in points if p[0] == m}
        order = [k for k in CONDS if k in pts]
        if len(order) > 1:
            s.append('<polyline fill="none" stroke="%s" stroke-opacity="0.35" points="%s"/>' % (
                c, " ".join(f"{X(pts[k][2])},{Y(pts[k][3])}" for k in order)))
        for k in order:
            s.append(mark(shapes[k], X(pts[k][2]), Y(pts[k][3]), c))
    ly = T + 5
    for mi, m in enumerate(models):
        s.append(f'<rect x="{L+pw+15}" y="{ly}" width="10" height="10" fill="{colors[mi % len(colors)]}"/><text x="{L+pw+30}" y="{ly+9}">{m.split(":",1)[1].removesuffix(":latest")}</text>')
        ly += 18
    ly += 10
    for k in CONDS:
        s.append(mark(shapes[k], L + pw + 20, ly + 5, "#444") + f'<text x="{L+pw+30}" y="{ly+9}">{k}</text>')
        ly += 18
    s.append("</svg>")
    # two-decimal coordinates: same picture, shorter file, no long digit runs
    out = re.sub(r"\d+\.\d{3,}", lambda m: f"{float(m.group()):.2f}", "\n".join(s))
    open(path, "w").write(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", nargs="+", default=sorted(glob.glob("data/items*.jsonl")))
    ap.add_argument("--raw", default="results/raw/*.jsonl")
    ap.add_argument("--out", default="results/analysis.json")
    ap.add_argument("--fig", default="figures/tradeoff.svg")
    a = ap.parse_args()
    items, V, quotes = load(a.items, a.raw)
    claims = sorted({it["claim_id"] for it in items.values()})
    gold0 = {it["claim_id"]: it["gold"] for it in items.values() if it["state"] == "E0"}
    res = {"direction": {}, "e4_leak": {}, "checker": {}, "paired": {}, "tradeoff": []}

    for m in sorted(V):
        for cond in CONDS:
            T = V[m].get(cond)
            if not T:
                continue
            for s in UNDEC + PARTIAL:
                vs = [v for (c, st), v in T.items() if st == s and v != "NOT_ENOUGH_INFO"]
                if vs:
                    res["direction"][f"{m}|{cond}|{s}"] = {"n_verdicts": len(vs),
                                                          "share_support": round(vs.count("SUPPORT") / len(vs), 3)}
            for s in PARTIAL:
                vs = [(v, gold0[c]) for (c, st), v in T.items() if st == s and v != "NOT_ENOUGH_INFO"]
                if vs:
                    res["e4_leak"][f"{m}|{cond}|{s}"] = {"n_verdicts": len(vs),
                                                         "match_hidden_gold": round(sum(v == g for v, g in vs) / len(vs), 3)}
            cs = claim_stats(V, m, cond, claims)
            if cs:
                res["tradeoff"].append([m, cond, sum(x[1] for x in cs.values()) / len(cs),
                                        sum(x[0] for x in cs.values()) / len(cs), len(cs)])
        base = claim_stats(V, m, "P0", claims)
        for cond in CONDS[1:]:
            cs = claim_stats(V, m, cond, claims)
            fv = bootstrap_diff({k: v[0] for k, v in base.items()}, {k: v[0] for k, v in cs.items()})
            ab = bootstrap_diff({k: float(v[1]) for k, v in base.items()}, {k: float(v[1]) for k, v in cs.items()})
            if fv:
                res["paired"][f"{m}|{cond}-P0"] = {"d_false_verdict": [round(x, 3) for x in fv[:3]],
                                                   "d_e0_false_abstain": [round(x, 3) for x in ab[:3]], "n_claims": fv[3]}
        # P2 checker: why verdicts were rejected
        reasons = defaultdict(lambda: defaultdict(int))
        for (mm, (c, st)), (v, q) in quotes.items():
            if mm != m or v == "NOT_ENOUGH_INFO":
                continue
            it = items[f"{c}-{st}"]
            if not q.strip():
                r = "no_quote"
            elif not P.check_in_evidence(q, it["evidence"]):
                r = "not_in_evidence"
            elif not P.check_not_restatement(q, it["claim"]):
                r = "restatement"
            elif not P.check_overlap(q, it["claim"]):
                r = "passes_P2_fails_overlap"
            else:
                r = "passes_all"
            reasons[st][r] += 1
        res["checker"][m] = {st: dict(v) for st, v in sorted(reasons.items())}

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(res, open(a.out, "w"), indent=1)
    os.makedirs(os.path.dirname(a.fig), exist_ok=True)
    svg_tradeoff([tuple(t[:4]) for t in res["tradeoff"]], a.fig)
    print(json.dumps(res["paired"], indent=1))
    print(json.dumps(res["checker"], indent=1))


if __name__ == "__main__":
    main()
