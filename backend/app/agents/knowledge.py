"""KnowledgeAgent — RAG over processed documents using semantic memory."""

import json
import logging

from app.agents.base import BaseAgent, AgentResult
from app.agents.registry import register_agent
from app.llm.router import get_router

logger = logging.getLogger(__name__)

KNOWLEDGE_PROMPT = """Answer the following question using ONLY the provided context.
If the context doesn't contain enough information, say so.

Context:
{context}

Respond ONLY with valid JSON (no markdown):
{{"answer": "<answer>", "sources": [{{"doc_id": "<id>", "chunk": "<relevant excerpt>", "relevance": "<high/medium/low>"}}], "confidence": <0.0-1.0>}}

Question:
{question}"""


class KnowledgeAgent(BaseAgent):
    name = "KnowledgeAgent"
    agent_type = "knowledge"
    description = "Answers questions using RAG over processed documents and semantic memory."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        question = input_data.get("question", input_data.get("text", ""))
        config = config or {}

        if config.get("demo") or not question:
            return AgentResult(
                output={
                    "answer": "Demo answer — based on available documents, the quarterly revenue increased by 15%.",
                    "sources": [
                        {"doc_id": "doc-001", "chunk": "Revenue grew 15% year-over-year...", "relevance": "high"},
                    ],
                    "confidence": 0.88,
                },
                tokens_used=710, cost_usd=0.0042,
                provider="groq", model="llama-3.3-70b-versatile",
            )

        # Retrieve context from semantic search
        context_chunks = []
        try:
            from app.memory.semantic import SemanticMemory
            sem = SemanticMemory()
            memories = await sem.recall("knowledge", question, top_k=5)
            context_chunks = [m["content"] for m in memories]
        except Exception as exc:
            logger.warning("KnowledgeAgent semantic recall failed: %s", exc)

        context = "\n---\n".join(context_chunks) if context_chunks else "No relevant documents found."
        messages = [
            {"role": "system", "content": self._build_system_prompt("Answer questions using document context.")},
            {"role": "user", "content": KNOWLEDGE_PROMPT.format(context=context[:4000], question=question[:1000])},
        ]

        try:
            router = get_router()
            resp = await router.chat(messages, temperature=0.2, max_tokens=1024)
            parsed = json.loads(resp.text)
            return AgentResult(
                output=parsed,
                tokens_used=resp.tokens_input + resp.tokens_output,
                cost_usd=getattr(resp, "cost_usd", 0.0),
                provider=resp.provider, model=resp.model,
            )
        except Exception as exc:
            logger.warning("KnowledgeAgent LLM fallback: %s", exc)
            return AgentResult(
                output={"answer": f"Unable to answer: {exc}", "sources": [], "confidence": 0.0},
                tokens_used=280, cost_usd=0.0017,
                provider="groq", model="llama-3.3-70b-versatile",
            )


register_agent("knowledge", KnowledgeAgent())
