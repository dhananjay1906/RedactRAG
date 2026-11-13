import os
import psycopg
from dotenv import load_dotenv
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer
from app.mask import mask

load_dotenv()
DB_URL = os.environ["DATABASE_URL"]
model = SentenceTransformer("all-MiniLM-L6-v2")  # 384-dim, runs locally

def search(query: str, k: int = 5) -> list[dict]:
    q = model.encode(mask(query))
    with psycopg.connect(DB_URL) as conn:
        register_vector(conn)
        rows = conn.execute(
            "SELECT doc, page, content, embedding <=> %s AS dist "
            "FROM chunks ORDER BY dist LIMIT %s", (q, k)).fetchall()
    return [{"doc": d, "page": p, "content": c, "distance": float(x)} for d, p, c, x in rows]