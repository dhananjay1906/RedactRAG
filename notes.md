# Notes

## Results (2026-11-12)

Model: `claude-haiku-5-5`. Embeddings: `all-MiniLM-L6-v2` (384-dim). 10 policy docs, 179 chunks.
Chunking: split on `##` sections, then 500 chars with 100 overlap inside each section; every chunk
starts with `<doc title> > <section heading>`. 32 eval questions in `evals/cases.json`
(28 on the original 8 docs, 4 on the 2 held-out docs).

### PII detection, base vs. custom recognizers (`scripts/detection_report.py`, 100 synthetic records)

| Type        | Base correct | Base leaked | Custom correct | Custom leaked |
|-------------|--------------|-------------|----------------|---------------|
| PERSON      | 100/100      | 0           | 100/100        | 0             |
| PHONE       | 82/100       | 18          | 100/100        | 0             |
| EMAIL       | 100/100      | 0           | 100/100        | 0             |
| CASE_NUMBER | 0/100        | 100         | 100/100        | 0             |
| BOOKING_ID  | 0/100        | 98          | 100/100        | 0             |

Over-masked policy phrases: 0 in both. Base missed phones with extensions (e.g. `394.802.6542x351`).

### Held-out ID formats (`scripts/make_holdout.py`, 30 docs, custom recognizers unchanged)

`python -m scripts.detection_report --dir data/holdout`. Formats the regexes were not written for;
names and emails use the usual formats as a control.

| Type        | Correct (right label, full span) | Digits leaked |
|-------------|----------------------------------|---------------|
| PERSON      | 30/30                            | 0             |
| PHONE       | 30/30                            | 0             |
| EMAIL       | 30/30                            | 0             |
| CASE_NUMBER | **10/30**                        | 0             |
| BOOKING_ID  | **0/30**                         | **28/30**     |

By format:

| Format | Correct | Digits leaked | Notes |
|--------|---------|---------------|-------|
| `prb-2024-001234` | 10/10 | 0/10 | Presidio regexes are case-insensitive by default |
| `PRB 2024 001234` | 0/10 | 0/10 | hidden only by luck: 10 digits match the phone regex |
| `Case #2024-001234` | 0/10 | 0/10 | same luck: masked as `PHONE_NUMBER` |
| `BK-1234567` | 0/15 | 13/15 | |
| `Booking: 1234567` | 0/15 | 15/15 | |
| `(213) 555 0199`, `213.555.0199 ext. 12`, `+1 213 555 0199` | 30/30 | 0/30 | phone regex already covered these |

Takeaway: the in-distribution 100/100 for CASE_NUMBER and BOOKING_ID does not carry over to new formats.
Case numbers only look safe because the phone rule over-matches; booking IDs leak almost every time.

**After widening the recognizers** (`app/mask.py`; held-out docs untouched):

| Type        | Before: correct / leaked | After: correct / leaked |
|-------------|--------------------------|-------------------------|
| CASE_NUMBER | 10/30 / 0                | **30/30 / 0**           |
| BOOKING_ID  | 0/30 / 28                | **30/30 / 0**           |

Changes: `PRB` and `BK` accept `-`, a space or nothing after the prefix; a bare `YYYY-NNNNNN` or
7-digit number counts only right after a label (`Case #`, `case`, `docket`, `Booking:`, `booking`),
via lookbehinds so the label is not masked. A bare 7-digit number with no label is still left alone.
`data/records` stays 100/100 with 0 leaks, over-masked policy phrases 0, and every other metric is unchanged.

Caveat: these 30 docs were used to pick the fix, so they are now a dev set, not a held-out set.
30/30 shows the fix works on these formats, not that it generalises. An honest generalisation number
needs a fresh set of formats (e.g. `Case No. 2024/001234`, `Booking ID 1234567`) scored before any tuning.

### DB leak count

`SELECT count(*) FROM chunks WHERE content ~ 'PRB-|@|BK[0-9]{7}'`: 14 before the email fix, **0** after.

### Retrieval (`tests/test_retrieval.py`)

