"""Build the evaluation items: one SciFact claim x six evidence states.

Written during the sprint (2026-11-13). Input: the SciFact release (data/claims_*.jsonl,
data/corpus.jsonl). Output: items.jsonl, one line per (claim, evidence state).

Evidence states
  E0  gold abstract (control; the claim is decidable)
  E1  retrieval returned nothing
  E2  retrieval returned an error string (404 / timeout / 503)
  E3  an on-topic but non-cited abstract (lexical nearest neighbour)
  E4  the gold abstract truncated just before the first rationale sentence
  E5  the "evidence" is the claim itself echoed back
Gold label is SUPPORT / REFUTE for E0 and NOT_ENOUGH_INFO for E1-E5.
"""
import argparse
import json
import math
import random
import re
from collections import Counter

ERRORS = [
    "HTTP 404 Not Found: the requested document could not be retrieved.",
    "Error: request timed out after 30 seconds while fetching the source.",
    "503 Service Unavailable: the source server is temporarily unable to handle the request.",
]
STOP = set("""a an the of in on and or to for with by from as at is are was were be been being that this
these those it its into than then there their which who whom whose not no can may might will would
should could does do did has have had our we they he she his her them via per vs""".split())


def toks(s):
    return [w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in STOP and len(w) > 1]


def load(path):
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]


def pick_gold(c):
    """Return (doc_id, label, rationale sentence ids) or None if not usable."""
    if not c["evidence"]:
        return None
    doc_id, sets = next(iter(c["evidence"].items()))
    labels = {s["label"] for s in sets}
    if len(labels) != 1:
        return None
    sent_ids = sorted({i for s in sets for i in s["sentences"]})
    return int(doc_id), labels.pop(), sent_ids


def abstract_text(doc, upto=None):
    sents = doc["abstract"] if upto is None else doc["abstract"][:upto]
    return doc["title"].strip() + ". " + " ".join(s.strip() for s in sents)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="SciFact data/ directory")
    ap.add_argument("--n-per-label", type=int, default=75)
    ap.add_argument("--min-rationale-index", type=int, default=2,
                    help="first rationale sentence must be at least this index, so E4 keeps some context")
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    corpus = {d["doc_id"]: d for d in load(a.data + "/corpus.jsonl")}
    claims = load(a.data + "/claims_train.jsonl") + load(a.data + "/claims_dev.jsonl")

    # TF-IDF over abstracts for the E3 neighbour.
    doc_toks = {i: Counter(toks(abstract_text(d))) for i, d in corpus.items()}
    df = Counter(w for c in doc_toks.values() for w in c)
    n_docs = len(corpus)
    idf = {w: math.log(n_docs / (1 + k)) for w, k in df.items()}

    def vec(counter):
        v = {w: tf * idf.get(w, 0.0) for w, tf in counter.items()}
        n = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {w: x / n for w, x in v.items()}

    doc_vecs = {i: vec(c) for i, c in doc_toks.items()}

    usable = {"SUPPORT": [], "CONTRADICT": []}
    for c in claims:
        g = pick_gold(c)
        if g is None or g[0] not in corpus:
            continue
        doc_id, label, sent_ids = g
        if sent_ids[0] < a.min_rationale_index:
            continue
        usable[label].append((c, doc_id, label, sent_ids))

    rng = random.Random(a.seed)
    chosen = []
    for label, rows in usable.items():
        rng.shuffle(rows)
        chosen += rows[: a.n_per_label]
    print({k: len(v) for k, v in usable.items()}, "-> chosen", len(chosen))

    out = open(a.out, "w")
    for c, doc_id, label, sent_ids in sorted(chosen, key=lambda r: r[0]["id"]):
        cid = c["id"]
        gold_doc = corpus[doc_id]
        excluded = {int(x) for x in c.get("cited_doc_ids", [])} | {int(x) for x in c["evidence"]}
        cv = vec(Counter(toks(c["claim"])))
        best, best_s = None, -1.0
        for i, dv in doc_vecs.items():
            if i in excluded:
                continue
            s = sum(x * dv.get(w, 0.0) for w, x in cv.items())
            if s > best_s:
                best, best_s = i, s
        states = {
            "E0": abstract_text(gold_doc),
            "E1": "",
            "E2": ERRORS[cid % len(ERRORS)],
            "E3": abstract_text(corpus[best]),
            "E4": abstract_text(gold_doc, upto=sent_ids[0]),
            "E5": c["claim"],
        }
        gold0 = "SUPPORT" if label == "SUPPORT" else "REFUTE"
        for st, ev in states.items():
            out.write(json.dumps({
                "item_id": f"{cid}-{st}", "claim_id": cid, "state": st, "claim": c["claim"],
                "evidence": ev, "gold": gold0 if st == "E0" else "NOT_ENOUGH_INFO",
                "meta": {"gold_doc": doc_id, "rationale_sents": sent_ids,
                         "e3_doc": best, "e3_cos": round(best_s, 3)},
            }) + "\n")
    out.close()


if __name__ == "__main__":
    main()
