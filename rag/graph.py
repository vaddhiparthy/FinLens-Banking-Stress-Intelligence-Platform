"""R2: the FullLens Analyst Assistant RAG path, orchestrated with LangGraph ($0, local).

Pipeline: retrieve (Chroma) -> ground_model (pull the LIVE Capstone-2 model prediction for any
bank named in the question) -> synthesize (local Ollama llama3.2:3b, instructed to answer ONLY
from the retrieved context and to cite source URLs). If Ollama is unavailable the synthesis
falls back to an extractive, fully-cited answer, so the path always runs $0 with no paid API.

Public entry point: answer_question(question) -> dict with answer, citations, retrieved, and
the model prediction used (if any). Run a demo: python -m rag.graph "Why did SVB fail?"
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TypedDict

REPO = Path(__file__).resolve().parents[1]
for p in (REPO, REPO / "src", REPO / "ml"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from rag.ingest import CHROMA_DIR, COLLECTION  # noqa: E402

OLLAMA_MODEL = "llama3.2:3b"
TOP_K = 4


class State(TypedDict, total=False):
    question: str
    docs: list
    sources: list
    bank_cert: int
    bank_name: str
    model_pred: dict
    answer: str
    used_llm: bool


def _collection():
    import chromadb
    from chromadb.utils import embedding_functions
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_collection(COLLECTION, embedding_function=ef)


def _bank_lookup() -> dict:
    """lowercase name fragments -> (cert, canonical name), incl common short forms."""
    from finlens_ml.failure_cause_labels import load_failure_causes
    m = {}
    for _, r in load_failure_causes().iterrows():
        m[r["name"].lower()] = (int(r["cert"]), r["name"])
    m.update({
        "svb": (24735, "Silicon Valley Bank"),
        "silicon valley": (24735, "Silicon Valley Bank"),
        "first republic": (59017, "First Republic Bank"),
        "signature": (57053, "Signature Bank"),
        "republic first": (27332, "Republic First Bank"),
        "pulaski": (28611, "Pulaski Savings Bank"),
        "heartland": (25851, "Heartland Tri-State Bank"),
    })
    return m


# ---- nodes ----

def retrieve(state: State) -> State:
    col = _collection()
    res = col.query(query_texts=[state["question"]], n_results=TOP_K)
    docs = res["documents"][0]
    metas = res["metadatas"][0]
    sources = []
    for md in metas:
        src = md.get("source_url") or md.get("source")
        if src and src not in sources:
            sources.append(src)
    return {"docs": docs, "sources": sources}


def ground_model(state: State) -> State:
    q = state["question"].lower()
    hit = None
    for frag, (cert, name) in _bank_lookup().items():
        if frag in q:
            hit = (cert, name)
            break
    if not hit:
        return {}
    cert, name = hit
    try:
        from finlens_ml import scenario
        row = scenario.latest_known_row_for_cert(cert)
        if row is None:
            return {"bank_cert": cert, "bank_name": name}
        scored = scenario.score_features(row["features"])
        return {"bank_cert": cert, "bank_name": name,
                "model_pred": {"quarter": row["quarter"], "probability": scored["probability"],
                               "threshold": scored["threshold"]}}
    except Exception:  # noqa: BLE001
        return {"bank_cert": cert, "bank_name": name}


def _context_block(state: State) -> str:
    lines = [f"[{i+1}] {d}" for i, d in enumerate(state.get("docs", []))]
    if state.get("model_pred"):
        mp = state["model_pred"]
        lines.append(f"[model] FullLens live score for {state.get('bank_name')} as of "
                     f"{mp['quarter']}: calibrated 4-quarter distress probability "
                     f"{mp['probability']:.3f} (review threshold {mp['threshold']:.2f}).")
    return "\n".join(lines)


import os  # noqa: E402

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434").replace("http://", "")
OLLAMA_URL = f"http://{OLLAMA_HOST}/api/chat"


def _strip_ansi(s: str) -> str:
    import re
    return re.sub(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*\x07", "", s).replace("\r", "")


def _ollama_cli(prompt: str) -> str:
    """Generate via the local Ollama CLI (`ollama run`). On this machine the HTTP server on
    :11434 has an empty model set but the CLI store has llama3.2:3b, so the CLI path is the one
    that actually serves the model. Strips terminal control codes from the output."""
    import subprocess
    r = subprocess.run(["ollama", "run", OLLAMA_MODEL, prompt],
                       capture_output=True, text=True, timeout=240)
    out = _strip_ansi(r.stdout or "").strip()
    if not out:
        raise RuntimeError(f"empty ollama-cli output (rc={r.returncode}): {r.stderr[:120]}")
    return out


def _ollama_chat(prompt: str) -> str:
    """Call the local Ollama HTTP API directly. Raises on any failure -> next fallback."""
    import json
    import urllib.request
    body = json.dumps({"model": OLLAMA_MODEL, "stream": False,
                       "messages": [{"role": "user", "content": prompt}],
                       "options": {"temperature": 0.1}}).encode()
    req = urllib.request.Request(OLLAMA_URL, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())["message"]["content"].strip()


def synthesize(state: State) -> State:
    context = _context_block(state)
    prompt = (
        "You are a bank-risk analyst assistant. Answer the question using ONLY the numbered "
        "context below. Cite the context items you use like [1], [2]. If the context does not "
        "support an answer, say so plainly. Do not invent facts or numbers.\n\n"
        f"Context:\n{context}\n\nQuestion: {state['question']}\n\nCited answer:")
    for backend in (_ollama_cli, _ollama_chat):  # CLI first (the path that works here), then HTTP
        try:
            return {"answer": backend(prompt), "used_llm": True}
        except Exception:  # noqa: BLE001
            continue
    # extractive, fully-cited fallback ($0, no LLM needed)
    bullets = "\n".join(f"- {d}" for d in state.get("docs", [])[:3])
    mp = state.get("model_pred")
    extra = (f"\nLive model score for {state.get('bank_name')}: "
             f"{mp['probability']:.3f} as of {mp['quarter']}." if mp else "")
    return {"answer": f"(extractive, no local LLM available)\n{bullets}{extra}",
            "used_llm": False}


def _build_graph():
    from langgraph.graph import END, START, StateGraph
    g = StateGraph(State)
    g.add_node("retrieve", retrieve)
    g.add_node("ground_model", ground_model)
    g.add_node("synthesize", synthesize)
    g.add_edge(START, "retrieve")
    g.add_edge("retrieve", "ground_model")
    g.add_edge("ground_model", "synthesize")
    g.add_edge("synthesize", END)
    return g.compile()


_GRAPH = None


def answer_question(question: str) -> dict:
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = _build_graph()
    out = _GRAPH.invoke({"question": question})
    return {"question": question, "answer": out.get("answer", ""),
            "citations": out.get("sources", []), "retrieved": out.get("docs", []),
            "model_pred": out.get("model_pred"), "used_llm": out.get("used_llm", False)}


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "Why did Silicon Valley Bank fail?"
    r = answer_question(q)
    print("Q:", q)
    print("used_llm:", r["used_llm"], "| model_pred:", r["model_pred"])
    print("\nANSWER:\n", r["answer"])
    print("\nCITATIONS:")
    for c in r["citations"]:
        print(" -", c)
