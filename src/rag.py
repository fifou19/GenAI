"""
Pipeline RAG : retrieval depuis ChromaDB + génération via LLM.
C'est le fichier principal qui orchestre la recherche et la réponse.
"""

import chromadb
from chromadb.utils import embedding_functions

from src.config import (
    EMBEDDING_MODEL, CHROMA_PERSIST_DIR, CHROMA_COLLECTION_NAME, TOP_K
)
from src.prompts import build_messages
from src.llm import call_gemini


# ============================================================
# RETRIEVER — Recherche dans ChromaDB
# ============================================================
class Retriever:
    """Recherche les chunks les plus pertinents dans ChromaDB."""

    def __init__(self):
        self.ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL
        )
        self.client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        self.collection = self.client.get_collection(
            name=CHROMA_COLLECTION_NAME,
            embedding_function=self.ef,
        )

    def search(self, query: str, top_k: int = TOP_K, 
               source_filter: str = None) -> list[dict]:
        """
        Recherche sémantique dans la base vectorielle.
        
        Args:
            query: la question du salarié
            top_k: nombre de chunks à retourner
            source_filter: "gouv" ou "novatech" pour filtrer par source
        
        Returns:
            Liste de dicts avec 'text', 'metadata', 'distance'
        """
        where_filter = None
        if source_filter:
            where_filter = {"source": source_filter}

        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where_filter,
        )

        chunks = []
        if results and results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                chunks.append({
                    "text": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0,
                })

        return chunks

    def get_stats(self) -> dict:
        """Retourne des stats sur la collection."""
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
    """Pipeline complet : question → retrieval → LLM → réponse."""

    def __init__(self):
        self.retriever = Retriever()

    def answer(self, question: str, chat_history: list[dict] = None,
               top_k: int = TOP_K) -> dict:
        """
        Répond à une question en utilisant le RAG.
        
        Args:
            question: la question du salarié
            chat_history: historique de la conversation (optionnel)
            top_k: nombre de chunks à récupérer
        
        Returns:
            dict avec 'answer', 'sources', 'chunks'
        """
        # 1. Retrieval
        chunks = self.retriever.search(question, top_k=top_k)

        # 2. Build messages (system + few-shot + history + context + question)
        messages = build_messages(question, chunks, chat_history)

        # 3. Call LLM
        answer = call_gemini(messages)

        # 4. Extract sources for display
        sources = self._extract_sources(chunks)

        return {
            "answer": answer,
            "sources": sources,
            "chunks": chunks,
        }

    def _extract_sources(self, chunks: list[dict]) -> list[dict]:
        """Extrait les sources uniques des chunks pour l'affichage."""
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