"""
RAG core: ChromaDB retriever used by the multi-agent pipeline.
"""

import chromadb
from chromadb.utils import embedding_functions

from src.config import EMBEDDING_MODEL, CHROMA_PERSIST_DIR, CHROMA_COLLECTION_NAME, TOP_K


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


# ============================================================
# RETRIEVER — Search in ChromaDB
# ============================================================
class Retriever:
    """Searches for the most relevant chunks in ChromaDB."""

    def __init__(self):
        """Initialize the Retriever with ChromaDB client and collection."""
        self.ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL  # type: ignore
        )
        self.client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)  # type: ignore
        self.collection = self.client.get_collection(
            name=CHROMA_COLLECTION_NAME,  # type: ignore
            embedding_function=self.ef,  # type: ignore
        )

    def search(self, query: str, top_k: int = TOP_K,
               source_filter: str = None, distance_threshold: float = None) -> list[dict]:  # type: ignore
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
            n_results=top_k * 2,
            where=where_filter,  # type: ignore
        )

        chunks = []
        if results and results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                distance = results["distances"][0][i] if results["distances"] else 0
                if distance_threshold is not None and distance > distance_threshold:
                    continue
                chunks.append({
                    "text": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": distance,
                })

        return chunks[:top_k]

    def get_stats(self) -> dict:
        """Return stats about the collection."""
        return {
            "total_chunks": self.collection.count(),
            "collection": CHROMA_COLLECTION_NAME,
            "embedding_model": EMBEDDING_MODEL,
        }
