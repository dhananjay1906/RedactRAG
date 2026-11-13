import hashlib
from pathlib import Path
import psycopg
from pgvector.psycopg import register_vector
from app.mask import mask
from app.search import model, DB_URL

def chunk(text: str, size: int = 500, overlap: int = 100) -> list[str]:
    return [text[i:i + size] for i in range(0, len(text), size - overlap)]

def main():
    with psycopg.connect(DB_URL, autocommit=True) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        register_vector(conn)
        conn.execute("""CREATE TABLE IF NOT EXISTS chunks (
            id serial PRIMARY KEY, doc text, page int, content text, embedding vector(384))""")
        conn.execute("TRUNCATE chunks")
        seen = set()
        for path in sorted(Path("data/policies").glob("*.md")):
            masked_doc = mask(path.read_text(encoding="utf-8"))   # mask FIRST
            for piece in chunk(masked_doc):                        # then chunk
                h = hashlib.sha256(piece.encode()).hexdigest()
                if h in seen:
                    continue
                seen.add(h)
                conn.execute(
                    "INSERT INTO chunks (doc, page, content, embedding) VALUES (%s, %s, %s, %s)",
                    (path.name, 1, piece, model.encode(piece)))
    print("Ingest done")

if __name__ == "__main__":
    main()