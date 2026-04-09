"""Quick command-line test for the multi-agent orchestrator."""
from src.agents import OrchestratorAgent

orchestrator = OrchestratorAgent()

# Stats
print(orchestrator.retriever.get_stats())

# Debug: inspect a question
print(f"\n{'='*80}")
print("DEBUG — Multi-agent test")
print(f"{'='*80}")
q = "How many telework days do I have? I am an executive."
result = orchestrator.answer(q, top_k=5, use_reranking=True)

print(f"\nAgents used : {result['agents_used']}")
print(f"Answer      : {result['answer'][:300]}...")
print(f"\nChunks retrieved: {len(result['chunks'])}")
for i, c in enumerate(result['chunks']):
    score = f", rerank: {c['rerank_score']:.3f}" if "rerank_score" in c else ""
    print(f"  [{i+1}] dist={c['distance']:.3f}{score} — {c['metadata'].get('document', '')}")
