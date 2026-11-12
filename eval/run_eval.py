"""End-to-end RAG evaluation: Claude backend vs Gemini backend on identical documents.

Prerequisites (local stack, see docker-compose.local.yml):
  backend (Claude) on :18000, backend-gemini on :18001, worker + services up.
Usage:
  python run_eval.py --corpus C:/audito_eval/corpus --out C:/audito_eval/results [--only Q01,Q06] [--backends claude,gemini]

Secrets: the Anthropic key is read from ANTHROPIC_API_KEY or the file named by
ANTHROPIC_KEY_FILE, only to run the (optional) unsupported-claim judge. It is never printed.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import uuid

import httpx

BACKENDS = {"claude": "http://127.0.0.1:18000", "gemini": "http://127.0.0.1:18001"}
LLM_CONTAINER = {"claude": "audito_local-llm-service-1", "gemini": "audito_local-llm-service-gemini-1"}
# USD per million tokens (claude-opus-5-5): input, output, cache read, cache write (5m)
OPUS_55 = {"in": 4.00, "out": 20.00, "cache_read": 0.20, "cache_write": 5.00}

NOT_FOUND = re.compile(
    r"(not|n't|no|neither|nor|cannot|can't|unable)\s+(\w+\s+){0,5}?(state|specif|mention|provid|contain|includ|availab|found|appear|say|disclos|indicat|report|address|cover|record|identif)"
    r"|(no|not any)\s+(\w+\s+){0,3}(information|mention|reference|data|details)"
    r"|(is|are|was|were) not (given|listed|stated)|could not find|couldn't find|doesn'?t (say|specify|include)",
    re.I,
)
REF = re.compile(r"([\w\-. ]+?\.pdf)[\s,;:(]+(?:p\.?|pp\.?|page)\s*(\d+)", re.I)


def log(*a):
    print(*a, flush=True)


# --------------------------------------------------------------------------- api
class Api:
    def __init__(self, base):
        self.base = base
        self.c = httpx.Client(base_url=base, timeout=300)

    def register(self, name, email, password):
        r = self.c.post("/api/auth/register", json={"name": name, "email": email, "password": password})
        r.raise_for_status()
        return r.json()["token"]

    def upload(self, token, session_id, path):
        with open(path, "rb") as fh:
            r = self.c.post("/api/upload", headers={"Authorization": f"Bearer {token}"},
                            data={"session_id": session_id}, files={"file": (os.path.basename(path), fh, "application/pdf")})
        r.raise_for_status()
        return r.json()

    def status(self, token, task_id):
        return self.c.get(f"/api/upload/status/{task_id}", headers={"Authorization": f"Bearer {token}"}).json()

    def chat(self, token, session_id, query):
        t0 = time.time()
        r = self.c.post("/api/chat", headers={"Authorization": f"Bearer {token}"}, data={"query": query, "session_id": session_id})
        return r, time.time() - t0


def docker_log_usage(container, since_epoch):
    """Token usage lines the llm-service logged since `since_epoch` (metadata only)."""
    try:
        out = subprocess.run(["docker", "logs", "--since", str(int(since_epoch)), container], capture_output=True, text=True, timeout=60)
        text = out.stdout + out.stderr
    except Exception:
        return []
    rows = []
    for m in re.finditer(r"llm provider=(\w+) model=(\S+) served_by=(\S+) stop=(\S+) in=(\d+) out=(\d+) cache_read=(\d+) cache_write=(\d+) latency_ms=(\d+)", text):
        rows.append(dict(provider=m.group(1), model=m.group(2), served_by=m.group(3), stop=m.group(4), input=int(m.group(5)),
                         output=int(m.group(6)), cache_read=int(m.group(7)), cache_write=int(m.group(8)), latency_ms=int(m.group(9))))
    return rows


def opus_cost(rows):
    return sum(r["input"] * OPUS_55["in"] + r["output"] * OPUS_55["out"] + r["cache_read"] * OPUS_55["cache_read"]
               + r["cache_write"] * OPUS_55["cache_write"] for r in rows) / 1e6


# --------------------------------------------------------------------------- scoring
def score(q, resp_json, status, corpus_pages):
    text = (resp_json or {}).get("response") or ""
    cites = (resp_json or {}).get("citations") or []
    s = {"http": status, "words": len(text.split())}

    if status != 200:
        s.update(correct=False, error=(resp_json or {}).get("detail", "")[:200])
        return s

    # facts
    facts = q.get("facts") or []
    hit = [any(re.search(p, text, re.I) for p in group) for group in facts]
    s["facts_total"], s["facts_hit"] = len(facts), sum(hit)
    s["completeness"] = (sum(hit) / len(facts)) if facts else None
    s["missed_facts"] = [facts[i][0] for i, h in enumerate(hit) if not h]

    forbidden = [p for p in q.get("must_not", []) if re.search(p, text, re.I)]
    s["forbidden_hits"] = forbidden

    nf = bool(NOT_FOUND.search(text))
    s["says_not_found"] = nf
    min_words = q.get("min_words")
    s["long_enough"] = (s["words"] >= min_words) if min_words else None

    if q.get("expect_not_found"):
        s["correct"] = nf and not forbidden
    else:
        s["correct"] = (sum(hit) == len(facts)) and not forbidden and (s["long_enough"] is not False)

    # citations vs expected pages
    expected = q.get("pages") or []
    got = [(c.get("source", ""), c.get("page")) for c in cites]
    s["citations"] = [f"{src}:{pg}" for src, pg in got]
    if expected:
        hits = sum(1 for f, p in expected if any(f in src and pg == p for src, pg in got))
        recall = hits / len(expected)
        need = 1.0 if len(expected) <= 2 else 0.6
        ok = recall >= need
        for doc in q.get("require_both_docs", []):
            ok = ok and any(doc in src for src, _ in got)
        s["citation_recall"], s["citation_ok"] = round(recall, 2), ok
        rel = sum(1 for src, pg in got if any(f in src and pg == p for f, p in expected))
        s["citation_precision"] = round(rel / len(got), 2) if got else None
    else:
        s["citation_ok"] = len(got) == 0          # nothing should be cited when the answer is "not in the documents"
        s["citation_recall"] = s["citation_precision"] = None

    # fabricated in-text references: file/page that does not exist in the user's corpus
    bad = []
    for m in REF.finditer(text):
        fname, page = m.group(1).strip(" ()[]"), int(m.group(2))
        match = [k for k in corpus_pages if os.path.basename(k).lower() == os.path.basename(fname).lower()]
        if not match or page < 1 or page > corpus_pages[match[0]]:
            bad.append(f"{fname} p.{page}")
    s["fabricated_refs"] = bad
    return s


JUDGE_PROMPT = """You are a strict fact-checker. You are given a FACT SHEET (the complete text of the documents the user uploaded), a QUESTION and an ANSWER written by an assistant that was supposed to answer only from those documents.

