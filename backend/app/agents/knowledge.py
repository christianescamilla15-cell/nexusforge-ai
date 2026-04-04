"""KnowledgeAgent — RAG with conversation-aware retrieval + citations."""

import json
import logging

from app.agents.base import BaseAgent, AgentResult
from app.agents.registry import register_agent

logger = logging.getLogger(__name__)

REWRITE_PROMPT = """Rewrite this follow-up question into a standalone question using the conversation context.
If it's already standalone, return it unchanged.

Conversation: {history}
Follow-up: {question}

Return ONLY the rewritten question as plain text (no JSON, no quotes)."""

KNOWLEDGE_PROMPT = """Answer the following question using ONLY the provided context.
If the context doesn't contain enough information, say "I don't have enough information to answer this."

IMPORTANT: For each claim in your answer, cite the source using [Source N] notation.

Context:
{context}

Respond ONLY with valid JSON (no markdown):
{{
  "answer": "<answer with [Source N] citations>",
  "sources": [{{"index": <N>, "doc_id": "<id>", "chunk": "<relevant excerpt>", "relevance": "<high/medium/low>"}}],
  "confidence": <0.0-1.0>,
  "needs_more_context": <true|false>
}}

Question:
{question}"""


class KnowledgeAgent(BaseAgent):
    name = "KnowledgeAgent"
    agent_type = "knowledge"
    description = "Answers questions using RAG with conversation-aware retrieval and source citations."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        question = input_data.get("question", input_data.get("text", ""))
        history = input_data.get("conversation_history", [])
        config = config or {}

        if config.get("demo") or not question:
            return AgentResult(
                output={
                    "answer": "Based on available documents, the quarterly revenue increased by 15% [Source 1].",
                    "sources": [
                        {"index": 1, "doc_id": "doc-001", "chunk": "Revenue grew 15% year-over-year...", "relevance": "high"},
                    ],
                    "confidence": 0.88,
                    "needs_more_context": False,
                },
                tokens_used=0, cost_usd=0.0,
                provider="local", model="demo",
            )

        total_tokens = 0
        total_cost = 0.0

        # Step 1: Conversation-aware query rewriting (if history exists)
        search_query = question
        if history and len(history) >= 2:
            try:
                history_text = "\n".join(
                    f"{m.get('role', 'user')}: {m.get('content', '')[:200]}"
                    for m in history[-6:]  # last 3 turns
                )
                rewrite_messages = [
                    {"role": "system", "content": "You rewrite follow-up questions into standalone questions."},
                    {"role": "user", "content": REWRITE_PROMPT.format(
                        history=history_text, question=question
                    )},
                ]
                rewrite_resp = await self._resilient_llm_call(
                    rewrite_messages, temperature=0.1, max_tokens=200
                )
                search_query = rewrite_resp.text.strip().strip('"')
                total_tokens += rewrite_resp.tokens_input + rewrite_resp.tokens_output
                total_cost += getattr(rewrite_resp, "cost_usd", 0.0)
                logger.info("KnowledgeAgent: rewritten query: %s", search_query[:100])
            except Exception as exc:
                logger.info("Query rewriting skipped: %s", exc)

        # Step 2: Retrieve context from semantic search
        context_chunks = []
        chunk_metadata = []
        try:
            from app.memory.semantic import SemanticMemory
            sem = SemanticMemory()
            memories = await sem.recall("knowledge", search_query, top_k=5)
            for i, m in enumerate(memories):
                context_chunks.append(m["content"])
                chunk_metadata.append({
                    "index": i + 1,
                    "doc_id": m.get("metadata", {}).get("doc_id", f"chunk-{i+1}"),
                    "chunk": m["content"][:200],
                    "relevance": "high" if i < 2 else ("medium" if i < 4 else "low"),
                })
        except Exception as exc:
            logger.warning("KnowledgeAgent semantic recall failed: %s", exc)

        # Build numbered context for citation tracking
        if context_chunks:
            context = "\n---\n".join(
                f"[Source {i+1}]: {chunk}" for i, chunk in enumerate(context_chunks)
            )
        else:
            context = "No relevant documents found."

        # Step 3: Generate answer with citations
        messages = [
            {"role": "system", "content": self._build_system_prompt(
                "Answer questions using document context. Always cite sources."
            )},
            {"role": "user", "content": KNOWLEDGE_PROMPT.format(
                context=context[:4000], question=question[:1000]
            )},
        ]

        try:
            resp = await self._resilient_llm_call(messages, temperature=0.2, max_tokens=1024)
            parsed = json.loads(resp.text)
            total_tokens += resp.tokens_input + resp.tokens_output
            total_cost += getattr(resp, "cost_usd", 0.0)

            # Enrich sources with actual chunk metadata
            if chunk_metadata and not parsed.get("sources"):
                parsed["sources"] = chunk_metadata
            elif chunk_metadata:
                for src in parsed.get("sources", []):
                    idx = src.get("index", 0) - 1
                    if 0 <= idx < len(chunk_metadata):
                        src["doc_id"] = chunk_metadata[idx]["doc_id"]
                        if not src.get("chunk"):
                            src["chunk"] = chunk_metadata[idx]["chunk"]

            if search_query != question:
                parsed["_rewritten_query"] = search_query

            return AgentResult(
                output=parsed,
                tokens_used=total_tokens,
                cost_usd=total_cost,
                provider=resp.provider, model=resp.model,
            )
        except Exception as exc:
            logger.warning("KnowledgeAgent LLM fallback: %s", exc)
            return AgentResult(
                output={
                    "answer": f"Unable to answer: {exc}",
                    "sources": chunk_metadata[:3],
                    "confidence": 0.0,
                    "needs_more_context": True,
                },
                tokens_used=total_tokens, cost_usd=total_cost,
                provider="local", model="fallback",
            )


register_agent("knowledge", KnowledgeAgent())
