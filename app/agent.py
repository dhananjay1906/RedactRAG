import os, re
from typing import TypedDict
from anthropic import Anthropic
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from app.mask import mask
from app.search import search

load_dotenv()
client = Anthropic()
MODEL = os.environ["CLAUDE_MODEL"]
SENT_PROMPTS: list[str] = []   # every masked prompt sent to Claude, used by the leak test

class State(TypedDict, total=False):
    question: str
    masked: bool              # False only for the cost-of-privacy ablation
    masked_question: str
    chunks: list[dict]
    prompt: str
    answer: str
    citations: list[str]

def mask_question(s):
    if not s.get("masked", True):
        return {"masked_question": s["question"]}   # ablation: question sent as typed
    return {"masked_question": mask(s["question"])}

def retrieve(s):
    return {"chunks": search(s["masked_question"], k=5, masked=s.get("masked", True))}

def build_prompt(s):
    context = "\n\n".join(f"[{c['doc']}]\n{c['content']}" for c in s["chunks"])
    prompt = ("Answer using ONLY the sources below. Cite each fact like [file.md]. "
              "If the answer isn't in the sources, say \"I don't know.\"\n\n"
              f"SOURCES:\n{context}\n\nQUESTION: {s['masked_question']}")
    if s.get("masked", True):
        SENT_PROMPTS.append(prompt)
    return {"prompt": prompt}

def generate(s):
    msg = client.messages.create(model=MODEL, max_tokens=1500,
                                 output_config={"effort": "low"},
                                 messages=[{"role": "user", "content": s["prompt"]}])
    # Haiku 5.5 thinks by default, so content[0] can be a ThinkingBlock; take the text block.
    return {"answer": next((b.text for b in msg.content if b.type == "text"), "")}

def check_citations(s):
    cited = set(re.findall(r"\[([\w\-]+\.md)\]", s["answer"]))
    retrieved = {c["doc"] for c in s["chunks"]}
    if not cited or not cited <= retrieved:
        return {"answer": "I don't know - no supporting source found.", "citations": []}
    source_text = " ".join(c["content"] for c in s["chunks"] if c["doc"] in cited)
    answer_text = re.sub(r"\[[\w\-]+\.md\]", "", s["answer"])
    numbers = set(re.findall(r"\d+(?:\.\d+)?", answer_text))
    unsupported = [n for n in numbers if n not in source_text]
    if unsupported:
        return {"answer": "I don't know - the sources don't support that answer.", "citations": []}
    return {"citations": sorted(cited)}

g = StateGraph(State)
for name, fn in [("mask_question", mask_question), ("retrieve", retrieve),
                 ("build_prompt", build_prompt), ("generate", generate),
                 ("check_citations", check_citations)]:
    g.add_node(name, fn)
g.add_edge(START, "mask_question")
g.add_edge("mask_question", "retrieve")
g.add_edge("retrieve", "build_prompt")
g.add_edge("build_prompt", "generate")
g.add_edge("generate", "check_citations")
g.add_edge("check_citations", END)
agent = g.compile()

def ask(question: str, masked: bool = True) -> dict:
    return agent.invoke({"question": question, "masked": masked})

def prepare(question: str) -> str:
    s = {"question": question}
    s |= mask_question(s)
    s |= retrieve(s)
    s |= build_prompt(s)
    return s["prompt"]
