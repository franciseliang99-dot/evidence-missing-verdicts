"""E4b: a stricter 'truncated' state, added during the sprint after auditing E4.

The E4 audit (notes/audit_e4.md) found that the kept title often states the paper's finding,
so E4 was frequently decidable. E4b drops the title and keeps only the abstract sentences
before the first rationale sentence. It is written to its own items file so the main runs are
not disturbed; run.py and score.py take it like any other items file.

  python3 src/build_e4b.py --corpus _download/data/corpus.jsonl --items data/items.jsonl --out data/items_e4b.jsonl
"""
import argparse
import json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--items", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    corpus = {}
    for l in open(a.corpus):
        d = json.loads(l)
        corpus[d["doc_id"]] = d
    n = 0
    with open(a.out, "w") as f:
        for l in open(a.items):
            it = json.loads(l)
            if it["state"] != "E4":
                continue
            doc = corpus[it["meta"]["gold_doc"]]
            first = it["meta"]["rationale_sents"][0]
            ev = " ".join(s.strip() for s in doc["abstract"][:first])
            row = dict(it, item_id=f'{it["claim_id"]}-E4b', state="E4b", evidence=ev)
            f.write(json.dumps(row) + "\n")
            n += 1
    print(f"wrote {n} E4b items")


if __name__ == "__main__":
    main()
