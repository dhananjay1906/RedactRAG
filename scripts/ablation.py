"""Cost-of-privacy ablation: accuracy with masking on vs. off.

Needs both tables:  python -m app.ingest  and  python -m app.ingest --raw
Run:                python -m scripts.ablation        (2 Claude calls per eval case)
All data is synthetic, so sending the raw version to Claude is safe here.
"""
from app.agent import ask
from tests.test_accuracy import CASES, has   # same cases and pass rule as the accuracy test

def passed(case, r) -> bool:
    return (case["expected_doc"] in r.get("citations", [])
            and all(has(r["answer"], i) for i in case["must_include"]))

def main():
    rows = []
    for c in CASES:
        m = ask(c["question"], masked=True)
        r = ask(c["question"], masked=False)
        rows.append((c, m, r, passed(c, m), passed(c, r)))
    n = len(rows)
    print(f"Masked accuracy: {sum(x[3] for x in rows)}/{n}")
    print(f"Raw accuracy:    {sum(x[4] for x in rows)}/{n}")
    diffs = [x for x in rows if x[3] != x[4]]
    print(f"Questions where they differ: {len(diffs)}")
    for c, m, r, pm, pr in diffs:
        print(f"\nQ: {c['question']}  (expected {c['expected_doc']}, must include {c['must_include']})")
        print(f"  MASKED [{'pass' if pm else 'FAIL'}] {m['citations']}: {m['answer']}")
        print(f"  RAW    [{'pass' if pr else 'FAIL'}] {r['citations']}: {r['answer']}")

if __name__ == "__main__":
    main()
