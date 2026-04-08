"""Quick RAG command-line test."""
from src.rag import RAGChain

rag = RAGChain()

# Stats
print(rag.retriever.get_stats())


# Debug: inspect chunks retrieved with reranking
print(f"\n{'='*80}")
print("DEBUG WITH RERANKING")
print(f"{'='*80}")
q = "How many telework days do I have? I am an executive."
result = rag.answer(q, top_k=5, use_reranking=True)
for i, c in enumerate(result['chunks']):
    print(f"\n--- Chunk {i+1} (dist: {c['distance']:.3f}, score: {c.get('rerank_score', 'N/A')}) ---")
    print(f"Source: {c['metadata']['document']}")
    print(f"Text: {c['text'][:300]}...")