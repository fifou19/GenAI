"""
RAG pipeline: retrieval from ChromaDB + generation via LLM.
Main file that orchestrates search and response.
"""

import json
import chromadb
from chromadb.utils import embedding_functions

from src.config import (
    EMBEDDING_MODEL, CHROMA_PERSIST_DIR, CHROMA_COLLECTION_NAME, TOP_K, DISTANCE_THRESHOLD,
    RERANKING_MODEL,USE_RERANKING
)
from src.prompts import build_messages
from src.llm import call_gemini
from src.tools import TOOL_DEFINITIONS, format_tool_instructions, execute_tool_call


def extract_json_object(text: str) -> str | None:
    """Find the first complete JSON object in a text output."""
    start = text.find("{")
    while start != -1:
        depth = 0
        in_string = False
        escape = False
        for idx in range(start, len(text)):
            char = text[idx]
            if char == '"' and not escape:
                in_string = not in_string
            if in_string and char == '\\' and not escape:
                escape = True
                continue
            escape = False
            if in_string:
                continue
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start:idx + 1]
        start = text.find("{", start + 1)
    return None


def parse_tool_call(response_text: str) -> dict | None:
    json_text = extract_json_object(response_text)
    if not json_text:
        return None

    try:
        tool_call = json.loads(json_text)
        if isinstance(tool_call, dict) and "tool" in tool_call and "arguments" in tool_call:
            return tool_call
    except Exception:
        return None
    return None


# ============================================================
# RETRIEVER — Search in ChromaDB
# ============================================================
class Retriever:
    """Searches for the most relevant chunks in ChromaDB."""

    def __init__(self):
        self.ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL # type: ignore
        )
        self.client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR) # type: ignore
        self.collection = self.client.get_collection(
            name=CHROMA_COLLECTION_NAME, # type: ignore
            embedding_function=self.ef, # type: ignore
        )

    def search(self, query: str, top_k: int = TOP_K, 
               source_filter: str = None, distance_threshold: float = None) -> list[dict]: # type: ignore
        """
        Semantic search in the vector database.
        
        Args:
            query: the employee's question
            top_k: number of chunks to return
            source_filter: "gouv" or "novatech" to filter by source
            distance_threshold: distance threshold (0-2), chunks above are filtered
        
        Returns:
            List of dicts with 'text', 'metadata', 'distance'
        """
        where_filter = None
        if source_filter:
            where_filter = {"source": source_filter}

        results = self.collection.query(
            query_texts=[query],
            n_results=top_k * 2,  # Retrieve more to filter later
            where=where_filter, # type: ignore
        )

        chunks = []
        if results and results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                distance = results["distances"][0][i] if results["distances"] else 0
                
                # Filter by distance threshold when specified
                if distance_threshold is not None and distance > distance_threshold:
                    continue
                    
                chunks.append({
                    "text": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": distance,
                })

        # Return only the first top_k chunks
        return chunks[:top_k]

    def get_stats(self) -> dict:
        """Return stats about the collection."""
        count = self.collection.count()
        return {
            "total_chunks": count,
            "collection": CHROMA_COLLECTION_NAME,
            "embedding_model": EMBEDDING_MODEL,
        }


# ============================================================
# RAG CHAIN — Retrieval + Generation
# ============================================================
class RAGChain:
    """Complete pipeline: question → retrieval → LLM → answer."""

    def __init__(self):
        self.retriever = Retriever()
        self._cross_encoder = None  # lazy-loaded once on first reranking call

    def _get_cross_encoder(self):
        if self._cross_encoder is None:
            from sentence_transformers import CrossEncoder
            self._cross_encoder = CrossEncoder(RERANKING_MODEL)
        return self._cross_encoder

    def answer(self, question: str, chat_history: list[dict] = None, # type: ignore
               top_k: int = TOP_K, distance_threshold: float = DISTANCE_THRESHOLD,
               use_reranking: bool = USE_RERANKING) -> dict:
        """
        Answer a question using the RAG pipeline.
        
        Args:
            question: the employee's question
            chat_history: conversation history (optional)
            top_k: number of chunks to retrieve
            distance_threshold: threshold for filtering chunks
            use_reranking: enable the LLM reranking of chunks
        
        Returns:
            dict with 'answer', 'sources', 'chunks'
        """
        # 1. Retrieval
        chunks = self.retriever.search(question, top_k=top_k, distance_threshold=distance_threshold)
        
        # 2. Optional reranking
        if use_reranking and chunks:
            chunks = self.rerank_chunks(question, chunks, top_k=top_k)
        
        # 3. Build messages (system + few-shot + history + context + question)
        messages = build_messages(question, chunks, chat_history)

        # 4. Ask the LLM whether a tool should be used
        # Merge tool instructions into the last user message to avoid consecutive user turns
        tool_instructions = format_tool_instructions()
        messages_with_tool_prompt = messages[:-1] + [{
            "role": "user",
            "content": messages[-1]["content"] + "\n\n" + tool_instructions,
        }]

        response_text = call_gemini(messages_with_tool_prompt)
        tool_call = parse_tool_call(response_text)

        tool_result = None
        if tool_call:
            tool_result = execute_tool_call(tool_call["tool"], tool_call["arguments"])
            followup_messages = messages_with_tool_prompt + [
                {"role": "assistant", "content": f"Tool call result: {tool_result}"},
                {"role": "user", "content": "Use the tool result above to answer the original question."},
            ]
            answer = call_gemini(followup_messages)
        else:
            answer = response_text

        # 5. Extract sources for display
        sources = self._extract_sources(chunks)

        return {
            "answer": answer,
            "sources": sources,
            "chunks": chunks,
            "tool_call": tool_call,
            "tool_result": tool_result,
        }

    def rerank_chunks(self, question: str, chunks: list[dict], top_k: int = 5) -> list[dict]:
        """
        Rerank chunks using a local cross-encoder (no API call).
        Much faster and more accurate than LLM-based scoring.
        """
        if not chunks:
            return chunks

        model = self._get_cross_encoder()
        pairs = [[question, chunk["text"]] for chunk in chunks]
        scores = model.predict(pairs)

        scored_chunks = [
            {**chunk, "rerank_score": float(score)}
            for chunk, score in zip(chunks, scores)
        ]
        scored_chunks.sort(key=lambda x: -x["rerank_score"])
        return scored_chunks[:top_k]

    def _extract_sources(self, chunks: list[dict]) -> list[dict]:
        """Extract unique sources from chunks for display."""
        seen = set()
        sources = []
        for chunk in chunks:
            meta = chunk.get("metadata", {})
            doc = meta.get("document", "")
            source_type = meta.get("source", "")
            key = f"{source_type}:{doc}"
            if key not in seen:
                seen.add(key)
                sources.append({
                    "document": doc,
                    "source": source_type,
                    "filename": meta.get("filename", ""),
                    "distance": chunk.get("distance", 0),
                })
        return sources