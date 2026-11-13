import hashlib
import re
import sys
from pathlib import Path
import psycopg
from pgvector.psycopg import register_vector
from pypdf import PdfReader
from app.mask import mask
from app.search import model, DB_URL, MASKED_TABLE, RAW_TABLE

SOURCE_DIRS = [Path("data/policies"), Path("docs")]

_SENT_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9<(\"'])")
_ABBREV = ("e.g.", "i.e.", "a.m.", "p.m.", "No.", "Dr.", "Mr.", "Ms.", "Mrs.", "St.")

def units(text: str) -> list[tuple[str, str]]:
    """Split into (sentence, separator). Each line is split into sentences; separator is
    ' ' between sentences on one line and '\\n' at a line end, so bullets stay intact."""
    out = []
    for line in (l.strip() for l in text.split("\n")):
        if not line:
            continue
        parts = []
        for p in _SENT_END.split(line):
            if parts and parts[-1].endswith(_ABBREV):   # "Dr. <PERSON>" is one sentence
                parts[-1] += " " + p
            else:
                parts.append(p)
        out += [(p, " ") for p in parts[:-1]] + [(parts[-1], "\n")]
    return out

def _join(us: list[tuple[str, str]]) -> str:
    return "".join(t + sep for t, sep in us).strip()

def chunk(text: str, size: int = 500, min_tail: int = 100) -> list[str]:
    """Pack whole sentences up to ~size chars, overlap one sentence, fold a short tail back."""
    chunks: list[list[tuple[str, str]]] = []
    cur: list[tuple[str, str]] = []
    for u in units(text):
        if not cur or len(_join(cur + [u])) <= size:
            cur.append(u)
            continue
        only_overlap = bool(chunks) and len(cur) == 1 and cur[0] == chunks[-1][-1]
        if not only_overlap:
            chunks.append(cur)
            cur = [cur[-1], u]                           # one-sentence overlap
        else:
            cur = [u]                                    # overlap + u won't fit: start fresh
    if cur and not (chunks and len(cur) == 1 and cur[0] == chunks[-1][-1]):
        chunks.append(cur)
    if len(chunks) > 1 and len(_join(chunks[-1])) < min_tail:
        tail = chunks.pop()
        chunks[-1] += tail[1:] if tail[0] == chunks[-1][-1] else tail   # skip repeated overlap
    return [_join(c) for c in chunks]

def read_pages(path: Path) -> list[tuple[int, str]]:
    """Return (page_number, text). Markdown is one page; PDFs keep real page numbers."""
    if path.suffix == ".pdf":
        return [(i, p.extract_text() or "") for i, p in enumerate(PdfReader(path).pages, 1)]
    return [(1, path.read_text(encoding="utf-8"))]

def sections(text: str) -> list[tuple[str, str]]:
    """Split on '## ' headings -> (heading, body). Text before the first heading has heading ''."""
    parts = re.split(r"^## +(.+)$", text, flags=re.MULTILINE)
    out = [("", parts[0])]
    out += [(parts[i].strip(), parts[i + 1]) for i in range(1, len(parts), 2)]
    return [(h, b.strip()) for h, b in out if b.strip()]

def title_of(text: str, path: Path) -> str:
    m = re.search(r"^# +(.+)$", text, flags=re.MULTILINE)
    return m.group(1).strip() if m else path.stem.replace("-", " ").title()

def main(raw: bool = False):
    """raw=True (ablation only) skips masking and writes to chunks_raw, never to chunks."""
    table = RAW_TABLE if raw else MASKED_TABLE
    with psycopg.connect(DB_URL, autocommit=True) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        register_vector(conn)
        conn.execute(f"""CREATE TABLE IF NOT EXISTS {table} (
            id serial PRIMARY KEY, doc text, page int, content text, embedding vector(384))""")
        conn.execute(f"TRUNCATE {table}")
        seen = set()
        paths = sorted(p for d in SOURCE_DIRS if d.exists()
                       for p in d.iterdir() if p.suffix in (".md", ".pdf"))
        for path in paths:
            for page, text in read_pages(path):
                masked = text if raw else mask(text)               # mask FIRST (unless --raw)
                title = title_of(masked, path)
                for heading, body in sections(masked):             # then split and chunk
                    header = f"{title} > {heading}" if heading else title
                    for piece in chunk(body):
                        content = f"{header}\n{piece}"             # heading travels with every chunk
                        h = hashlib.sha256(content.encode()).hexdigest()
                        if h in seen:
                            continue
                        seen.add(h)
                        conn.execute(
                            f"INSERT INTO {table} (doc, page, content, embedding) VALUES (%s, %s, %s, %s)",
                            (path.name, page, content, model.encode(content)))
    print(f"Ingest done ({table})")

if __name__ == "__main__":
    main(raw="--raw" in sys.argv)
