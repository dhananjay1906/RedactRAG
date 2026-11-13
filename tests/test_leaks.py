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
CASES = load("evals/cases.json")

# Names in the staff directory get the deny-list; held-out names rely on NER alone.
STAFF = set(load("config/staff_directory.json"))
POLICY_NAMES = [d["pii"]["PERSON"] for d in policies if "PERSON" in d["pii"]]
KNOWN_NAMES = [n for n in POLICY_NAMES if n in STAFF]
HELD_OUT_NAMES = [n for n in POLICY_NAMES if n not in STAFF]

# Hard gate: every planted value except held-out names (measured separately below).
PLANTED = [v for d in records + policies for v in flatten(d["pii"]) if v not in HELD_OUT_NAMES]

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

def test_name_leak_rates():
    """Mask each policy doc and count which contact names survive."""
    from app.mask import mask
    masked = {d: mask(Path("data/policies", d).read_text(encoding="utf-8"))
              for d in {p["doc"] for p in policies}}
    all_text = "\n".join(masked.values())
    known_leaks = [n for n in KNOWN_NAMES if n in all_text]
    held_out_leaks = [n for n in HELD_OUT_NAMES if n in all_text]
    print(f"\nKnown staff (deny-list + NER): {len(known_leaks)}/{len(KNOWN_NAMES)} leaked "
          f"({len(known_leaks) / len(KNOWN_NAMES):.0%})")
    print(f"Unknown names (NER only):      {len(held_out_leaks)}/{len(HELD_OUT_NAMES)} leaked "
          f"({len(held_out_leaks) / len(HELD_OUT_NAMES):.0%})", held_out_leaks)
    assert not known_leaks
    # Held-out rate is reported, not asserted: it is the honest NER-only number.
