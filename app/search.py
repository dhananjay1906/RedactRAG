import os
import psycopg
from dotenv import load_dotenv
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer
from app.mask import mask

load_dotenv()
DB_URL = os.environ["DATABASE_URL"]
model = SentenceTransformer("all-MiniLM-L6-v2")  # 384-dim, runs locally

MASKED_TABLE, RAW_TABLE = "chunks", "chunks_raw"   # fixed names; never built from input

def search(query: str, k: int = 5, masked: bool = True) -> list[dict]:
    """masked=False is only for the cost-of-privacy ablation: unmasked query, raw table."""
    table = MASKED_TABLE if masked else RAW_TABLE
    q = model.encode(mask(query) if masked else query)
    with psycopg.connect(DB_URL) as conn:
        register_vector(conn)
        rows = conn.execute(
            f"SELECT doc, page, content, embedding <=> %s AS dist "
            f"FROM {table} ORDER BY dist LIMIT %s", (q, k)).fetchall()
    return [{"doc": d, "page": p, "content": c, "distance": float(x)} for d, p, c, x in rows]