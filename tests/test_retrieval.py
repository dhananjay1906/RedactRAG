import json
from pathlib import Path
from app.search import search

CASES = json.loads(Path("evals/cases.json").read_text(encoding="utf-8"))

def test_retrieval_hit_rate():
    hit1 = hit3 = 0
    misses = []
    for c in CASES:
        docs = [r["doc"] for r in search(c["question"], k=3)]
        hit1 += docs[0] == c["expected_doc"]
        hit3 += c["expected_doc"] in docs
        if c["expected_doc"] not in docs:
            misses.append((c["question"], docs))
    n = len(CASES)
    print(f"\nhit@1: {hit1}/{n}  hit@3: {hit3}/{n}")
    for m in misses: print("MISS:", m)
    assert hit3 / n >= 0.85