| Metric | Fixed 500-char chunks (28 q) | Section-aware chunks (28 q) | Section-aware (32 q) |
|--------|------------------------------|-----------------------------|----------------------|
| hit@1  | 27/28 (96%)                  | 27/28 (96%)                 | 31/32 (97%)          |
| hit@3  | 27/28 (96%)                  | **28/28 (100%)**            | **32/32 (100%)**     |

Old miss: "What is the maximum number of hours per week an employee may work in approved outside employment?"
With fixed chunks the expected `code-of-conduct.md` chunk was not in the top 8: the answer sentence
never says "outside employment", only the `## Outside Employment` heading does, and the 500-char window
cut the heading off. With the heading on every chunk it ranks 3rd (behind `remote-work.md` and
`leave-and-sick-time.md`), so it is a hit@3 but still not a hit@1.

### End-to-end leak rate (`tests/test_leaks.py`, 182 prompts, no API calls)

Prompts: 32 eval questions + 120 questions with user-typed PII + 30 "who do I contact" questions
(3 phrasings x 10 docs). Fact questions never retrieve a "Contacts" section, so without the contact
questions the unknown-name rate read 0/152 while 3 names sat unmasked in the DB.

| Prompt-level check | Leak rate |
|--------------------|-----------|
| Known PII (records, known staff, phones, emails, case numbers) | **0.00% (0/182)** |
| Unknown names (NER only) | **1.65% (3/182)** |

All 3 unknown-name leaks come from "who is the contact" questions about `community-service.md`
and `victim-notification.md`.

History: before the deny-list the known-PII rate was 20.95% (31/148), from 2 contact names NER missed
(`Wilhelmina Strathcona-Ibe`, `Lucía Fernández-Hobart`).

### Contact-name leak rate (`test_name_leak_rates`, every policy doc masked)

The deny-list loads `config/staff_directory.json` (stand-in for the HR directory), never the test manifest.
2 extra policy docs (`community-service.md`, `victim-notification.md`) add 6 contact names that are NOT
in that file, in mixed styles: 2 hyphenated, 2 accented, 2 single-word surnames.

| Names | Protection | Leaked |
|-------|------------|--------|
| Known staff (21) | deny-list + NER | **0/21 (0%)** |
| Unknown names (6, held out) | NER only | **3/6 (50%)** |

Leaked: `Benedikt Harrowgate-Mensah` (hyphenated), `Aurelia Mbeki-Lindgren` (hyphenated),
`Radomír Eszterházy` (accented). Caught: `Søren Ångström` (accented), `Cornelius Afolabi`,
`Philippa Nakamura` (single-word surnames). With all-hyphenated held-out names the rate was 2/6.
NER alone on the 21 known names missed 2/21 (10%). Small samples; NER is not enough on its own.

### Accuracy (`tests/test_accuracy.py`, Haiku calls)

**32/32** with section-aware chunks (28 original + 4 held-out-doc questions). Was 27/28 with fixed
chunks: the only failure was the retrieval miss above, and the agent answered "I don't know"
instead of guessing.

## Bugs found

- Found: Presidio skipped non-standard email domains; fixed with a custom recognizer.
- Found: spaCy NER misses some names in "Contacts" bullet lists (2/21 policy contacts). Fixed with a staff-name deny-list recognizer.
- Found: the first deny-list loaded names from the leak test's own manifest, so the 0% was guaranteed.
  Moved the list to `config/staff_directory.json` and added 6 held-out names to measure NER alone.
- Found: `.gitignore` excluded all of `data/`, so a fresh clone had no policy corpus. Now only `data/records/` is ignored.
- Found: fixed-size chunks separated answers from their section headings. Chunking by `##` section
  and prefixing the heading took hit@3 from 27/28 to 28/28 and accuracy from 27/28 to 28/28.
- Found: the prompt-level leak test never asked for contacts, so it could not see unmasked names
  in "Contacts" sections. Added 30 contact questions; unknown-name prompt leaks went from 0/152 to 3/182.
