import json, random
from pathlib import Path
from app.agent import prepare

def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))

def flatten(x):
    if isinstance(x, dict):
        for v in x.values(): yield from flatten(v)
    elif isinstance(x, list):
        for v in x: yield from flatten(v)
    elif isinstance(x, str):
        yield x

records = load("data/records/manifest.json")
policies = load("data/policies/manifest.json")
PLANTED = [v for d in records + policies for v in flatten(d["pii"])]
CASES = load("evals/cases.json")

# Questions where the USER types PII, a realistic risk
random.seed(0)
PII_QUESTIONS = []
for d in random.sample(records, 30):
    p = d["pii"]
    PII_QUESTIONS += [
        f"I'm {p['PERSON']}, how many sick days do I get?",
        f"Call me at {p['PHONE']} about my travel permit deadline.",
        f"For case {p['CASE_NUMBER']}, what is the drug test fee?",
        f"Email {p['EMAIL']} the records request fee.",
    ]
QUESTIONS = [c["question"] for c in CASES] + PII_QUESTIONS

def test_leak_rate():
    prompts = [prepare(q) for q in QUESTIONS]
    leaks = [(q, [v for v in PLANTED if v in p])
             for q, p in zip(QUESTIONS, prompts) if any(v in p for v in PLANTED)]
    rate = len(leaks) / len(prompts)
    print(f"\nLeak rate: {rate:.2%} ({len(leaks)}/{len(prompts)} prompts)")
    for q, vals in leaks[:10]:
        print("LEAK:", q, "->", vals)
    assert rate == 0
