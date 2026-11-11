"""R1: build the local Chroma knowledge index for the FullLens Analyst Assistant.

Corpus ($0, all from sources already in the repo):
  - one cited failure-case document per OOT failed bank, grounded in the regulator-stated
    cause from ml/finlens_ml/failure_cause_labels.py (FDIC OIG / OCC / Fed / Treasury OIG),
    each carrying its source URL so answers can cite it;
  - methodology documents drawn from the committed artifacts (decomposition, pooled-vs-
    addressable, CBLR robustness, sequence challenger, served-model summary), so the assistant
    can answer "how was this measured / how good is the model" with grounded, cited context.

Embeddings: sentence-transformers all-MiniLM-L6-v2, run locally (no paid API). Persisted to
rag/chroma_db. R2 (LangGraph) retrieves from this index and additionally pulls the LIVE model
prediction (Capstone 2) at query time for the quantitative profile. Run: python -m rag.ingest
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
for p in (REPO, REPO / "src", REPO / "ml"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from finlens_ml.failure_cause_labels import load_failure_causes  # noqa: E402

CHROMA_DIR = REPO / "rag" / "chroma_db"
COLLECTION = "fulllens_kb"
ART = REPO / "ml" / "artifacts"


def _failure_docs():
    df = load_failure_causes()
    docs, ids, metas = [], [], []
    for _, r in df.iterrows():
        text = (f"{r['name']} (FDIC CERT {r['cert']}) failed in {r['failure_year']}. "
                f"Regulator-determined primary cause of failure: {r['cause']} "
                f"(financial-visibility class: {r['visibility']}). {r['quote']} "
                f"Source ({r['source_type']}): {r['source_url']}.")
        docs.append(text)
        ids.append(f"failure::{r['cert']}")
        metas.append({"type": "failure_case", "cert": int(r["cert"]), "bank": r["name"],
                      "failure_year": str(r["failure_year"]), "cause": r["cause"],
                      "visibility": r["visibility"], "source_url": r["source_url"],
                      "confidence": r["confidence"]})
    return docs, ids, metas


def _methodology_docs():
    docs, ids, metas = [], [], []

    def add(key, text, src):
        docs.append(text); ids.append(f"method::{key}")
        metas.append({"type": "methodology", "topic": key, "source": src})

    def _j(name):
        p = ART / name
        return json.loads(p.read_text()) if p.exists() else {}

    fd = _j("failure_decomposition.json")
    if fd:
        add("failure_decomposition",
            "Failure-type decomposition: of the 66 out-of-time failures, "
            f"{fd.get('type_counts', {})}. {fd.get('interpretation', '')} Addressable PR-AUC "
            f"{fd.get('pr_auc_addressable')} {fd.get('pr_auc_addressable_ci')} vs full "
            f"{fd.get('pr_auc_full')} {fd.get('pr_auc_full_ci')}.",
            "ml/artifacts/failure_decomposition.json")
    pa = _j("pooled_vs_addressable.json")
    if pa:
        add("pooled_vs_addressable", pa.get("claim", ""), "ml/artifacts/pooled_vs_addressable.json")
    cb = _j("cblr_robustness.json")
    if cb:
        add("cblr_robustness", cb.get("conclusion", ""), "ml/artifacts/cblr_robustness.json")
    sq = _j("sequence_challenger.json")
    if sq:
        add("sequence_challenger", sq.get("verdict", ""), "ml/artifacts/sequence_challenger.json")
    m = _j("metrics_h4.json")
    if m:
        t = m.get("oot_test", {}).get("calibrated_lgbm", {})
        add("served_model",
            "The served FullLens model is a calibrated, monotone-constrained gradient-boosted "
            f"hazard model predicting failure within 4 quarters. Out-of-time PR-AUC "
            f"{t.get('pr_auc')}, ROC-AUC {t.get('roc_auc')}, recall@200 {t.get('recall_at_k')}, "
            "on 66 real failures. It is calibrated, monotone, and SHAP-explainable; a GRU "
            "sequence challenger and RF/XGBoost baselines were tested and do not beat it.",
            "ml/artifacts/metrics_h4.json")
    return docs, ids, metas


def main() -> None:
    import chromadb
    from chromadb.utils import embedding_functions

    fdocs, fids, fmetas = _failure_docs()
    mdocs, mids, mmetas = _methodology_docs()
    docs = fdocs + mdocs
    ids = fids + mids
    metas = fmetas + mmetas

    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        client.delete_collection(COLLECTION)
    except Exception:  # noqa: BLE001
        pass
    col = client.create_collection(COLLECTION, embedding_function=ef,
                                   metadata={"hnsw:space": "cosine"})
    col.add(documents=docs, ids=ids, metadatas=metas)
    print(f"indexed {len(docs)} docs ({len(fdocs)} failure cases + {len(mdocs)} methodology) "
          f"into {CHROMA_DIR} :: {COLLECTION}", flush=True)
    # smoke query
    res = col.query(query_texts=["Why did Silicon Valley Bank fail?"], n_results=2)
    print("smoke query 'Why did SVB fail?' top hit:", res["ids"][0][0],
          "->", res["documents"][0][0][:120], flush=True)


if __name__ == "__main__":
    main()
