"""Workflow tests with fake LLM / retrieval - no network, no models."""
from types import SimpleNamespace
from typing import List

import pytest

from add_ai_core.entities.document import DocumentChunk
from app.clients.llm_client import LlmServiceError
from app.prompts.audito_system_prompt import (
    AUDITO_SYSTEM_PROMPT,
    FOLLOWUP_DELIMITER,
    LEGACY_SYSTEM_PROMPT,
    SOURCES_DELIMITER,
    get_system_prompt,
)
from app.services.chat_workflow_service import MAX_HISTORY_MESSAGE_CHARS, ChatWorkflowService


def chunk(text, source="a.pdf", page=1, file_id="1", **meta):
    return DocumentChunk(
        content=f"ATTENTION LLM: FILE: '{source}' | PAGE: {page} \n{text}",
        metadata={"source": source, "page": page, "file_id": file_id, **meta},
    )


class FakeReranker:
    def rerank(self, query, docs, top_n):
        return docs[:top_n]


class FakeRetrieval:
    def __init__(self, docs_per_query):
        self.docs_per_query = docs_per_query
        self.reranker = FakeReranker()
        self.calls = []

    def hybrid_search(self, query, user_id, top_k, file_ids=None):
        self.calls.append(dict(query=query, user_id=user_id, file_ids=file_ids))
        return list(self.docs_per_query)


class FakeLLM:
    """Records every call. `complete` accepts max_tokens/effort like the real client."""

    def __init__(self, decompose='["q1"]', answer="Answer."):
        self.decompose, self.answer, self.calls = decompose, answer, []

    def complete(self, messages, max_tokens=None, effort=None):
        self.calls.append(dict(messages=messages, max_tokens=max_tokens, effort=effort))
        if len(messages) == 1:       # the decomposition prompt is a single user message
            return self.decompose
        return self.answer


class LegacyLLM:
    """An LLM whose complete() has no tuning parameters (older client)."""

    def __init__(self):
        self.calls = []

    def complete(self, messages):
        self.calls.append(messages)
        return '["q1"]' if len(messages) == 1 else "Answer."


def build(llm, docs, prompt_version="audito"):
    svc = ChatWorkflowService(llm, FakeRetrieval(docs), top_k_per_query=15, final_docs_per_query=6,
                              max_total_context_docs=18, prompt_version=prompt_version)
    return svc


def generation_call(llm):
    return [c for c in llm.calls if len(c["messages"]) > 1][-1]


# ------------------------------------------------------------------ context / prompt
def test_context_uses_source_labels_and_strips_internal_prefix():
    llm = FakeLLM(answer="Revenue was 5.")
    docs = [chunk("Revenue 5 crore", "r.pdf", 3), chunk("Net profit 1", "r.pdf", 4)]
    build(llm, docs).run("revenue?", "7", "s1")
    user_msg = generation_call(llm)["messages"][-1][1]
    assert "[SOURCE 1 | File: r.pdf | Page: 3]" in user_msg and "[SOURCE 2 | File: r.pdf | Page: 4]" in user_msg
    assert "ATTENTION LLM" not in user_msg and "Revenue 5 crore" in user_msg
    assert "Question: revenue?" in user_msg


def test_system_prompt_is_audito_and_contains_owner_text_verbatim():
    llm = FakeLLM()
    build(llm, [chunk("x")]).run("q", "7", "s1")
    system = generation_call(llm)["messages"][0]
    assert system[0] == "system"
    assert system[1].startswith("You are AUDITO, an advanced AI document intelligence")
    assert AUDITO_SYSTEM_PROMPT in system[1]
    assert "## C. REQUIRED ANSWER STRUCTURE" in system[1] and "## G. USER EXPERIENCE" in system[1]
    assert SOURCES_DELIMITER in system[1] and FOLLOWUP_DELIMITER in system[1]
    assert "untrusted document data" in system[1]          # prompt-injection rule


