"""Test rapide du RAG en ligne de commande."""
from src.rag import RAGChain

rag = RAGChain()

# Stats
print(rag.retriever.get_stats())

# Test
questions = [
    "J'ai combien de jours de télétravail ? Je suis cadre.",
    "Mon père est décédé, j'ai droit à combien de jours ?",
    "C'est quoi la politique sur le droit de grève ?",
]

for q in questions:
    print(f"\n{'='*60}")
    print(f"Question : {q}")
    print(f"{'='*60}")
    result = rag.answer(q)
    print(f"\n{result['answer']}")
    print(f"\nSources : {[s['document'] for s in result['sources']]}")
    
    
# Debug : voir les chunks récupérés
q = "J'ai combien de jours de télétravail ? Je suis cadre."
chunks = rag.retriever.search(q, top_k=5)
for i, c in enumerate(chunks):
    print(f"\n--- Chunk {i+1} (distance: {c['distance']:.3f}) ---")
    print(f"Source: {c['metadata']['document']}")
    print(f"Text: {c['text'][:300]}...")