
import re
import json
import inspect
from typing import Any, Dict, List, Optional, Tuple, TypedDict, Annotated
from operator import add

from langgraph.graph import StateGraph, START, END

from add_ai_core.entities.chat import ChatAnswer, Citation
from add_ai_core.entities.document import DocumentChunk
from add_ai_core.interfaces.llm_client import ILLMClient
from app.prompts.audito_system_prompt import (
    FOLLOWUP_DELIMITER,
    SOURCES_DELIMITER,
    get_system_prompt,
    uses_source_tail,
)
from app.services.retrieval_service import RetrievalService

# Prior conversation turns are sent to the model so follow-ups such as
# "explain point 3" resolve. Each prior message is capped so one very long
# earlier answer cannot crowd out the freshly retrieved evidence.
MAX_HISTORY_MESSAGE_CHARS = 4000
# Citations shown to the user when the model reports which sources it used.
MAX_CITATIONS_USED = 6


class AgentState(TypedDict):
    query: str
    user_id: str
    session_id: str
    chat_history: Annotated[list, add]
    sub_queries: List[str]
    retrieved_docs: List[DocumentChunk]
    response: str
    follow_up_questions: List[str]
    citations: List[Dict[str, Any]]
    selected_file_ids: List[str]
    history_pairs: List[Tuple[str, str]]


