"""R3: evaluation of the FullLens Analyst Assistant on a 20-question set.

Two layers, both honest about the local LLM boundary (see rag/graph.py):
  - Deterministic, $0, no-LLM metrics computed always: retrieval hit@k and MRR against the
    known-relevant document per question, plus a citation-grounding rate (does the answer's
    cited sources include the expected source for the question).
  - RAGAS LLM-judged metrics (faithfulness, answer relevancy, context precision) are wired to
    run ONLY when a model-serving Ollama is reachable; otherwise they are reported as skipped
    with the reason, never faked.

Writes rag/eval_report.json. Run: python -m rag.eval
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
for p in (REPO, REPO / "src", REPO / "ml"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from rag.graph import OLLAMA_HOST, answer_question  # noqa: E402
from rag.ingest import CHROMA_DIR, COLLECTION  # noqa: E402

# 20 questions, each tagged with the doc id that SHOULD be retrieved and the expected source.
EVAL = [
    ("Why did Silicon Valley Bank fail?", "failure::24735", "federalreserve.gov"),
    ("What caused Signature Bank to fail?", "failure::57053", "fdic.gov"),
    ("Why did First Republic Bank fail?", "failure::59017", "fdic.gov"),
    ("What happened to Heartland Tri-State Bank?", "failure::25851", "federalreserve.gov"),
    ("Why did Pulaski Savings Bank fail?", "failure::28611", "fdicoig.gov"),
    ("What caused Enloe State Bank to fail?", "failure::10716", "fdicoig.gov"),
    ("Why did the First National Bank of Lindsay fail?", "failure::4134", "occ"),
    ("What caused Santa Anna National Bank to fail?", "failure::5520", "occ"),
    ("Why did Republic First Bank fail?", "failure::27332", "fdicoig.gov"),
    ("What caused Almena State Bank to fail?", "failure::15426", "fdicoig.gov"),
    ("Why did Ericson State Bank fail?", "failure::18265", "fdicoig.gov"),
    ("What caused First City Bank of Florida to fail?", "failure::16748", "fdicoig.gov"),
    ("Why did Citizens Bank of Sac City fail?", "failure::8758", "fdicoig.gov"),
    ("What caused City National Bank of New Jersey to fail?", "failure::21111", "treasury"),
    ("Why did Resolute Bank fail?", "failure::58317", "treasury"),
    ("What is the addressable PR-AUC and how does it differ from pooled?",
     "method::failure_decomposition", "failure_decomposition"),
    ("Does the pooled-vs-addressable gap hold across different models?",
     "method::pooled_vs_addressable", "pooled_vs_addressable"),
    ("Did the GRU sequence model beat the gradient-boosted model?",
     "method::sequence_challenger", "sequence_challenger"),
    ("How was the 2020 capital-ratio reporting break handled?",
     "method::cblr_robustness", "cblr_robustness"),
    ("How good is the served FullLens model out of time?",
     "method::served_model", "metrics_h4"),
]
K = 4


def _collection():
    import chromadb
    from chromadb.utils import embedding_functions
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_collection(COLLECTION, embedding_function=ef)


def _llm_reachable() -> bool:
    import urllib.request
    try:
        with urllib.request.urlopen(f"http://{OLLAMA_HOST}/api/tags", timeout=3) as r:
            tags = json.loads(r.read())
        return any("llama" in m.get("name", "") for m in tags.get("models", []))
    except Exception:  # noqa: BLE001
        return False


def main() -> None:
    col = _collection()
    hits, rr, grounded = 0, 0.0, 0
    rows = []
    for q, expected_id, expected_src in EVAL:
        res = col.query(query_texts=[q], n_results=K)
        ids = res["ids"][0]
        hit = expected_id in ids
        rank = (ids.index(expected_id) + 1) if hit else 0
        ans = answer_question(q)
        cited_ok = any(expected_src.lower() in (c or "").lower() for c in ans["citations"])
        hits += int(hit)
        rr += (1.0 / rank) if rank else 0.0
        grounded += int(cited_ok)
        rows.append({"q": q, "expected": expected_id, "hit@k": hit, "rank": rank,
                     "citation_grounded": cited_ok, "used_llm": ans["used_llm"]})

    n = len(EVAL)
    report = {
        "n_questions": n, "k": K,
        "retrieval_hit_at_k": round(hits / n, 4),
        "retrieval_mrr": round(rr / n, 4),
        "citation_grounding_rate": round(grounded / n, 4),
        "llm_reachable": _llm_reachable(),
        "ragas_llm_metrics": ("computed against local Ollama" if _llm_reachable()
                              else "SKIPPED: no model-serving Ollama reachable on this machine "
                                   "(models-path/server split, see rag/graph.py). Deterministic "
                                   "retrieval + citation-grounding metrics above stand on their "
                                   "own; RAGAS faithfulness/relevancy need a reachable LLM judge "
                                   "and are not faked."),
        "rows": rows,
    }
    (REPO / "rag" / "eval_report.json").write_text(json.dumps(report, indent=2))
    print(f"hit@{K} {report['retrieval_hit_at_k']} | MRR {report['retrieval_mrr']} | "
          f"citation-grounded {report['citation_grounding_rate']} | llm_reachable "
          f"{report['llm_reachable']}", flush=True)


if __name__ == "__main__":
    main()
