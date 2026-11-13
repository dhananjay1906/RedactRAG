import json, pytest
from pathlib import Path
from app.agent import ask

CASES = json.loads(Path("evals/cases.json").read_text(encoding="utf-8"))

def has(answer, item):
    options = item if isinstance(item, list) else [item]
    return any(o.lower() in answer.lower() for o in options)

@pytest.mark.llm
@pytest.mark.parametrize("case", CASES, ids=[c["question"][:40] for c in CASES])
def test_answer(case):
    r = ask(case["question"])
    assert case["expected_doc"] in r["citations"], r["answer"]
    assert all(has(r["answer"], i) for i in case["must_include"]), r["answer"]
