from fastapi import FastAPI, Query
from pydantic import BaseModel
from app.agent import ask
from app.search import search

app = FastAPI(title="RedactRAG")

class AskRequest(BaseModel):
    question: str

class AskResponse(BaseModel):
    answer: str
    citations: list[str]

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/ask", response_model=AskResponse)
def ask_endpoint(req: AskRequest):
    r = ask(req.question)
    return AskResponse(answer=r["answer"], citations=r.get("citations", []))

@app.get("/search")
def search_endpoint(q: str, k: int = Query(5, ge=1, le=20)):  # cap k so one call can't dump the DB
    return search(q, k)
