# Notes

## Results (2026-11-12)

Model: `claude-haiku-5-5`. Embeddings: `all-MiniLM-L6-v2` (384-dim). 10 policy docs, 179 chunks.
Chunking: split on `##` sections, then 500 chars with 100 overlap inside each section; every chunk
starts with `<doc title> > <section heading>`. 28 eval questions in `evals/cases.json`.

### PII detection, base vs. custom recognizers (`scripts/detection_report.py`, 100 synthetic records)

| Type        | Base correct | Base leaked | Custom correct | Custom leaked |
|-------------|--------------|-------------|----------------|---------------|
| PERSON      | 100/100      | 0           | 100/100        | 0             |
| PHONE       | 82/100       | 18          | 100/100        | 0             |
| EMAIL       | 100/100      | 0           | 100/100        | 0             |
| CASE_NUMBER | 0/100        | 100         | 100/100        | 0             |
| BOOKING_ID  | 0/100        | 98          | 100/100        | 0             |

Over-masked policy phrases: 0 in both. Base missed phones with extensions (e.g. `394.802.6542x351`).

### DB leak count

`SELECT count(*) FROM chunks WHERE content ~ 'PRB-|@|BK[0-9]{7}'`: 14 before the email fix, **0** after.

### Retrieval (`tests/test_retrieval.py`)

| Metric | Fixed 500-char chunks | Section-aware chunks |
|--------|-----------------------|----------------------|
| hit@1  | 27/28 (96%)           | 27/28 (96%)          |
| hit@3  | 27/28 (96%)           | **28/28 (100%)**     |

Old miss: "What is the maximum number of hours per week an employee may work in approved outside employment?"
With fixed chunks the expected `code-of-conduct.md` chunk was not in the top 8: the answer sentence
never says "outside employment", only the `## Outside Employment` heading does, and the 500-char window
cut the heading off. With the heading on every chunk it ranks 3rd (behind `remote-work.md` and
`leave-and-sick-time.md`), so it is a hit@3 but still not a hit@1.

### End-to-end leak rate (`tests/test_leaks.py`, 148 prompts, no API calls)

**0.00% (0/148).** Was 20.95% (31/148) before the fix. All leaks were 2 policy contact names that spaCy NER did not tag as PERSON:
`Wilhelmina Strathcona-Ibe` (records-requests.md) and `Lucía Fernández-Hobart` (check-in-and-reporting.md).
Before the fix, policy manifest: PERSON 2/21 left in DB; PHONE, EMAIL, CASE_NUMBER 0. All 120 user-typed PII questions masked.
Held-out names are excluded from this gate and measured below.

### Contact-name leak rate (`test_name_leak_rates`, every policy doc masked)

The deny-list loads `config/staff_directory.json` (stand-in for the HR directory), never the test manifest.
2 extra policy docs (`community-service.md`, `victim-notification.md`) add 6 contact names that are NOT in that file.

| Names | Protection | Leaked |
|-------|------------|--------|
| Known staff (21) | deny-list + NER | **0/21 (0%)** |
| Unknown names (6, held out) | NER only | **2/6 (33%)** |

Leaked held-out names: `Benedikt Harrowgate-Mensah`, `Aurelia Mbeki-Lindgren`.
For comparison, NER alone on the 21 known names missed 2/21 (10%). Small samples; the honest
NER-only miss rate on names like these is somewhere in that range, not 0.

### Accuracy (`tests/test_accuracy.py`, 28 Haiku calls)

**28/28** with section-aware chunks. Was 27/28 with fixed chunks: the only failure was the retrieval
miss above, and the agent answered "I don't know" instead of guessing.

## Bugs found

- Found: Presidio skipped non-standard email domains; fixed with a custom recognizer.
- Found: spaCy NER misses some names in "Contacts" bullet lists (2/21 policy contacts). Fixed with a staff-name deny-list recognizer.
- Found: the first deny-list loaded names from the leak test's own manifest, so the 0% was guaranteed.
  Moved the list to `config/staff_directory.json` and added 6 held-out names to measure NER alone.
- Found: `.gitignore` excluded all of `data/`, so a fresh clone had no policy corpus. Now only `data/records/` is ignored.
- Found: fixed-size chunks separated answers from their section headings. Chunking by `##` section
  and prefixing the heading took hit@3 from 27/28 to 28/28 and accuracy from 27/28 to 28/28.
