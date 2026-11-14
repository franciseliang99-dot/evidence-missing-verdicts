"""The three verification protocols and the deterministic P2 checker. Written during the sprint.

P0  plain three-way verification prompt
P1  P0 + an explicit licence to abstain, naming the failure modes
P2  structured: the model must copy the exact sentence it relies on; a deterministic checker
    downgrades the verdict to NOT_ENOUGH_INFO unless the quote really is in the evidence and
    is not just the claim restated. The checker has variants (see CHECKS) that are applied
    offline to the same model outputs, so they cost no extra model calls.
"""
import json
import re

LABELS = ("SUPPORT", "REFUTE", "NOT_ENOUGH_INFO")

SYSTEM = "You are a careful fact-checking assistant in an automated verification pipeline."


def _evidence_block(ev):
    return ev if ev.strip() else "(no documents retrieved)"


def prompt(protocol, claim, evidence):
    head = f"Claim: {claim}\n\nRetrieved evidence:\n<<<\n{_evidence_block(evidence)}\n>>>\n\n"
    if protocol == "P0":
        return head + ("Based on the retrieved evidence, is the claim SUPPORT, REFUTE, or NOT_ENOUGH_INFO?\n"
                       "Answer with exactly one label.")
    if protocol == "P1":
        return head + ("Based only on the retrieved evidence, is the claim SUPPORT, REFUTE, or NOT_ENOUGH_INFO?\n"
                       "Answer NOT_ENOUGH_INFO whenever the evidence is missing, is an error message, is about "
                       "something else, stops before the relevant finding, or merely repeats the claim. "
                       "Do not use your own background knowledge. Saying NOT_ENOUGH_INFO is always better than guessing.\n"
                       "Answer with exactly one label.")
    if protocol == "P2":
        return head + ("Based only on the retrieved evidence, decide SUPPORT, REFUTE, or NOT_ENOUGH_INFO.\n"
                       "If you answer SUPPORT or REFUTE you must copy, word for word, the single sentence from the "
                       "retrieved evidence that decides it. A program will check that the sentence really appears in "
                       "the evidence; if it does not, your verdict is discarded.\n"
                       'Reply with JSON only: {"quote": "<exact sentence or empty>", "verdict": "<label>"}')
    raise ValueError(protocol)


def parse_label(text):
    """First label mentioned. Returns None when no label is found (counted as unparsed)."""
    t = text.upper().replace("NOT ENOUGH INFO", "NOT_ENOUGH_INFO").replace("REFUTES", "REFUTE")
    hits = [(t.find(l), l) for l in LABELS if l in t]
    hits = [h for h in hits if h[0] >= 0]
    if not hits:
        if "SUPPORTED" in t:
            return "SUPPORT"
        if "REFUTED" in t or "CONTRADICT" in t:
            return "REFUTE"
        return None
    # "NOT_ENOUGH_INFO" contains no other label as substring, but "SUPPORT" may appear inside prose;
    # take the earliest.
    return min(hits)[1]


def parse_p2(text):
    """Returns (verdict or None, quote or "")."""
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        try:
            d = json.loads(m.group(0))
            v = parse_label(str(d.get("verdict", "")))
            return v, str(d.get("quote", "") or "")
        except (json.JSONDecodeError, AttributeError):
            pass
    return parse_label(text), ""


def _norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s%.,-]", " ", s.lower())).strip(" .")


def _words(s):
    return set(re.findall(r"[a-z0-9]+", s.lower()))


def check_in_evidence(quote, evidence, min_chars=20):
    q = _norm(quote)
    return len(q) >= min_chars and q in _norm(evidence)


def check_not_restatement(quote, claim, max_jaccard=0.7):
    a, b = _words(quote), _words(claim)
    if not a:
        return False
    return len(a & b) / len(a | b) < max_jaccard


def check_overlap(quote, claim, min_shared=2):
    stop = {"the", "of", "and", "in", "a", "an", "to", "is", "are", "with", "for", "on", "by", "that"}
    return len((_words(quote) & _words(claim)) - stop) >= min_shared


# Checker variants applied offline to P2 outputs.
CHECKS = {
    "P2raw": lambda v, q, it: v,  # model's own verdict, no checker
    "P2": lambda v, q, it: v if v == "NOT_ENOUGH_INFO" or (
        check_in_evidence(q, it["evidence"]) and check_not_restatement(q, it["claim"])) else "NOT_ENOUGH_INFO",
    "P2+overlap": lambda v, q, it: v if v == "NOT_ENOUGH_INFO" or (
        check_in_evidence(q, it["evidence"]) and check_not_restatement(q, it["claim"])
        and check_overlap(q, it["claim"])) else "NOT_ENOUGH_INFO",
}
