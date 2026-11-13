import hashlib
import re
from pathlib import Path
import psycopg
from pgvector.psycopg import register_vector
from pypdf import PdfReader
from app.mask import mask
from app.search import model, DB_URL

SOURCE_DIRS = [Path("data/policies"), Path("docs")]

def chunk(text: str, size: int = 500, overlap: int = 100) -> list[str]:
    return [text[i:i + size] for i in range(0, len(text), size - overlap)]

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

def main():
    with psycopg.connect(DB_URL, autocommit=True) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        register_vector(conn)
        conn.execute("""CREATE TABLE IF NOT EXISTS chunks (
            id serial PRIMARY KEY, doc text, page int, content text, embedding vector(384))""")
        conn.execute("TRUNCATE chunks")
        seen = set()
        paths = sorted(p for d in SOURCE_DIRS if d.exists()
                       for p in d.iterdir() if p.suffix in (".md", ".pdf"))
        for path in paths:
            for page, raw in read_pages(path):
                masked = mask(raw)                                 # mask FIRST
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
                            "INSERT INTO chunks (doc, page, content, embedding) VALUES (%s, %s, %s, %s)",
                            (path.name, page, content, model.encode(content)))
    print("Ingest done")

if __name__ == "__main__":
    main()
