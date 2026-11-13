import json, random
from pathlib import Path
from faker import Faker

fake = Faker(); Faker.seed(42); random.seed(42)
Path("data/records").mkdir(parents=True, exist_ok=True)

TEMPLATES = [
    "Case {case}. Client {name} (booking {booking}) must check in weekly. "
    "Contact: {phone}, {email}. Policy: missed check-ins are reported within 48 hours.",
    "Per docket {case}, {name} is assigned to the evening program. "
    "Reach them at {email} or {phone}. Booking ref {booking}.",
    "HR note: {name} requested 3 days of leave. Employees get 10 sick days per year. "
    "Phone {phone}. Linked file {case}, booking {booking}. Email {email}.",
]

manifest = []
for i in range(100):
    pii = {
        "PERSON": fake.name(),
        "PHONE": fake.phone_number(),
        "EMAIL": fake.email(),
        "CASE_NUMBER": f"PRB-{random.randint(2018, 2026)}-{random.randint(0, 999999):06d}",
        "BOOKING_ID": f"BK{random.randint(0, 9999999):07d}",
    }
    text = random.choice(TEMPLATES).format(
        name=pii["PERSON"], phone=pii["PHONE"], email=pii["EMAIL"],
        case=pii["CASE_NUMBER"], booking=pii["BOOKING_ID"])
    fname = f"doc_{i:03}.txt"
    Path("data/records", fname).write_text(text, encoding="utf-8")
    manifest.append({"doc": fname, "pii": pii})

Path("data/records/manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print("Wrote 100 docs + manifest")
