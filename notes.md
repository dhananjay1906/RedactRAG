# Notes

## Retrieval eval (2026-11-12)

`pytest tests/test_retrieval.py -s`. 28 questions from `evals/cases.json`, 8 policy docs, 116 chunks.
Embeddings: `all-MiniLM-L6-v2` (384-dim). Chunks: 500 chars, 100 overlap. Cosine distance in pgvector.

| Metric | Score |
|--------|-------|
| hit@1  | 27/28 (96%) |
| hit@3  | 27/28 (96%) |

Miss: "What is the maximum number of hours per week an employee may work in approved outside employment?"
Expected `code-of-conduct.md`; top 3 were `remote-work.md`, `remote-work.md`, `leave-and-sick-time.md`.
The expected chunk is not in the top 8.

## Bugs found

- Found: Presidio skipped non-standard email domains; fixed with a custom recognizer.
