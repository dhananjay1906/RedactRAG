"""Second held-out set: name, phone and ID formats not used in data/records/ or data/holdout/.

Same layout as data/records/ (doc_XXX.txt + manifest.json), so detection_report.py can score it.
Never edit the generated docs to make them pass; change the recognizers instead.
"""
import json, random
from pathlib import Path
from faker import Faker

OUT = Path("data/holdout2")
SEED = 7319                     # different from make_data.py (42) and make_holdout.py (2024)
fake = Faker(); Faker.seed(SEED); random.seed(SEED)
OUT.mkdir(parents=True, exist_ok=True)
N = 30

# Each format returns (manifest value, text as written in the doc).
# For labelled formats the label stays in the text but not in the value.
CASE_FORMATS = [
    lambda y, n: (f"PRB/{y}/{n:06d}",) * 2,                          # PRB/2024/001234
    lambda y, n: (f"PRB-{y % 100:02d}-{n:06d}",) * 2,                 # PRB-24-001234
    lambda y, n: (f"{y % 100:02d}-PRB-{n:06d}",
                  f"Case No. {y % 100:02d}-PRB-{n:06d}"),             # Case No. 24-PRB-001234
    lambda y, n: (f"PRB{y}{n:06d}", f"Docket No. PRB{y}{n:06d}"),    # Docket No. PRB2024001234
]
BOOKING_FORMATS = [
    lambda n: (f"BK {n:07d}",) * 2,                                   # BK 1234567
    lambda n: (f"bk-{n:07d}",) * 2,                                   # bk-1234567
    lambda n: (f"{n:07d}", f"Booking No. {n:07d}"),                   # Booking No. 1234567
    lambda n: (f"BK#{n:07d}",) * 2,                                   # BK#1234567
]
PHONE_FORMATS = [
    lambda a, l, x: f"({a}) 555-{l:04d}",                             # (415) 555-0123
    lambda a, l, x: f"1-{a}-555-{l:04d}",                             # 1-415-555-0123
    lambda a, l, x: f"+1 ({a}) 555-{l:04d}",                          # +1 (415) 555-0123
    lambda a, l, x: f"{a}-555-{l:04d} ext. {x}",                      # 415-555-0123 ext. 204
]

# Name styles. Each returns (manifest value, text as written in the doc).
FIRST = ["Grace", "Daniel", "Priya", "Thomas", "Laura", "Marcus", "Hannah", "Samuel", "Nadia", "Owen"]
NAME_STYLES = [
    # accented
    lambda: (random.choice(["José Hernández", "Zoë Lefèvre", "Renée Côté", "Björn Åkesson",
                            "Inés Muñoz", "François Gagné", "Chloé Bérubé", "Dagný Jónsdóttir"]),) * 2,
    # apostrophe
    lambda: (f"{random.choice(FIRST)} {random.choice(['O\'Neill', 'O\'Brien', 'D\'Angelo', 'O\'Connor', 'D\'Souza', 'O\'Hara'])}",) * 2,
    # surname particle
    lambda: (random.choice(["Pieter van der Berg", "María de la Cruz", "Luca De Rosa", "Anna von Bülow",
                            "Ahmed bin Rashid", "Carlos de los Santos", "Emma van Dijk", "Jean-Luc Le Gall"]),) * 2,
    # hyphenated surname
    lambda: (f"{random.choice(FIRST)} {random.choice(['Kowalski-Brandt', 'Smith-Jones', 'Garcia-Lopez', 'Martin-Hughes', 'Nguyen-Reyes', 'Fischer-Owens'])}",) * 2,
    # middle initial
    lambda: (f"{fake.first_name()} {random.choice('ABCDEHJKLMRST')}. {fake.last_name()}",) * 2,
    # honorific in text, not in value
    lambda: random.choice([
        lambda: (lambda nm: (nm, f"Mr. {nm}"))(f"{fake.first_name_male()} {fake.last_name()}"),
        lambda: (lambda nm: (nm, f"{random.choice(['Ms.', 'Mrs.'])} {nm}"))(
            f"{fake.first_name_female()} {fake.last_name()}"),
        lambda: (lambda nm: (nm, f"Dr. {nm}"))(f"{fake.first_name()} {fake.last_name()}"),
    ])(),
]

# Same policy phrases as make_data.py, so the over-masking check still works.
# Case/booking placeholders carry their own label when the format has one.
TEMPLATES = [
    "Reference {case}. Client {name} ({booking}) must check in weekly. "
    "Contact: {phone}, {email}. Policy: missed check-ins are reported within 48 hours.",
    "Under {case}, {name} has been assigned to the evening program. "
    "Reach them at {email} or {phone}. Intake record {booking}.",
    "HR note: {name} asked for 3 days of leave. Staff get 10 sick days per year. "
    "Phone {phone}. Linked matter {case}, {booking}. Email {email}.",
]


def balanced(k):
    """N indices into a list of k formats, spread evenly, in random order."""
    idx = [i % k for i in range(N)]
    random.shuffle(idx)
    return idx


case_idx, book_idx = balanced(len(CASE_FORMATS)), balanced(len(BOOKING_FORMATS))
phone_idx, name_idx = balanced(len(PHONE_FORMATS)), balanced(len(NAME_STYLES))
tmpl_idx = balanced(len(TEMPLATES))

manifest = []
for i in range(N):
    case_val, case_txt = CASE_FORMATS[case_idx[i]](random.randint(2018, 2026), random.randint(0, 999999))
    book_val, book_txt = BOOKING_FORMATS[book_idx[i]](random.randint(0, 9999999))
    phone = PHONE_FORMATS[phone_idx[i]](random.randint(201, 989), random.randint(100, 199),
                                        random.randint(2, 999))
    name_val, name_txt = NAME_STYLES[name_idx[i]]()
    pii = {"PERSON": name_val, "PHONE": phone, "EMAIL": fake.email(),
           "CASE_NUMBER": case_val, "BOOKING_ID": book_val}
    text = TEMPLATES[tmpl_idx[i]].format(name=name_txt, phone=phone, email=pii["EMAIL"],
                                         case=case_txt, booking=book_txt)
    assert all(isinstance(v, str) and v in text for v in pii.values()), (i, pii)
    fname = f"doc_{i:03}.txt"
    (OUT / fname).write_text(text, encoding="utf-8")
    manifest.append({"doc": fname, "pii": pii})

(OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Wrote {len(manifest)} docs + manifest to {OUT}")
