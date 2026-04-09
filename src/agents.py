"""
Multi-agent architecture for the HR Assistant.

Agents:
  PolicyAgent      — RAG on NovaTech internal policies  (source_filter="novatech")
  LegalAgent       — RAG on French labor law docs        (source_filter="gouv")
  ActionAgent      — Tool execution: forms, checklists, HR contacts
  OrchestratorAgent— LLM-based router + synthesizer

Usage:
    from src.agents import OrchestratorAgent
    orchestrator = OrchestratorAgent()
    result = orchestrator.answer("How many telework days do I have?")
    print(result["answer"])
"""

import json

from src.rag import Retriever, extract_json_object
from src.llm import call_gemini
from src.config import TOP_K, DISTANCE_THRESHOLD, USE_RERANKING, RERANKING_MODEL
from src.tools import execute_tool_call
from prompts.rag_prompt_template import build_messages
from prompts.prompts_llm import infer_answer_language
from prompts.prompts_agents import ROUTER_SYSTEM_PROMPT, SYNTHESIS_SYSTEM_PROMPT, ACTION_AGENT_PROMPT



# ============================================================
# BASE
# ============================================================
class BaseAgent:
    name: str = "base"

    def run(self, question: str, **kwargs) -> dict:
        raise NotImplementedError


# ============================================================
# RAG BASE  (shared by PolicyAgent and LegalAgent)
# ============================================================
class RAGAgent(BaseAgent):
    """Abstract base for agents that do RAG retrieval + LLM generation."""

    source_filter: str = ""

    def __init__(self, retriever: Retriever, cross_encoder=None):
        self.retriever = retriever
        self._cross_encoder = cross_encoder

    def run(self, question: str, chat_history: list = None, # type: ignore
            top_k: int = TOP_K, distance_threshold: float = DISTANCE_THRESHOLD,
            use_reranking: bool = USE_RERANKING) -> dict: # type: ignore

        chunks = self.retriever.search(
            question,
            top_k=top_k,
            source_filter=self.source_filter,
            distance_threshold=distance_threshold,
        )

        if use_reranking and chunks and self._cross_encoder:
            chunks = self._rerank(question, chunks, top_k)

        if not chunks:
            return {"answer": None, "chunks": [], "agent": self.name}

        messages = build_messages(question, chunks, chat_history)
        answer = call_gemini(messages)

        return {"answer": answer, "chunks": chunks, "agent": self.name}

    def _rerank(self, question: str, chunks: list, top_k: int) -> list:
        pairs = [[question, c["text"]] for c in chunks]
        scores = self._cross_encoder.predict(pairs) # type: ignore
        scored = [{**c, "rerank_score": float(s)} for c, s in zip(chunks, scores)]
        scored.sort(key=lambda x: -x["rerank_score"])
        return scored[:top_k]


# ============================================================
# POLICY AGENT  — NovaTech internal docs
# ============================================================
class PolicyAgent(RAGAgent):
    name = "policy"
    source_filter = "novatech"


# ============================================================
# LEGAL AGENT  — French labor law docs
# ============================================================
class LegalAgent(RAGAgent):
    name = "legal"
    source_filter = "gouv"


# ============================================================
# ACTION AGENT  — forms, checklists, HR contacts
# ============================================================
class ActionAgent(BaseAgent):
    name = "action"
    TOOL_TYPE_MAP = {
        "get_form_link": "form",
        "generate_checklist": "checklist",
        "route_to_contact": "contact",
    }

    def run(self, question: str, **kwargs) -> dict:
        # Ask the LLM which tools to call and with what arguments
        messages = [
            {"role": "system", "content": ACTION_AGENT_PROMPT},
            {"role": "user", "content": question},
        ]
        response = call_gemini(messages)
        json_text = extract_json_object(response)

        tool_calls = []
        if json_text:
            try:
                parsed = json.loads(json_text)
                tool_calls = parsed.get("tool_calls", [])
            except Exception:
                pass

        # Execute each selected tool
        tools_results = []
        for call in tool_calls:
            tool_name = call.get("tool", "")
            arguments = call.get("arguments", {})
            result = execute_tool_call(tool_name, arguments)
            if result.get("found"):
                tools_results.append({
                    "type": self.TOOL_TYPE_MAP.get(tool_name, tool_name),
                    "tool": tool_name,
                    **result,
                })

        return {"tools": tools_results, "agent": self.name}