class ChatWorkflowService:

    def __init__(
        self,
        llm_client: ILLMClient,
        retrieval_service: RetrievalService,
        top_k_per_query: int,
        final_docs_per_query: int,
        max_total_context_docs: int,
        prompt_version: str = "audito",
    ):
        self._llm = llm_client
        self._retrieval = retrieval_service
        self._top_k_per_query = top_k_per_query
        self._final_docs_per_query = final_docs_per_query
        self._max_total_context_docs = max_total_context_docs
        self._prompt_version = prompt_version
        # Per-request tuning (max_tokens / effort) is only passed to LLM
        # clients whose `complete` accepts it, so older/fake clients keep working.
        try:
            self._llm_accepts_opts = "max_tokens" in inspect.signature(llm_client.complete).parameters
        except (TypeError, ValueError):
            self._llm_accepts_opts = False
        self._graph = self._build_graph()

    def _complete(self, messages: List[Tuple[str, str]], **opts: Any) -> str:
        if opts and self._llm_accepts_opts:
            return self._llm.complete(messages, **opts)
        return self._llm.complete(messages)

    def run(
        self,
        query: str,
        user_id: str,
        session_id: str,
        selected_file_ids: Optional[List[str]] = None,
        chat_history: Optional[List[Tuple[str, str]]] = None,
    ) -> ChatAnswer:
        """`chat_history` is the earlier turns of THIS conversation as
        (role, text) pairs with role 'user' or 'assistant', oldest first."""
        history_pairs = [(r, t) for r, t in (chat_history or []) if t and str(t).strip()]
        initial_state: AgentState = {
            "query": query,
            "user_id": user_id,
            "session_id": session_id,
            "selected_file_ids": selected_file_ids or [],
            "chat_history": [
                f"{'User' if r == 'user' else 'Bot'}: {t[:600]}" for r, t in history_pairs[-6:]
            ],
            "history_pairs": history_pairs,
            "sub_queries": [],
            "retrieved_docs": [],
            "response": "",
            "follow_up_questions": [],
            "citations": [],
        }
        result = self._graph.invoke(initial_state)
        return ChatAnswer(
            response_text=result.get("response", "No answer generated."),
            sub_queries_used=result.get("sub_queries", []),
            follow_up_questions=result.get("follow_up_questions", []),
            citations=[Citation(**c) for c in result.get("citations", [])],
        )

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("decompose", self._decompose_node)
        workflow.add_node("retrieve", self._retrieve_node)
        workflow.add_node("generate", self._generate_node)

        workflow.add_edge(START, "decompose")
        workflow.add_edge("decompose", "retrieve")
        workflow.add_edge("retrieve", "generate")
        workflow.add_edge("generate", END)

        return workflow.compile()

    def _decompose_node(self, state: AgentState) -> Dict[str, Any]:
        print(f"\n[Workflow] Stage 0: Decomposing query for User: {state['user_id']}...")
        sub_queries = self._decompose_query(state["query"], state["chat_history"])
        print(f"   -> Sub-Queries Generated: {sub_queries}")
        return {"sub_queries": sub_queries}

    def _decompose_query(self, query: str, chat_history: List[str]) -> List[str]:
        history_str = "\n".join(chat_history[-6:]) if chat_history else "No prior history."
        decomposition_prompt = (
            "You are an advanced Query Rewriter and Decomposition engine for retrieval over a user's uploaded documents "
            "(reports, contracts, policies, manuals, financial statements and similar).\n"
            "Your task is to produce 1 to 3 optimized search queries based on the user question.\n\n"
            "FOLLOW-UPS: If the user input refers back to the conversation (e.g. 'explain point 3', 'give me more details', "
            "'what about the second document', 'compare both', 'the complete process'), use the Chat History to rewrite it as "
            "fully self-contained search queries that name the actual topic, entities, figures or document it refers to. "
            "Never output a query that only makes sense with the history.\n\n"
            "CRITICAL: If the question compares, contrasts, or asks about MULTIPLE named entities/companies "
            "(e.g. 'compare Tata and Mahindra', 'net profit for both companies'), you MUST generate one separate "
            "sub-query PER entity, each explicitly naming that entity (e.g. 'Tata Motors net profit', "
            "'Mahindra net profit') — never a single merged query that risks one entity's data being outranked "
            "and dropped entirely from the retrieved context.\n\n"
            "OUTPUT REQUIREMENT:\nReturn ONLY a JSON list of strings, nothing else. Do not wrap it in markdown fences.\n\n"
            f"Chat History:\n{history_str}\n\nRaw User Input: {query}"
        )
        try:
            # Short JSON-only task: small output cap and the cheapest effort.
            raw = self._complete([("user", decomposition_prompt)], max_tokens=600, effort="low").strip()
            raw = re.sub(r"^```(json)?|```$", "", raw, flags=re.MULTILINE).strip()
            queries = json.loads(raw)
            if isinstance(queries, list) and len(queries) > 0:
                return queries[:3]
        except Exception as e:
            print(f" Query optimization failed ({e}), falling back to raw query.")
        return [query]

    def _retrieve_node(self, state: AgentState) -> Dict[str, Any]:
        print("[Workflow] Stage 1: Executing multi-doc hybrid search loop...")
        docs_by_source: Dict[str, List[DocumentChunk]] = {}
        seen = set()

        selected_file_ids = state.get("selected_file_ids") or None

        for sub_q in state["sub_queries"]:
            candidates = self._retrieval.hybrid_search(
                query=sub_q,
                user_id=state["user_id"],
                top_k=self._top_k_per_query,
                file_ids=selected_file_ids,
            )
            if not candidates:
                continue

            print(f"[Workflow] Stage 2: Cross-Encoder filtering for: '{sub_q}'")
            verified = self._retrieval.reranker.rerank(sub_q, candidates, self._final_docs_per_query)

            for doc in verified:
                key = (doc.source, doc.page, doc.content[:80])
                if key not in seen:
                    seen.add(key)
                    docs_by_source.setdefault(doc.source, []).append(doc)

        all_final_docs: List[DocumentChunk] = []
        sources = list(docs_by_source.keys())
        idx = 0
        while any(docs_by_source.values()):
            src = sources[idx % len(sources)]
            if docs_by_source[src]:
                all_final_docs.append(docs_by_source[src].pop(0))
            idx += 1
            if idx > 10000:
                break

        all_final_docs = all_final_docs[: self._max_total_context_docs]
        if all_final_docs:
            print(f"   -> Context Pipeline Ready. Top Segment Match: {all_final_docs[0].source}, Page {all_final_docs[0].page}\n")
        return {"retrieved_docs": all_final_docs}

    def _generate_node(self, state: AgentState) -> Dict[str, Any]:
        docs = state["retrieved_docs"]
        if not docs:
            return {
                "response": (
                    "I could not find information relevant to your question in your uploaded documents. "
                    "Try rephrasing the question, or check that the document that contains the answer has finished processing."
                ),
                "chat_history": [],
                "follow_up_questions": [],
                "citations": [],
            }

        context_str = self._build_context(docs)

        messages: List[Tuple[str, str]] = [("system", self._build_system_prompt())]
        messages.extend(self._history_messages(state.get("history_pairs") or []))
        messages.append((
            "user",
            "Retrieved document passages (these are the only evidence available for this answer):\n\n"
            f"{context_str}\n\nQuestion: {state['query']}",
        ))

        raw_content = self._complete(messages)
        answer_text, used_sources, follow_up_questions = self._parse_model_output(raw_content)

        if used_sources is None:
            # The model did not report which passages it used (e.g. the legacy
            # prompt): fall back to the top-ranked passages, as before.
            citation_docs, max_citations = docs, 3
        else:
            # Only passages the model says it relied on become citations; every
            # number is checked against what was really retrieved, so a citation
            # can never point at a document/page that was not in the evidence.
            citation_docs = [docs[n - 1] for n in used_sources if 1 <= n <= len(docs)]
            max_citations = MAX_CITATIONS_USED
        citations: List[Dict[str, Any]] = self._build_citations(citation_docs, max_citations=max_citations)

        return {
            "response": answer_text,
            "chat_history": [f"User: {state['query']}", f"Bot: {answer_text}"],
            "follow_up_questions": follow_up_questions,
            "citations": citations,
        }

    @staticmethod
    def _build_context(docs: List[DocumentChunk]) -> str:
        blocks = []
        for i, d in enumerate(docs, start=1):
            body = d.content
            # The parser prepends an internal "ATTENTION LLM: FILE ... | PAGE ..." line
            # to every chunk for retrieval; the SOURCE label below replaces it.
            if body.startswith("ATTENTION LLM:"):
                parts = body.split("\n", 1)
                body = parts[1] if len(parts) > 1 else ""
            blocks.append(f"[SOURCE {i} | File: {d.source} | Page: {d.page}]\n{body.strip()}")
        return "\n\n".join(blocks)

    @staticmethod
    def _history_messages(pairs: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        out: List[Tuple[str, str]] = []
        for role, text in pairs[-6:]:
            role = "assistant" if role == "assistant" else "user"
            out.append((role, text[:MAX_HISTORY_MESSAGE_CHARS]))
        while out and out[0][0] != "user":
            out.pop(0)
        return out

    @staticmethod
    def _parse_json_list(fragment: str) -> Optional[list]:
        fragment = re.sub(r"^```(json)?|```$", "", fragment.strip(), flags=re.MULTILINE).strip()
        try:
            value = json.loads(fragment)
        except Exception:
            return None
        return value if isinstance(value, list) else None

    @classmethod
    def _parse_model_output(cls, raw: str) -> Tuple[str, Optional[List[int]], List[str]]:
        """Split the model output into (visible answer, used source numbers, follow-ups).

        `used source numbers` is None when the model emitted no SOURCES tail."""
        positions = sorted(
            (raw.find(d), d) for d in (SOURCES_DELIMITER, FOLLOWUP_DELIMITER) if raw.find(d) != -1
        )
        if not positions:
            return raw.strip(), None, []

        answer = raw[: positions[0][0]].strip()
        used: Optional[List[int]] = None
        followups: List[str] = []
        for i, (start, delim) in enumerate(positions):
            end = positions[i + 1][0] if i + 1 < len(positions) else len(raw)
            parsed = cls._parse_json_list(raw[start + len(delim): end])
            if parsed is None:
                continue
            if delim == SOURCES_DELIMITER:
                used = [int(n) for n in parsed if isinstance(n, (int, float)) or str(n).isdigit()]
            else:
                followups = [str(q).strip() for q in parsed if str(q).strip()][:3]
        return answer, used, followups

    @staticmethod
    def _build_citations(retrieved_docs: List[DocumentChunk], max_citations: int = 3) -> List[Dict[str, Any]]:
        """
        Builds the citation payload the frontend uses to open the PDF
        viewer panel: which file (`file_id`), which page (`page`), a short
        `snippet` of the actual chunk text, and — for OCR'd/scanned pages
        only — a `bbox` (exact highlight region in PDF point space) plus
        the page's `page_width`/`page_height` needed to scale it.

        The snippet strips the internal "ATTENTION LLM: FILE: ... | PAGE:
        ..." scaffolding line the parser prepends to every chunk (see
        pdf_parser.py) — that line is retrieval/prompt plumbing, not real
        document text, and would never actually appear on the rendered PDF
        page, so searching for it client-side would never match anything.
        """
        citations: List[Dict[str, Any]] = []
        seen_keys = set()

        for d in retrieved_docs:
            key = (d.source, d.page)
            if key in seen_keys:
                continue
            seen_keys.add(key)

            body = d.content
            if body.startswith("ATTENTION LLM:"):
                
                parts = body.split("\n", 1)
                body = parts[1] if len(parts) > 1 else ""

            body = body.split("### Extracted Document Tables:")[0]  # drop trailing table markdown
            body = body.strip()

            # Table-derived chunks have their numbers rearranged into
            # markdown "| ... | ... |" cells that never appear verbatim on
            # the actual rendered PDF page (the page shows a real table
            # layout, not pipe-delimited text) — searching for that text
            # on the page can never succeed, so skip the highlight attempt
            # entirely rather than sending a snippet that's guaranteed not
            # to match. The frontend still scrolls to the correct page.
            if d.metadata.get("has_table"):
                snippet = None
            else:
                # 24 words (not the whole chunk) — long enough to be a
                # distinctive fingerprint that won't collide with an
                # unrelated repeated phrase elsewhere on the page, short
                # enough that the frontend's fuzzy line-matcher can still
                # tolerate a few OCR/spacing mismatches and find it.
                snippet = " ".join(body.split()[:24]) or None

            # Scanned pages have no embedded PDF text layer at all, so
            # pdf.js's client-side text search (which the frontend falls
            # back to via `snippet`) can never find anything to highlight
            # there. For those pages we instead compute the exact
            # highlight region here, from the word-level bounding boxes
            # captured during OCR (see pdf_parser.py), and send it as
            # `bbox` — the frontend draws this directly instead of
            # searching the (empty) text layer.
            bbox = None
            ocr_words = d.metadata.get("ocr_words")
            if snippet and ocr_words:
                bbox = ChatWorkflowService._find_ocr_bbox(ocr_words, snippet)

            citations.append({
                "source": d.source,
                "page": d.page,
                "file_id": d.metadata.get("file_id"),
                "snippet": snippet,
                "bbox": bbox,
                "page_width": d.metadata.get("ocr_page_width") if bbox else None,
                "page_height": d.metadata.get("ocr_page_height") if bbox else None,
            })

            if len(citations) >= max_citations:
                break

        return citations

    @staticmethod
    def _find_ocr_bbox(ocr_words: List[Dict[str, Any]], snippet: str) -> Optional[Dict[str, float]]:
        """
        Finds the run of OCR words whose text best matches the start of
        `snippet`, and returns the union of their bounding boxes (already
        in PDF point space — see pdf_parser.py). Returns None if no
        reasonable match is found (e.g. OCR mangled the text badly enough
        that the words don't line up), in which case the frontend just
        scrolls to the page without a highlight rather than drawing a
        wrong one.
        """
        target_words = snippet.split()[:8]  # first ~8 words is enough to anchor a match
        if len(target_words) < 3 or not ocr_words:
            return None

        target_norm = [w.strip(".,;:()[]\"'").lower() for w in target_words]
        page_words_norm = [w.get("text", "").strip(".,;:()[]\"'").lower() for w in ocr_words]

        best_start, best_score = None, 0
        window = len(target_norm)
        for i in range(len(page_words_norm) - window + 1):
            candidate = page_words_norm[i : i + window]
            score = sum(1 for a, b in zip(candidate, target_norm) if a == b)
            if score > best_score:
                best_score, best_start = score, i

        
        if best_start is None or best_score < window / 2:
            return None

        matched = ocr_words[best_start : best_start + window]
        return {
            "x0": min(w["x0"] for w in matched),
            "y0": min(w["y0"] for w in matched),
            "x1": max(w["x1"] for w in matched),
            "y1": max(w["y1"] for w in matched),
        }

    def _build_system_prompt(self) -> str:
        return get_system_prompt(self._prompt_version)

    @staticmethod
    def _split_answer_and_followups(raw_content: str):
        if FOLLOWUP_DELIMITER not in raw_content:
            return raw_content.strip(), []

        answer_part, _, followup_part = raw_content.partition(FOLLOWUP_DELIMITER)
        answer_part = answer_part.strip()

        followup_part = followup_part.strip()
        followup_part = re.sub(r"^```(json)?|```$", "", followup_part, flags=re.MULTILINE).strip()

        try:
            questions = json.loads(followup_part)
            if isinstance(questions, list):
                return answer_part, [str(q).strip() for q in questions if str(q).strip()][:3]
        except Exception as e:
            print(f" Follow-up question parsing failed ({e}), returning answer without follow-ups.")

        return answer_part, []