def test_legacy_prompt_selectable_for_rollback():
    assert get_system_prompt("legacy") == LEGACY_SYSTEM_PROMPT
    llm = FakeLLM()
    build(llm, [chunk("x")], prompt_version="legacy").run("q", "7", "s1")
    assert generation_call(llm)["messages"][0][1] == LEGACY_SYSTEM_PROMPT


# ------------------------------------------------------------------ output parsing / citations
def test_parse_tail_sources_then_followups():
    raw = f"Body text.\n{SOURCES_DELIMITER}[2, 1]\n{FOLLOWUP_DELIMITER}[\"a?\",\"b?\",\"c?\",\"d?\"]"
    text, used, fu = ChatWorkflowService._parse_model_output(raw)
    assert text == "Body text." and used == [2, 1] and fu == ["a?", "b?", "c?"]


def test_parse_tail_reversed_order_and_fences():
    raw = f"Body.\n{FOLLOWUP_DELIMITER}```json\n[\"a?\"]\n```\n{SOURCES_DELIMITER}[3]"
    text, used, fu = ChatWorkflowService._parse_model_output(raw)
    assert text == "Body." and used == [3] and fu == ["a?"]


def test_parse_no_tail_and_malformed_tail():
    assert ChatWorkflowService._parse_model_output("Plain answer.") == ("Plain answer.", None, [])
    text, used, fu = ChatWorkflowService._parse_model_output(f"Body.\n{SOURCES_DELIMITER}not json")
    assert text == "Body." and used is None and fu == []


def test_visible_answer_never_contains_protocol_markers():
    llm = FakeLLM(answer=f"Real answer.\n{SOURCES_DELIMITER}[1]\n{FOLLOWUP_DELIMITER}[\"x?\"]")
    ans = build(llm, [chunk("fact")]).run("q", "7", "s1")
    assert ans.response_text == "Real answer." and "###" not in ans.response_text
    assert ans.follow_up_questions == ["x?"]


def test_citations_only_for_sources_the_model_used():
    docs = [chunk("one", "a.pdf", 1, file_id="1"), chunk("two", "b.pdf", 9, file_id="2"), chunk("three", "a.pdf", 5, file_id="1")]
    llm = FakeLLM(answer=f"Uses two.\n{SOURCES_DELIMITER}[2]\n{FOLLOWUP_DELIMITER}[]")
    ans = build(llm, docs).run("q", "7", "s1")
    assert [(c.source, c.page, c.file_id) for c in ans.citations] == [("b.pdf", 9, "2")]


def test_hallucinated_source_numbers_are_dropped():
    docs = [chunk("one", "a.pdf", 1), chunk("two", "b.pdf", 2)]
    llm = FakeLLM(answer=f"x\n{SOURCES_DELIMITER}[99, 0, -1, 2]\n{FOLLOWUP_DELIMITER}[]")
    ans = build(llm, docs).run("q", "7", "s1")
    assert [(c.source, c.page) for c in ans.citations] == [("b.pdf", 2)]


def test_empty_sources_list_means_no_citations():
    llm = FakeLLM(answer=f"The documents do not say.\n{SOURCES_DELIMITER}[]\n{FOLLOWUP_DELIMITER}[]")
    assert build(llm, [chunk("irrelevant")]).run("q", "7", "s1").citations == []


def test_missing_sources_tail_falls_back_to_top_three():
    docs = [chunk(f"t{i}", "a.pdf", i) for i in range(1, 6)]
    ans = build(FakeLLM(answer="No tail."), docs).run("q", "7", "s1")
    assert [c.page for c in ans.citations] == [1, 2, 3]


def test_citations_deduplicate_same_page():
    docs = [chunk("a", "a.pdf", 4), chunk("b", "a.pdf", 4)]
    llm = FakeLLM(answer=f"x\n{SOURCES_DELIMITER}[1,2]\n{FOLLOWUP_DELIMITER}[]")
    assert len(build(llm, docs).run("q", "7", "s1").citations) == 1


