"""
Use case: whole-document summarization. Deliberately reuses
RetrievalService.hybrid_search rather than adding a new "fetch all chunks
for a file" primitive to IVectorStore/core — a handful of broad, generic
probe queries scoped to one file_id already pulls a representative spread
of chunks across the whole document, so no vectorstore-service or
add-ai-core changes are needed for this feature.
"""
from typing import List

from add_ai_core.entities.document import DocumentChunk
from add_ai_core.interfaces.llm_client import ILLMClient
from app.services.retrieval_service import RetrievalService

# Broad, generic angles used to sample chunks from across the whole
# document — deliberately not "the user's question" (there isn't one);
# the goal is document-wide coverage, not narrow relevance to one topic.
_SUMMARY_PROBE_QUERIES = [
    "executive summary and overview",
    "key financial figures, performance and results",
    "major risks, challenges and important disclosures",
    "conclusions, outlook and highlights",
]


class SummarizationService:

    def __init__(
        self,
        llm_client: ILLMClient,
        retrieval_service: RetrievalService,
        chunks_per_probe: int = 12,
        max_context_chunks: int = 36,
    ):
        self._llm = llm_client
        self._retrieval = retrieval_service
        self._chunks_per_probe = chunks_per_probe
        self._max_context_chunks = max_context_chunks

    def summarize(self, user_id: str, file_id: str) -> str:
        chunks = self._collect_document_chunks(user_id, file_id)
        if not chunks:
            raise ValueError("No indexed content found for this document yet.")

        context_str = self._build_context(chunks)
        raw = self._llm.complete([
            ("system", self._system_prompt()),
            ("user", f"Document content:\n\n{context_str}\n\nWrite the summary now."),
        ])
        return raw.strip()

    def _collect_document_chunks(self, user_id: str, file_id: str) -> List[DocumentChunk]:
        seen_contents = set()
        collected: List[DocumentChunk] = []

        for probe in _SUMMARY_PROBE_QUERIES:
            results = self._retrieval.hybrid_search(
                query=probe,
                user_id=user_id,
                top_k=self._chunks_per_probe,
                file_ids=[file_id],
            )
            for doc in results:
                if doc.content in seen_contents:
                    continue
                seen_contents.add(doc.content)
                collected.append(doc)

        # Chronological page order reads far more coherently to the LLM than
        # retrieval-rank order, which interleaves pages unpredictably.
        collected.sort(key=lambda d: d.page if isinstance(d.page, (int, float)) else 0)
        return collected[: self._max_context_chunks]

    @staticmethod
    def _build_context(chunks: List[DocumentChunk]) -> str:
        blocks = [f"[SECTION {i} | Page: {d.page}]\n{d.content}" for i, d in enumerate(chunks, start=1)]
        return "\n\n".join(blocks)

    @staticmethod
    def _system_prompt() -> str:
        return (
            "You are an expert financial and legal auditor writing a clear, well-structured "
            "summary of a document for a busy reader.\n\n"
            "Use ONLY the facts in the provided content — never invent numbers, names, or claims "
            "that aren't there.\n\n"
            "Structure the summary as:\n"
            "1. A short 2-3 sentence overview paragraph.\n"
            "2. A '## Key Highlights' section with concise bullet points covering the most "
            "important facts, figures, and findings.\n"
            "3. If the document discusses risks, concerns, or challenges, add a "
            "'## Risks & Considerations' section with bullet points.\n\n"
            "Write in clean Markdown. Do not mention 'sections', 'chunks', or any retrieval "
            "scaffolding — write as if you personally read the entire document."
        )
