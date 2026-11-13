"""Held-out records: ID and phone formats the recognizers in app/mask.py were NOT written for.

Same layout as data/records/ (doc_XXX.txt + manifest.json), so detection_report.py can score it.
Never edit the generated docs to make them pass; change the recognizers instead.
"""
import json, random
from pathlib import Path
from faker import Faker

OUT = Path("data/holdout")
fake = Faker(); Faker.seed(2024); random.seed(2024)   # different seed from make_data.py
OUT.mkdir(parents=True, exist_ok=True)

# Each format returns (manifest value, text as written in the doc).
# For labelled formats the label stays in the text but not in the value,
# so "correct" means the identifier itself was detected.
CASE_FORMATS = [
    lambda y, n: (f"PRB {y} {n:06d}",) * 2,                   # PRB 2024 001234
    lambda y, n: (f"prb-{y}-{n:06d}",) * 2,                   # prb-2024-001234
    lambda y, n: (f"{y}-{n:06d}", f"Case #{y}-{n:06d}"),      # Case #2024-001234
]
BOOKING_FORMATS = [
    lambda n: (f"BK-{n:07d}",) * 2,                           # BK-1234567
    lambda n: (f"{n:07d}", f"Booking: {n:07d}"),              # Booking: 1234567
]
PHONE_FORMATS = [
    lambda a, l, x: f"({a}) 555 {l:04d}",                     # (213) 555 0199
    lambda a, l, x: f"{a}.555.{l:04d} ext. {x}",              # 213.555.0199 ext. 12
    lambda a, l, x: f"+1 {a} 555 {l:04d}",                    # +1 213 555 0199
]

# Same policy phrases as make_data.py, so the over-masking check still works.
TEMPLATES = [
    "File {case}. Client {name} ({booking}) must check in weekly. "
    "Contact: {phone}, {email}. Policy: missed check-ins are reported within 48 hours.",
    "Per {case}, {name} is assigned to the evening program. "
    "Reach them at {email} or {phone}. {booking}.",
    "HR note: {name} requested 3 days of leave. Employees get 10 sick days per year. "
    "Phone {phone}. Linked {case}, {booking}. Email {email}.",
]

manifest = []
for i in range(30):
    case_val, case_txt = CASE_FORMATS[i % 3](random.randint(2018, 2026), random.randint(0, 999999))
    book_val, book_txt = BOOKING_FORMATS[i % 2](random.randint(0, 9999999))
    phone = PHONE_FORMATS[(i // 3) % 3](random.randint(201, 989), random.randint(100, 199),
                                        random.randint(1, 99))
    pii = {"PERSON": fake.name(), "PHONE": phone, "EMAIL": fake.email(),
           "CASE_NUMBER": case_val, "BOOKING_ID": book_val}
    text = random.choice(TEMPLATES).format(name=pii["PERSON"], phone=phone, email=pii["EMAIL"],
                                           case=case_txt, booking=book_txt)
    assert all(v in text for v in pii.values()), (i, pii)
    fname = f"doc_{i:03}.txt"
    (OUT / fname).write_text(text, encoding="utf-8")
    manifest.append({"doc": fname, "pii": pii})

(OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(f"Wrote {len(manifest)} docs + manifest to {OUT}")
