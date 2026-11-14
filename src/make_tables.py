"""Render the report's Tables 1-2 as HTML fragments from summary.json and analysis.json.

  python3 src/make_tables.py [--summary results/summary.json] [--analysis results/analysis.json]

Prints two <table> blocks; they are pasted into report/report.html between the
<!-- T1 --> / <!-- /T1 --> and <!-- T2 --> / <!-- /T2 --> markers with --write.
"""
import argparse
import json
import re

ORDER = ["llamacpp:gemma4-26b-a4b", "ollama:gemma2:9b", "ollama:qwen3.5:latest", "ollama:gemma2:2b"]
SHORT = {"llamacpp:gemma4-26b-a4b": "gemma4-26b-a4b", "ollama:gemma2:9b": "gemma2:9b",
         "ollama:qwen3.5:latest": "qwen3.5", "ollama:gemma2:2b": "gemma2:2b"}
CONDS = ["P0", "P1", "P2raw", "P2", "P2+overlap"]
UNDEC = ["E1", "E2", "E3", "E5"]


def f2(x):
    return f"{x:.2f}"


def table1(summary):
    cell = {(r["model"], r["condition"], r["state"]): r for r in summary}
    models = [m for m in ORDER if any(k[0] == m for k in cell)]
    out = ['<table>', '<tr><th>Model</th><th>Cond.</th>' + "".join(f'<th class="n">{s}</th>' for s in UNDEC)
           + '<th class="n">Mean [95% CI]</th><th class="n">E4</th><th class="n">E0 acc.</th>'
           '<th class="n">E0 false-abst.</th></tr>']
    for m in models:
        for c in CONDS:
            if (m, c, "E0") not in cell:
                continue
            fv = [cell[(m, c, s)]["false_verdict"][0] for s in UNDEC]
            k = sum(cell[(m, c, s)]["verdict"] for s in UNDEC)
            n = sum(cell[(m, c, s)]["n"] for s in UNDEC)
            # Wilson interval on the pooled 600 undecidable items
            z, p = 1.96, k / n
            d = 1 + z * z / n
            ctr = (p + z * z / (2 * n)) / d
            h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
            e0 = cell[(m, c, "E0")]
            e4 = cell.get((m, c, "E4"), {}).get("false_verdict", [float("nan")])[0]
            out.append(f'<tr><td>{SHORT[m]}</td><td>{c}</td>' + "".join(f'<td class="n">{f2(x)}</td>' for x in fv)
                       + f'<td class="n"><b>{f2(p)}</b> [{f2(max(0, ctr - h))}, {f2(min(1, ctr + h))}]</td>'
                       f'<td class="n">{f2(e4)}</td><td class="n">{f2(e0["accuracy"][0])}</td>'
                       f'<td class="n">{f2(e0["false_abstain"][0])}</td></tr>')
    out.append('</table>')
    return "\n".join(out)


def table2(analysis):
    P = analysis["paired"]
    out = ['<table>', '<tr><th>Model</th><th>Comparison</th><th class="n">&Delta; false-verdict rate [95% CI]</th>'
           '<th class="n">&Delta; E0 false-abstention [95% CI]</th></tr>']
    for m in ORDER:
        for c in CONDS[1:]:
            r = P.get(f"{m}|{c}-P0")
            if not r:
                continue
            a, b = r["d_false_verdict"], r["d_e0_false_abstain"]
            out.append(f'<tr><td>{SHORT[m]}</td><td>{c} &minus; P0</td>'
                       f'<td class="n">{a[0]:+.2f} [{a[1]:+.2f}, {a[2]:+.2f}]</td>'
                       f'<td class="n">{b[0]:+.2f} [{b[1]:+.2f}, {b[2]:+.2f}]</td></tr>')
    out.append('</table>')
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", default="results/summary.json")
    ap.add_argument("--analysis", default="results/analysis.json")
    ap.add_argument("--write", help="report HTML to update in place between the markers")
    a = ap.parse_args()
    t1 = table1(json.load(open(a.summary)))
    t2 = table2(json.load(open(a.analysis)))
    if not a.write:
        print(t1, t2, sep="\n\n")
        return
    html = open(a.write).read()
    for tag, body in (("T1", t1), ("T2", t2)):
        pat = re.compile(rf"<!-- {tag} -->.*?<!-- /{tag} -->", re.S)
        if len(pat.findall(html)) != 1:
            raise SystemExit(f"marker {tag} not found exactly once in {a.write}")
        html = pat.sub(lambda _: f"<!-- {tag} -->\n{body}\n<!-- /{tag} -->", html)
    open(a.write, "w").write(html)
    print(f"updated {a.write}")


if __name__ == "__main__":
    main()