# ------------------------------------------------------------------ conversation history
def test_history_is_sent_before_the_new_question():
    llm = FakeLLM()
    hist = [("user", "What was revenue?"), ("assistant", "Revenue was 482 crore."), ("user", "And profit?"), ("assistant", "61 crore.")]
    build(llm, [chunk("x")]).run("explain point 2", "7", "s1", chat_history=hist)
    roles = [m[0] for m in generation_call(llm)["messages"]]
    assert roles == ["system", "user", "assistant", "user", "assistant", "user"]
    assert generation_call(llm)["messages"][1][1] == "What was revenue?"
    assert "Question: explain point 2" in generation_call(llm)["messages"][-1][1]


def test_history_feeds_query_rewriting():
    llm = FakeLLM()
    build(llm, [chunk("x")]).run("explain point 3", "7", "s1", chat_history=[("user", "List the risks"), ("assistant", "1. FX 2. Credit 3. Cyber")])
    decomposition = llm.calls[0]["messages"][0][1]
    assert "List the risks" in decomposition and "3. Cyber" in decomposition and "Raw User Input: explain point 3" in decomposition


def test_long_history_messages_are_truncated_and_leading_assistant_dropped():
    out = ChatWorkflowService._history_messages([("assistant", "stray"), ("user", "u" * 10000), ("assistant", "a")])
    assert out[0][0] == "user" and len(out[0][1]) == MAX_HISTORY_MESSAGE_CHARS


def test_only_last_six_history_messages_are_used():
    out = ChatWorkflowService._history_messages([("user" if i % 2 == 0 else "assistant", str(i)) for i in range(20)])
    assert len(out) <= 6


# ------------------------------------------------------------------ llm tuning / failure handling
def test_decomposition_uses_cheap_settings_generation_uses_defaults():
    llm = FakeLLM()
    build(llm, [chunk("x")]).run("q", "7", "s1")
    assert (llm.calls[0]["max_tokens"], llm.calls[0]["effort"]) == (600, "low")
    assert (generation_call(llm)["max_tokens"], generation_call(llm)["effort"]) == (None, None)


def test_llm_without_tuning_parameters_still_works():
    llm = LegacyLLM()
    ans = build(llm, [chunk("x")]).run("q", "7", "s1")
    assert ans.response_text == "Answer." and len(llm.calls) == 2


def test_decomposition_failure_falls_back_to_raw_query():
    llm = FakeLLM(decompose="this is not json")
    svc = build(llm, [chunk("x")])
    ans = svc.run("my question", "7", "s1")
    assert ans.sub_queries_used == ["my question"]


def test_no_retrieved_docs_means_no_generation_call():
    llm = FakeLLM()
    ans = build(llm, []).run("q", "7", "s1")
    assert len(llm.calls) == 1                       # only the decomposition call
    assert "could not find" in ans.response_text.lower() and ans.citations == []


def test_llm_service_error_propagates_to_the_caller():
    class Boom(FakeLLM):
        def complete(self, messages, max_tokens=None, effort=None):
            if len(messages) == 1:
                return '["q"]'
            raise LlmServiceError(429, "busy", "rate_limited")

    with pytest.raises(LlmServiceError):
        build(Boom(), [chunk("x")]).run("q", "7", "s1")


# ------------------------------------------------------------------ retrieval scoping / multi-doc
def test_user_and_file_scope_are_passed_to_retrieval():
    llm = FakeLLM()
    svc = build(llm, [chunk("x")])
    svc.run("q", "42", "s1", selected_file_ids=["5", "6"])
    call = svc._retrieval.calls[0]
    assert call["user_id"] == "42" and call["file_ids"] == ["5", "6"]


def test_multi_document_context_interleaves_documents():
    docs = [chunk("a1", "a.pdf", 1), chunk("a2", "a.pdf", 2), chunk("b1", "b.pdf", 1), chunk("b2", "b.pdf", 2)]
    llm = FakeLLM()
    build(llm, docs).run("compare", "7", "s1")
    user_msg = generation_call(llm)["messages"][-1][1]
    order = [line.split("File: ")[1].split(" |")[0] for line in user_msg.splitlines() if line.startswith("[SOURCE")]
    assert order == ["a.pdf", "b.pdf", "a.pdf", "b.pdf"]