List every claim in the ANSWER about the documents' content that is NOT supported by the FACT SHEET or that contradicts it. Ignore wording, formatting and generic explanatory language that makes no factual claim about the documents. Do not penalise statements that the documents do not contain something. Do not penalise correct arithmetic derived from figures in the FACT SHEET.

Reply with ONLY this JSON: {"unsupported_claims": ["..."], "contradictions": ["..."]}

FACT SHEET:
%s

QUESTION: %s

ANSWER:
%s"""


def judge(client, fact_sheet, question, answer):
    try:
        r = client.messages.create(
            model="claude-haiku-5-5", max_tokens=1500, output_config={"effort": "low"},
            messages=[{"role": "user", "content": JUDGE_PROMPT % (fact_sheet, question, answer)}])
        txt = "".join(b.text for b in r.content if b.type == "text")
        m = re.search(r"\{.*\}", txt, re.S)
        d = json.loads(m.group(0)) if m else {}
        return {"unsupported": d.get("unsupported_claims", []), "contradictions": d.get("contradictions", [])}
    except Exception as e:
        return {"judge_error": type(e).__name__}


def pdf_text(path):
    import pypdf
    r = pypdf.PdfReader(path)
    return "\n".join(f"[page {i+1}] " + (p.extract_text() or "") for i, p in enumerate(r.pages))


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", default="")
    ap.add_argument("--backends", default="claude,gemini")
    ap.add_argument("--no-judge", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    qs = json.load(open(os.path.join(os.path.dirname(__file__), "questions.json"), encoding="utf-8"))
    if a.only:
        wanted = set(a.only.split(","))
        qs = [q for q in qs if q["id"] in wanted or q.get("after") in wanted]
    backends = a.backends.split(",")

    import pypdf
    corpus = {os.path.basename(p): os.path.join(a.corpus, p) for p in os.listdir(a.corpus) if p.endswith(".pdf")}
    pages = {k: len(pypdf.PdfReader(v).pages) for k, v in corpus.items()}
    A_docs = [k for k in corpus if k != "UserB_Confidential.pdf"]
    B_docs = ["UserB_Confidential.pdf"]
    sheet = {"A": "\n\n".join(f"=== {k} ===\n{pdf_text(corpus[k])}" for k in A_docs if k != "Scanned_Health_Advisory.pdf")
                  + "\n\n=== Scanned_Health_Advisory.pdf ===\n[page 1] HEALTH ADVISORY NOTICE. The mandatory quarantine period for arriving staff is 14 days. "
                    "Quarantine hotels are booked through the Kestrel Travel Desk. The advisory helpline number is 1800-555-0199. This notice was issued on 3 September 2025.",
             "B": "\n\n".join(f"=== {k} ===\n{pdf_text(corpus[k])}" for k in B_docs)}
    # the long handbook is mostly filler; keep the judge prompt small
    sheet["A"] = re.sub(r"(The facility follows standard operating procedures[^\[]{0,400}?)(?:\s*The facility follows[^\[]*?)+(?=\[page|\n=== |$)", r"\1 (filler repeated)", sheet["A"])

    judge_client = None
    if not a.no_judge:
        key = os.environ.get("ANTHROPIC_API_KEY") or open(os.environ["ANTHROPIC_KEY_FILE"]).read().strip()
        import anthropic
        judge_client = anthropic.Anthropic(api_key=key)

    # ---- users + indexing (once, through the Claude backend; both backends read the same stores)
    api = Api(BACKENDS["claude"])
    tag = uuid.uuid4().hex[:6]
    tokens = {"A": api.register("EVAL A", f"eval-a-{tag}@example.com", "Eval-pass-" + tag),
              "B": api.register("EVAL B", f"eval-b-{tag}@example.com", "Eval-pass-" + tag)}
    log(f"users registered (tag {tag})")
    tasks = []
    for user, docs in (("A", A_docs), ("B", B_docs)):
        sid = f"eval-upload-{user}-{tag}"
        for d in docs:
            r = api.upload(tokens[user], sid, corpus[d])
            tasks.append((user, d, r["task_id"], time.time()))
            log(f"  uploaded {d} for {user}: task queued")
    for user, d, tid, t0 in tasks:
        while True:
            st = api.status(tokens[user], tid)
            if st.get("state") in ("SUCCESS", "FAILURE"):
                break
            time.sleep(4)
            if time.time() - t0 > 900:
                break
        log(f"  indexed {d}: {st.get('state')} {st.get('status')} chunks={st.get('total_chunks_indexed')} ({int(time.time()-t0)}s)")
        if st.get("status") != "success":
            log("  !! indexing failed:", st)

    # ---- questions
    results = []
    for be in backends:
        bapi = Api(BACKENDS[be])
        sessions = {}
        for q in qs:
            sid = sessions.setdefault(q.get("after") or q["id"], f"eval-{be}-{tag}-{q.get('after') or q['id']}")
            t_start = time.time()
            r, dt = bapi.chat(tokens[q["user"]], sid, q["query"])
            try:
                js = r.json()
            except Exception:
                js = {"detail": r.text[:200]}
            usage = docker_log_usage(LLM_CONTAINER[be], t_start - 1) if be == "claude" else []
            sc = score(q, js, r.status_code, pages)
            row = dict(backend=be, id=q["id"], scenario=q["scenario"], query=q["query"], latency_s=round(dt, 1),
                       llm_calls=len(usage), input_tokens=sum(u["input"] for u in usage), output_tokens=sum(u["output"] for u in usage),
                       cache_read_tokens=sum(u["cache_read"] for u in usage), cost_usd=round(opus_cost(usage), 4) if usage else None,
                       stop_reasons=[u["stop"] for u in usage], served_by=sorted({u["served_by"] for u in usage}),
                       answer=(js.get("response") or js.get("detail") or ""), sub_queries=js.get("sub_queries_used"), followups=js.get("follow_up_questions"), **sc)
            if judge_client and r.status_code == 200 and row["answer"]:
                row["judge"] = judge(judge_client, sheet[q["user"]], q["query"], row["answer"])
            results.append(row)
            log(f"[{be}] {q['id']:5s} {q['scenario']:28s} http={r.status_code} correct={sc.get('correct')} cite_ok={sc.get('citation_ok')} {dt:5.1f}s"
                + (f" fabricated={sc['fabricated_refs']}" if sc.get("fabricated_refs") else "")
                + (f" missed={sc['missed_facts']}" if sc.get("missed_facts") else ""))
            with open(os.path.join(a.out, "results_partial.json"), "w", encoding="utf-8") as fh:
                json.dump(results, fh, indent=1, ensure_ascii=False)

    out = os.path.join(a.out, f"results_{tag}.json")
    json.dump(results, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    log("saved", out)


if __name__ == "__main__":
    sys.exit(main())