# ============================================================
# ORCHESTRATOR
# ============================================================
class OrchestratorAgent:
    """
    Routes the employee question to the right agents,
    collects their results, and synthesizes a final answer.
    """

    def __init__(self):
        self.retriever = Retriever()
        self._cross_encoder = None
        self.agents: dict[str, BaseAgent] = {
            "policy": PolicyAgent(self.retriever),
            "legal": LegalAgent(self.retriever),
            "action": ActionAgent(),
        }

    # --------------------------------------------------------
    # Lazy cross-encoder loader (shared across RAG agents)
    # --------------------------------------------------------
    def _get_cross_encoder(self):
        if self._cross_encoder is None:
            from sentence_transformers import CrossEncoder
            self._cross_encoder = CrossEncoder(RERANKING_MODEL)
            for name in ("policy", "legal"):
                self.agents[name]._cross_encoder = self._cross_encoder  # type: ignore
        return self._cross_encoder

    # --------------------------------------------------------
    # Routing
    # --------------------------------------------------------
    def _route(self, question: str) -> list[str]:
        """Ask the LLM which agents to invoke. Falls back to ['policy']."""
        messages = [
            {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]
        response = call_gemini(messages)
        json_text = extract_json_object(response)
        if json_text:
            try:
                parsed = json.loads(json_text)
                valid = [a for a in parsed.get("agents", []) if a in self.agents]
                if valid:
                    return valid
            except Exception:
                pass
        return ["policy"]

    # --------------------------------------------------------
    # Synthesis
    # --------------------------------------------------------
    def _synthesize(self, question: str, agent_results: dict,
                    chat_history: list = None) -> str: # type: ignore
        """Combine agent results into a single coherent answer."""
        answer_language = infer_answer_language(question)
        parts = []

        policy_result = agent_results.get("policy")
        if policy_result and policy_result.get("answer"):
            parts.append(
                f"**NovaTech Internal Policy answer:**\n{policy_result['answer']}"
            )

        legal_result = agent_results.get("legal")
        if legal_result and legal_result.get("answer"):
            parts.append(
                f"**French Labor Law answer:**\n{legal_result['answer']}"
            )

        action_result = agent_results.get("action")
        if action_result and action_result.get("tools"):
            tools_str = json.dumps(action_result["tools"], ensure_ascii=False, indent=2)
            parts.append(f"**Available HR actions (forms / checklists / contacts):**\n{tools_str}")

        # Only one agent answered — return directly, no synthesis LLM call needed
        if len(parts) == 1:
            if policy_result and policy_result.get("answer"):
                return policy_result["answer"]
            if legal_result and legal_result.get("answer"):
                return legal_result["answer"]
            # Only action tools, no text answer — ask LLM to format them
            if action_result and action_result.get("tools"):
                messages = [
                    {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
                    {
                        "role": "system",
                        "content": (
                            f"For the current request, the final answer must be written in {answer_language}. "
                            "Use the current employee question as the source of truth for language."
                        ),
                    },
                    {"role": "user", "content": (
                        f"Employee question: {question}\n\n"
                        f"Available HR actions:\n{parts[0]}\n\n"
                        "Format the above into a helpful, natural answer."
                    )},
                ]
                return call_gemini(messages)

        if not parts:
            return (
                "I don't have enough information in the available documents "
                "to answer this question. Please contact the HR team directly."
            )

        # Multiple agents — synthesize
        combined = "\n\n---\n\n".join(parts)
        messages = [
            {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
            {
                "role": "system",
                "content": (
                    f"For the current request, the final answer must be written in {answer_language}. "
                    "Use the current employee question as the source of truth for language, not previous history."
                ),
            },
        ]
        if chat_history:
            messages.extend(chat_history)
        messages.append({
            "role": "user",
            "content": (
                f"Employee question: {question}\n\n"
                f"{combined}\n\n"
                "Synthesize the above into a single, coherent, well-structured answer."
            ),
        })
        return call_gemini(messages)

    # --------------------------------------------------------
    # Main entry point
    # --------------------------------------------------------
    def answer(self, question: str, chat_history: list = None, # type: ignore
               top_k: int = TOP_K, distance_threshold: float = DISTANCE_THRESHOLD,
               use_reranking: bool = USE_RERANKING) -> dict: # type: ignore
        """
        Full pipeline: route → run agents → synthesize.

        Returns a dict with the same keys as RAGChain.answer() for drop-in compatibility:
            answer, sources, chunks, agents_used, agent_results
        """
        if use_reranking:
            self._get_cross_encoder()

        # 1. Route
        selected = self._route(question)
        print(f"    [Orchestrator] agents selected: {selected}")

        # 2. Run agents
        agent_results: dict = {}
        for name in selected:
            agent = self.agents[name]
            if isinstance(agent, RAGAgent):
                result = agent.run(
                    question,
                    chat_history=chat_history,
                    top_k=top_k,
                    distance_threshold=distance_threshold,
                    use_reranking=use_reranking,
                )
            else:
                result = agent.run(question)
            agent_results[name] = result

        # 3. Synthesize
        final_answer = self._synthesize(question, agent_results, chat_history)

        # 4. Aggregate chunks + sources
        all_chunks: list = []
        for r in agent_results.values():
            if isinstance(r, dict):
                all_chunks.extend(r.get("chunks", []))

        return {
            "answer": final_answer,
            "sources": self._extract_sources(all_chunks),
            "chunks": all_chunks,
            "agents_used": selected,
            "agent_results": agent_results,
        }

    def _extract_sources(self, chunks: list) -> list:
        seen: set = set()
        sources: list = []
        for chunk in chunks:
            meta = chunk.get("metadata", {})
            key = f"{meta.get('source', '')}:{meta.get('document', '')}"
            if key not in seen:
                seen.add(key)
                sources.append({
                    "document": meta.get("document", ""),
                    "source": meta.get("source", ""),
                    "filename": meta.get("filename", ""),
                    "distance": chunk.get("distance", 0),
                })
        return sources
