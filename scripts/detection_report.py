import json, re, sys
from collections import Counter
from pathlib import Path
from app.mask import analyze, mask

custom = "--no-custom" not in sys.argv
folder = sys.argv[sys.argv.index("--dir") + 1] if "--dir" in sys.argv else "data/records"
LABEL = {"PERSON": "PERSON", "PHONE": "PHONE_NUMBER", "EMAIL": "EMAIL_ADDRESS",
         "CASE_NUMBER": "CASE_NUMBER", "BOOKING_ID": "BOOKING_ID"}
KEEP = ["10 sick days", "48 hours", "weekly", "3 days", "evening program"]

def fragments(typ, val):
    frags = [val]
    long_digits = re.findall(r"\d{4,}", val)
    if long_digits: frags.append(max(long_digits, key=len))  # e.g. "0199"
    if typ == "CASE_NUMBER": frags.append("PRB-")
    if typ == "BOOKING_ID": frags.append(val[2:])
    return frags

manifest = json.loads(Path(folder, "manifest.json").read_text(encoding="utf-8"))
correct, leaked, total, overmask, missed_phones = Counter(), Counter(), Counter(), 0, []

for d in manifest:
    text = Path(folder, d["doc"]).read_text(encoding="utf-8")
    results = analyze(text, custom)
    masked = mask(text, custom)
    for typ, val in d["pii"].items():
        total[typ] += 1
        s = text.find(val); e = s + len(val)
        if any(r.entity_type == LABEL[typ] and r.start <= s and r.end >= e for r in results):
            correct[typ] += 1
        elif typ == "PHONE":
            missed_phones.append(val)
        if any(f in masked for f in fragments(typ, val)):
            leaked[typ] += 1
    overmask += sum(1 for k in KEEP if k in text and k not in masked)

print("Custom:", custom)
print(f"{'TYPE':12} {'CORRECT':>8} {'LEAKED':>7}")
for t in total:
    print(f"{t:12} {correct[t]:>5}/{total[t]} {leaked[t]:>7}")
print("Over-masked policy phrases:", overmask)
print("Missed phone formats:", missed_phones[:10])