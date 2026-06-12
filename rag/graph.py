"""R2: the FullLens Analyst Assistant RAG path, orchestrated with LangGraph ($0, local).

Pipeline: retrieve (Chroma) -> ground_model (pull the LIVE Capstone-2 model prediction for any
bank named in the question) -> synthesize (OpenRouter, instructed to answer ONLY from the
retrieved context and to cite source URLs). If OpenRouter is unreachable or unconfigured the
synthesis falls back to an extractive, fully-cited answer, so the path always returns an answer.

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

from rag.ingest import _failure_docs, _methodology_docs  # noqa: E402

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
TOP_K = 4


class State(TypedDict, total=False):
    question: str
    docs: list
    doc_sources: list  # source URL/path per doc, aligned 1:1 with docs (for cited-only output)
    sources: list
    bank_cert: int
    bank_name: str
    model_pred: dict
    answer: str
    used_llm: bool


from functools import lru_cache


@lru_cache(maxsize=1)
def _corpus() -> tuple:
    """Build the tiny knowledge corpus in-memory (66 cited failure cases + a few methodology docs)
    from the same sources the offline indexer uses. No vector DB / embedding model is needed at
    this scale, so the assistant runs in the lightweight $0 image with zero heavy ML deps."""
    fdocs, fids, fmetas = _failure_docs()
    mdocs, mids, mmetas = _methodology_docs()
    return (fdocs + mdocs, fids + mids, fmetas + mmetas)


def _toks(s: str) -> set:
    import re
    return {t for t in re.findall(r"[a-z0-9]+", (s or "").lower()) if len(t) >= 3}


def _lexical_topk(question: str, k: int):
    """Rank corpus docs by token overlap with the question (overlap + Jaccard tie-break). For a
    ~71-doc corpus this matches semantic retrieval in practice and needs no embeddings."""
    docs, _ids, metas = _corpus()
    q = _toks(question)
    scored = []
    for d, m in zip(docs, metas, strict=False):
        dt = _toks(d)
        overlap = len(q & dt)
        jacc = overlap / (len(q | dt) or 1)
        scored.append((overlap + jacc, d, m))
    scored.sort(key=lambda x: x[0], reverse=True)
    chosen = scored[:k]
    return [d for _s, d, _m in chosen], [m for _s, _d, m in chosen]

# Common short forms -> CERT, so colloquial names resolve to the right institution.
_SHORT_FORMS = {
    "svb": 24735, "silicon valley": 24735, "first republic": 59017,
    "signature bank": 57053, "republic first": 27332, "pulaski": 28611,
    "heartland tri-state": 25851,
}


@lru_cache(maxsize=1)
def _bank_index() -> list:
    """Every bank in the panel as (name_lower, cert, display_name, quarter), so a question can
    name ANY institution (not just failures). quarter lets us prefer the active entity when one
    name maps to several CERTs (legacy/merged charters)."""
    import re
    from finlens_ml import scenario
    items = []
    for _, r in scenario.live_bank_directory().iterrows():
        nm = str(r.get("bank_name") or "").strip()
        nl = nm.lower()
        core = re.sub(r"[^a-z0-9]", "", nl)
        # Include multi-word names AND single-token names the dropdown lists but a space-only
        # filter silently drops ("BancFirst", "EagleBank", "TowneBank", "EVB", "BANK 7"). Skip a
        # bare generic word ("BANK") so it can never match ordinary prose, and require a >=3-char
        # core to drop noise. Verbatim matching in _detect_bank is word-boundary-guarded, so even
        # short single-token names stay false-positive-safe.
        if (len(nm) >= 7 and " " in nm) or (len(core) >= 3 and core not in _GENERIC_NAME_WORDS):
            items.append((nl, int(r["cert"]), nm, str(r.get("quarter") or "")))
    return items


@lru_cache(maxsize=1)
def _cert_to_name() -> dict:
    return {cert: disp for _nl, cert, disp, _q in _bank_index()}


@lru_cache(maxsize=1)
def _bank_cores() -> dict:
    """Distinctive core name (generic words stripped) -> entities, for typo-tolerant matching.
    e.g. 'fifth third bank, national association' -> core 'fifth third'."""
    import re
    cores: dict = {}
    for nl, cert, disp, qtr in _bank_index():
        toks = [t for t in re.findall(r"[a-z0-9]+", nl)
                if t not in _GENERIC_NAME_WORDS and len(t) >= 3]
        if not toks:
            continue
        cores.setdefault(" ".join(toks), []).append((nl, cert, disp, qtr))
    return cores


_COMMON_WORD_BANKS = {
    "regions", "discover", "commerce", "valley", "citizens", "heritage", "premier", "summit",
    "pinnacle", "liberty", "century", "pacific", "provident", "sterling", "independence",
    "cornerstone", "signature", "republic", "columbia", "amerant", "pathward",
}
_GENERIC_NAME_WORDS = {
    "bank", "banks", "national", "association", "na", "the", "of", "company", "co", "trust",
    "and", "financial", "corp", "corporation", "inc", "savings", "federal", "fsb", "holding",
    "group", "bancorp", "banc", "members", "first", "community", "state",
}


def _name_tokens(name: str) -> set:
    import re
    toks = re.findall(r"[a-z0-9]+", name.lower())
    return {t for t in toks if t not in _GENERIC_NAME_WORDS and len(t) >= 3}


_NA_SUFFIXES = (", national association", " national association", ", n.a.", " n.a.",
                ", national assn", " bank, national association")


def _pick_primary(cands: list, phrase: str):
    """From entities whose name starts with `phrase`, pick the PRIMARY one: the bank whose name
    is just the phrase plus a 'national association'/'bank' suffix (no regional qualifier like
    'CALIFORNIA' or 'DEARBORN'), preferring the freshest filing. Falls back to freshest+shortest.
    Returns (cert, display_name)."""
    def core(nl: str) -> str:
        for s in _NA_SUFFIXES:
            if nl.endswith(s):
                return nl[: -len(s)].strip().rstrip(",").strip()
        return nl
    primary_cores = {phrase, phrase + " bank", phrase.removesuffix(" bank")}
    primary = [c for c in cands if core(c[0]) in primary_cores]
    pool = primary or cands
    top_q = max(c[3] for c in pool)
    pool = [c for c in pool if c[3] == top_q]          # freshest filing
    pool.sort(key=lambda c: len(c[0]))                  # then the least-qualified (shortest) name
    return pool[0][1], pool[0][2]


def _detect_bank(question: str):
    """Resolve any bank the question names -> (cert, display_name), or None. When a name maps to
    several CERTs (e.g. a legacy charter ending 2009 plus the active 2026 entity), prefer the one
    with the freshest filing so 'tell me about Fifth Third Bank' resolves to the active bank."""
    q = question.lower()
    for frag, cert in _SHORT_FORMS.items():
        if frag in q:
            return cert, _cert_to_name().get(cert, frag.title())
    idx = _bank_index()

    import re

    _STOP_FIRST = {"the", "a", "an", "of", "and", "what", "how", "why", "tell", "me", "about",
                   "is", "are", "was", "did", "does", "do", "it", "this", "that", "model",
                   "data", "give", "show", "happened", "to", "for", "on", "in"}

    # 1) exact-ish: the longest full bank name that appears verbatim (as whole tokens) in the
    # question. Word-boundary guarded so short single-token names ("EVB", "UBANK", "BANK 7")
    # only match when typed as their own word, never as a substring buried in ordinary prose.
    matched = None
    for name_lower, _cert, _disp, _qtr in sorted(idx, key=lambda x: len(x[0]), reverse=True):
        if re.search(rf"(?<![a-z0-9]){re.escape(name_lower)}(?![a-z0-9])", q):
            matched = name_lower
            break

    # 2) phrase-prefix: a contiguous phrase from the question that a bank name STARTS WITH
    # (handles "Bank of America", "JPMorgan Chase" whose full FDIC name is longer than typed).
    if matched is None:
        words = re.findall(r"[a-z0-9&.]+", q)
        for n in range(min(6, len(words)), 0, -1):  # longest phrases first, down to single word
            for i in range(len(words) - n + 1):
                seg = words[i:i + n]
                if seg[0] in _STOP_FIRST:
                    continue
                # single-word match must be a distinctive, non-generic name token (and not a
                # common English word that happens to be a bank name; those resolve via "<X> bank")
                if n == 1 and (seg[0] in _GENERIC_NAME_WORDS or len(seg[0]) < 6
                               or seg[0] in _COMMON_WORD_BANKS):
                    continue
                phrase = " ".join(seg)
                if len(phrase) < 6:
                    continue
                # the phrase must carry a distinctive (non-generic) token, else "bank of" /
                # "first national" prefix-match nearly every bank
                if not any(t not in _GENERIC_NAME_WORDS and t not in _STOP_FIRST for t in seg):
                    continue
                # word-boundary prefix only, so "morgan" does not match "morganton ..."
                if any(nl == phrase or nl.startswith(phrase + " ") or nl.startswith(phrase + ",")
                       for nl, _c, _d, _qt in idx):
                    matched = phrase
                    break
            if matched:
                break

    if matched is not None:
        cands = [(nl, cert, disp, qtr) for (nl, cert, disp, qtr) in idx if nl.startswith(matched)]
        return _pick_primary(cands, matched)

    # 3) token-subset: a bank whose >=2 distinctive tokens all appear in the question.
    # Requiring two tokens avoids a single common word (e.g. "america") mis-matching.
    qtokens = set(re.findall(r"[a-z0-9]+", q))
    best = None  # ((n_tokens, char_len, quarter), cert, disp)
    for nl, cert, disp, qtr in idx:
        toks = _name_tokens(nl)
        if len(toks) < 2 or not toks <= qtokens:
            continue
        key = (len(toks), sum(len(t) for t in toks), qtr)
        if best is None or key > best[0]:
            best = (key, cert, disp)
    if best:
        return best[1], best[2]

    # 4) fuzzy (typo-tolerant): close-match a question phrase to a distinctive bank core, so
    # "fifth thord" -> "fifth third", "wells fargp" -> "wells fargo". Strict cutoff to avoid
    # matching ordinary words; resolve to the freshest entity for the matched core.
    import difflib
    cores = _bank_cores()
    core_keys = list(cores)
    # Work only on DISTINCTIVE tokens (drop generic words like bank/of and common English-word
    # bank names), so a typo of a real bank name resolves but ordinary prose does not.
    dwords = [w for w in re.findall(r"[a-z0-9]+", q)
              if w not in _GENERIC_NAME_WORDS and w not in _STOP_FIRST
              and len(w) >= 3 and w not in _COMMON_WORD_BANKS]

    def _ratio(a, b):
        return difflib.SequenceMatcher(None, a, b).ratio()

    best_core = None  # (ratio, core_key)
    # multi-token phrases (>=2 distinctive tokens): robust against false positives
    for n in (3, 2):
        for i in range(len(dwords) - n + 1):
            phrase = " ".join(dwords[i:i + n])
            m = difflib.get_close_matches(phrase, core_keys, n=1, cutoff=0.86)
            if m and (best_core is None or _ratio(phrase, m[0]) > best_core[0]):
                best_core = (_ratio(phrase, m[0]), m[0])
    # single distinctive token: only as a TYPO (ratio < 1.0; exact single words are handled
    # earlier), length-guarded, so e.g. "comerca"/"citibnk" resolve but stray words do not
    if best_core is None:
        for w in dwords:
            if len(w) < 6:
                continue
            m = difflib.get_close_matches(w, core_keys, n=1, cutoff=0.86)
            if not m:
                continue
            r = _ratio(w, m[0])
            if 0.86 <= r < 1.0 and (best_core is None or r > best_core[0]):
                best_core = (r, m[0])
    if best_core:
        # resolve to the PRIMARY active entity for that core (not a Trust/regional sub-charter)
        return _pick_primary(cores[best_core[1]], best_core[1])
    return None


# ---- nodes ----

def retrieve(state: State) -> State:
    docs, metas = _lexical_topk(state["question"], TOP_K)

    # Precision fix: if the question names a known bank, make that bank's OWN failure document
    # rank first, so a short query ("what happened to SVB") never mis-cites another bank's report.
    hit = _detect_bank(state["question"])
    if hit:
        cert, _name = hit
        cdocs, cids, cmetas = _corpus()
        fid = f"failure::{cert}"
        if fid in cids:
            j = cids.index(fid)
            bank_doc, bank_meta = cdocs[j], cmetas[j]
            docs = [d for d in docs if d != bank_doc]
            metas = [m for m in metas if m.get("cert") != cert]
            docs.insert(0, bank_doc)
            metas.insert(0, bank_meta)
            docs, metas = docs[:TOP_K], metas[:TOP_K]

    doc_sources = [(m.get("source_url") or m.get("source") or "") for m in metas]
    # deduped, order-preserving list of all retrieved sources (fallback if no [n] is cited)
    sources: list = []
    for s in doc_sources:
        if s and s not in sources:
            sources.append(s)
    return {"docs": docs, "doc_sources": doc_sources, "sources": sources}


def ground_model(state: State) -> State:
    hit = _detect_bank(state["question"])
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


def _openrouter(prompt: str) -> str:
    """Synthesize via OpenRouter using the OPENROUTER_API_KEY env credential (never hardcoded).
    Raises on any failure (missing key, network, bad response) -> extractive fallback."""
    import json
    import urllib.request

    from finlens.config import get_settings

    settings = get_settings()
    key = settings.openrouter_api_key
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not configured")
    body = json.dumps({
        "model": settings.openrouter_model,
        "temperature": 0.1,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        OPENROUTER_URL, data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        out = json.loads(r.read())["choices"][0]["message"]["content"].strip()
    if not out:
        raise RuntimeError("empty OpenRouter response")
    return out


def synthesize(state: State) -> State:
    context = _context_block(state)
    prompt = (
        "You are a bank-risk analyst assistant. Answer the question using ONLY the numbered "
        "context below. Cite the context items you use like [1], [2]. If the context does not "
        "support an answer, say so plainly. Do not invent facts or numbers.\n\n"
        f"Context:\n{context}\n\nQuestion: {state['question']}\n\nCited answer:")
    try:
        return {"answer": _openrouter(prompt), "used_llm": True}
    except Exception:  # noqa: BLE001 -> extractive, fully-cited fallback (no external call)
        pass
    # extractive, fully-cited fallback
    bullets = "\n".join(f"- {d}" for d in state.get("docs", [])[:3])
    mp = state.get("model_pred")
    extra = (f"\nLive model score for {state.get('bank_name')}: "
             f"{mp['probability']:.3f} as of {mp['quarter']}." if mp else "")
    return {"answer": f"Answering from the retrieved sources:\n{bullets}{extra}",
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


def _cited_sources(answer: str, doc_sources: list, all_sources: list) -> list:
    """Return only the sources the answer actually cites via [n] markers, mapped through the
    per-doc source list. Falls back to all retrieved sources if the model emitted no markers.
    This stops irrelevant retrievals (e.g. a different bank's report) from being listed as
    'sources' when the answer never used them."""
    import re
    idxs = sorted({int(n) for n in re.findall(r"\[(\d{1,2})\]", answer or "")})
    cited: list = []
    for i in idxs:
        if 1 <= i <= len(doc_sources):
            s = doc_sources[i - 1]
            if s and s not in cited:
                cited.append(s)
    return cited or list(all_sources)


def _failure_record(cert: int):
    """Return the regulator failure-cause row for a CERT, or None if the bank did not fail."""
    try:
        from finlens_ml.failure_cause_labels import load_failure_causes
        df = load_failure_causes()
        sub = df[df["cert"] == cert]
        return None if sub.empty else sub.iloc[0].to_dict()
    except Exception:  # noqa: BLE001
        return None


def _bank_answer(question: str, cert: int, name: str) -> dict:
    """Deterministic, model-grounded answer for ANY named bank. Fast (no LLM): scores the bank
    live; for a bank that actually failed it adds the regulator cause + citation, otherwise it
    states plainly that the institution is operating. Always routes to the full report."""
    from finlens_ml import scenario
    from finlens_ml.scenario import humanize_feature

    rec = scenario.latest_row_for_cert(cert)
    if not rec:
        return {"question": question, "bank_name": name, "bank_cert": cert, "used_llm": False,
                "citations": [], "retrieved": [],
                "answer": f"{name} (FDIC CERT {cert}) is in the directory but has no scorable "
                          "filing on record."}
    scored = scenario.score_features(rec["features"])
    prob, thr = scored["probability"], scored["threshold"]
    state = rec.get("state") or "—"
    quarter = rec.get("quarter")
    model_pred = {"quarter": quarter, "probability": prob, "threshold": thr}
    top = next((r for r in scored.get("reasons", []) if r.get("shap") is not None), None)
    driver = (f" The largest model risk driver is {humanize_feature(top['feature'])} "
              f"({'raising' if top['shap'] > 0 else 'lowering'} estimated risk)." if top else "")

    fail = _failure_record(cert)
    citations = []
    if fail:
        cause = str(fail.get("cause", "—")).replace("_", "/")
        year = fail.get("failure_year", "—")
        quote = (fail.get("quote") or "").strip()
        src = fail.get("source_url") or ""
        if src:
            citations = [src]
        answer = (
            f"{name} (FDIC CERT {cert}, {state}) failed in {year}. Regulator-determined primary "
            f"cause: {cause}." + (f' "{quote}"' if quote else "") +
            f" The model's last pre-failure score, as of {quarter}, was {prob:.2%} against the "
            f"{thr:.0%} review threshold; a low score on a rate/liquidity or fraud failure is "
            "expected, since those leave little signal on quarterly Call Reports (see the "
            "failure-type decomposition).")
    else:
        rel = "above" if prob >= thr else "below"
        answer = (
            f"{name} (FDIC CERT {cert}, {state}) is an operating institution: it has not failed "
            f"and has no failure on record. As of {quarter}, the model estimates a {prob:.2%} "
            f"four-quarter distress probability, {rel} the {thr:.0%} review threshold. Bank "
            "failure is a sub-1% base-rate event, so this is a screening estimate, not a "
            "forecast of failure." + driver)
    answer += " Open the full report below for the complete assessment."
    return {"question": question, "answer": answer, "citations": citations, "retrieved": [],
            "model_pred": model_pred, "used_llm": False, "bank_name": name, "bank_cert": cert}


def answer_question(question: str) -> dict:
    # A question that names any bank gets a fast, deterministic, model-grounded answer (and the
    # report offer). Only open-ended/methodology questions go through the retrieval + LLM path.
    hit = _detect_bank(question)
    if hit:
        return _bank_answer(question, hit[0], hit[1])
    # methodology / open-ended path: run retrieve -> ground -> synthesize directly (no langgraph)
    state: State = {"question": question}
    state.update(retrieve(state))
    state.update(ground_model(state))
    state.update(synthesize(state))
    answer = state.get("answer", "")
    citations = _cited_sources(answer, state.get("doc_sources", []), state.get("sources", []))
    return {"question": question, "answer": answer,
            "citations": citations, "retrieved": state.get("docs", []),
            "model_pred": state.get("model_pred"), "used_llm": state.get("used_llm", False),
            "bank_name": state.get("bank_name"), "bank_cert": state.get("bank_cert")}


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "Why did Silicon Valley Bank fail?"
    r = answer_question(q)
    print("Q:", q)
    print("used_llm:", r["used_llm"], "| model_pred:", r["model_pred"])
    print("\nANSWER:\n", r["answer"])
    print("\nCITATIONS:")
    for c in r["citations"]:
        print(" -", c)
