"""Run one model x protocols over the items; resumable (skips item/protocol pairs already in the output).

  python3 src/run.py --model ollama:gemma2:2b --protocols P0 P1 P2 --items data/items.jsonl \
      --out results/raw/<name>.jsonl [--limit N] [--states E0 E1 ...]
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
import backends  # noqa: E402
import protocols  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--protocols", nargs="+", default=["P0", "P1", "P2"])
    ap.add_argument("--items", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0, help="first N claims only")
    ap.add_argument("--states", nargs="*")
    a = ap.parse_args()

    items = [json.loads(l) for l in open(a.items)]
    if a.states:
        items = [it for it in items if it["state"] in a.states]
    if a.limit:
        keep = sorted({it["claim_id"] for it in items})[: a.limit]
        items = [it for it in items if it["claim_id"] in set(keep)]

    done = set()
    if os.path.exists(a.out):
        for l in open(a.out):
            r = json.loads(l)
            if r.get("error") is None:
                done.add((r["item_id"], r["protocol"]))
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    todo = [(it, p) for p in a.protocols for it in items if (it["item_id"], p) not in done]
    print(f"{a.model}: {len(todo)} calls to do ({len(done)} already done)", flush=True)
    t0, n_err = time.time(), 0
    with open(a.out, "a") as f:
        for k, (it, p) in enumerate(todo, 1):
            rec = {"model": a.model, "protocol": p, "item_id": it["item_id"], "state": it["state"],
                   "gold": it["gold"], "error": None}
            for attempt in range(4):  # the shared server can drop connections while it swaps models
                try:
                    text, info = backends.generate(a.model, protocols.SYSTEM,
                                                   protocols.prompt(p, it["claim"], it["evidence"]),
                                                   max_tokens=300 if p == "P2" else 30)
                    rec.update(raw=text, error=None, **info)
                    break
                except Exception as e:  # after the last attempt: recorded and retried on the next run
                    rec["error"] = f"{type(e).__name__}: {e}"[:300]
                    time.sleep(15 * (attempt + 1))
            if rec["error"]:
                n_err += 1
            f.write(json.dumps(rec) + "\n")
            f.flush()
            if k % 50 == 0 or k == len(todo):
                el = time.time() - t0
                print(f"  {k}/{len(todo)}  {el/k:.2f}s/call  errors={n_err}", flush=True)
    sys.exit(1 if n_err else 0)


if __name__ == "__main__":
    main()
