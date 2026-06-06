"""R4: observability for the FullLens Analyst Assistant ($0, local).

Wraps answer_question with per-query tracing: latency, retrieval count, citations, whether the
local LLM was used, and the live model prediction pulled. Traces append to rag/traces.jsonl
(the $0 local equivalent of a Langfuse dashboard; Langfuse self-host can consume the same
records if a user runs the OSS server, but no paid/cloud account is required). A summary view
aggregates cost-free query stats (count, p50/p95 latency, llm-usage rate, mean citations).

Run a demo: python -m rag.trace "Why did SVB fail?"   then   python -m rag.trace --summary
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
for p in (REPO, REPO / "src", REPO / "ml"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from rag.graph import answer_question  # noqa: E402

TRACES = REPO / "rag" / "traces.jsonl"


def traced_answer(question: str) -> dict:
    t0 = time.perf_counter()
    out = answer_question(question)
    latency_ms = round((time.perf_counter() - t0) * 1000, 1)
    rec = {
        "ts": time.time(),
        "question": question,
        "latency_ms": latency_ms,
        "n_retrieved": len(out.get("retrieved", [])),
        "n_citations": len(out.get("citations", [])),
        "used_llm": out.get("used_llm", False),
        "model_pred": out.get("model_pred"),
        "cost_usd": 0.0,  # local model + local vector store: $0 per query, by construction
    }
    with TRACES.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
    return {**out, "trace": rec}


def summary() -> dict:
    if not TRACES.exists():
        return {"n": 0}
    recs = [json.loads(line) for line in TRACES.read_text(encoding="utf-8").splitlines() if line]
    lat = sorted(r["latency_ms"] for r in recs)
    n = len(recs)

    def pct(p):
        return lat[min(n - 1, int(p * n))] if n else 0.0
    return {
        "n_queries": n,
        "latency_ms_p50": pct(0.50),
        "latency_ms_p95": pct(0.95),
        "llm_usage_rate": round(sum(r["used_llm"] for r in recs) / n, 3) if n else 0.0,
        "mean_citations": round(sum(r["n_citations"] for r in recs) / n, 2) if n else 0.0,
        "total_cost_usd": round(sum(r.get("cost_usd", 0.0) for r in recs), 4),
    }


if __name__ == "__main__":
    if "--summary" in sys.argv:
        print(json.dumps(summary(), indent=2))
    else:
        q = " ".join(a for a in sys.argv[1:] if not a.startswith("--")) or "Why did SVB fail?"
        r = traced_answer(q)
        print("trace:", json.dumps(r["trace"]))
