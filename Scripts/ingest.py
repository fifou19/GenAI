"""
Pipeline d'ingestion pour l'assistant RH.
Chunking amélioré :
  - NovaTech : split sur ## (1 chunk = 1 article), préfixé avec le titre du doc
  - Gouv : split sur les questions/titres
  - Fallback : split par taille avec overlap

Usage:
    cd hr-assistant
    python data/ingest.py
"""

import os
import re
import hashlib
import sys
from pathlib import Path

import pdfplumber
import chromadb
from chromadb.utils import embedding_functions

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import (
    EMBEDDING_MODEL, CHROMA_PERSIST_DIR, CHROMA_COLLECTION_NAME,
    CHUNK_SIZE, CHUNK_OVERLAP, GOUV_DIR, NOVATECH_DIR
)


# ============================================================
# 1. Extraction texte PDF
# ============================================================
def extract_text_from_pdf(pdf_path: str) -> str:
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"
    except Exception as e:
        print(f"  ⚠ Erreur extraction {pdf_path}: {e}")
    return text.strip()


# ============================================================
# 2. Nettoyage
# ============================================================
def clean_extracted_text(text: str, source_type: str) -> str:
    if source_type == "gouv":
        text = re.sub(r"service-public\.fr\s+Le site officiel.*", "", text)
        text = re.sub(r"Source\s*:.*?Page\s*\d+", "", text)
        for pattern in [
            r"Ajouter à mes favoris.*?Lien copié",
            r"Ce sujet a été ajouté.*?mise à jour\.",
            r"Vous devez vous connecter.*?cette page\.",
            r"Le lien vers cette page.*?destinataires\.",
            r"Cette page vous a-t-elle.*?la page",
            r"L'équipe Service Public.*?du site\.",
            r"Vos remarques pour améliorer.*",
            r"Avez-vous rencontré.*",
            r"Avez-vous des suggestions.*",
            r"horaires\s*Lundi.*?Vendredi.*?\d{2}h\d{2}",
            r"Être rappelé\(e\).*?Gratuit",
            r"Il ne répond pas aux questions.*?patronales\.",
            r"Répondez aux questions successives.*?automatiquement",
        ]:
            text = re.sub(pattern, "", text, flags=re.DOTALL | re.IGNORECASE)
    else:
        text = re.sub(r"NovaTech Solutions SAS.*?Page\s*\d+", "", text)
        text = re.sub(r"Document interne\s*—\s*Confidentiel", "", text)

    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ============================================================
# 3. Chunking NovaTech — split sur ## headers
# ============================================================
def chunk_novatech(text: str) -> list[dict]:
    """
    1 chunk = 1 article (##). Chaque chunk est préfixé avec le titre du document
    pour que le retriever sache toujours de quel document il s'agit.
    Si un article est trop long, re-split sur ### puis par taille.
    """
    # Titre du document
    doc_title = ""
    m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    if m:
        doc_title = m.group(1).strip()

    # Split sur ##
    sections = re.split(r"(?=^##\s+)", text, flags=re.MULTILINE)

    chunks = []
    for section in sections:
        section = section.strip()
        if len(section) < 50:
            continue

        # Titre de la section
        section_title = ""
        sm = re.match(r"^##\s+(.+)$", section, re.MULTILINE)
        if sm:
            section_title = sm.group(1).strip()

        # Si trop long → re-split sur ###
        if len(section) > CHUNK_SIZE * 2:
            sub_sections = re.split(r"(?=^###\s+)", section, flags=re.MULTILINE)
            for sub in sub_sections:
                sub = sub.strip()
                if len(sub) < 50:
                    continue
                if len(sub) > CHUNK_SIZE * 2:
                    for sc in chunk_by_size(sub):
                        chunks.append({"text": sc, "section_title": section_title})
                else:
                    chunks.append({"text": sub, "section_title": section_title})
        else:
            chunks.append({"text": section, "section_title": section_title})

    # Préfixer avec le titre du document
    for chunk in chunks:
        if doc_title and not chunk["text"].startswith("#"):
            chunk["text"] = f"[{doc_title}]\n\n{chunk['text']}"

    if len(chunks) <= 1 and len(text) > CHUNK_SIZE:
        return [{"text": t, "section_title": ""} for t in chunk_by_size(text)]

    return chunks


# ============================================================
# 4. Chunking Gouv — split sur les questions
# ============================================================
def chunk_gouv(text: str) -> list[dict]:
    """Split sur les questions typiques de service-public.fr."""
    sections = re.split(
        r"(?=(?:Qu(?:el|'est-ce|i |and |uelle)|Comment |Combien |Peut-on |"
        r"Le salarié |Un salarié |Y a-t|Qui est concern|"
        r"L'employeur |Conditions|Montant|Durée|Mode de calcul|"
        r"Quand débute|Pendant combien|L'accident|Qu'est-ce qu))",
        text
    )

    chunks = []
    for section in sections:
        section = section.strip()
        if len(section) < 80:
            continue

        section_title = ""
        first_line = section.split("\n")[0].strip()
        if first_line.endswith("?") or len(first_line) < 120:
            section_title = first_line

        if len(section) > CHUNK_SIZE * 2:
            for sc in chunk_by_size(section):
                chunks.append({"text": sc, "section_title": section_title})
        else:
            chunks.append({"text": section, "section_title": section_title})

    if len(chunks) <= 1 and len(text) > CHUNK_SIZE:
        return [{"text": t, "section_title": ""} for t in chunk_by_size(text)]

    return chunks


# ============================================================
# 5. Fallback par taille
# ============================================================
def chunk_by_size(text: str) -> list[str]:
    chunks = []
    sentences = re.split(r"(?<=[.!?])\s+", text)
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) > CHUNK_SIZE and current:
            chunks.append(current.strip())
            overlap = current[-CHUNK_OVERLAP:] if len(current) > CHUNK_OVERLAP else ""
            current = overlap + " " + sentence
        else:
            current += " " + sentence
    if current.strip():
        chunks.append(current.strip())
    return chunks


# ============================================================
# 6. Chargement PDF
# ============================================================
def load_all_documents() -> list[dict]:
    documents = []

    for source_dir, source_type in [(GOUV_DIR, "gouv"), (NOVATECH_DIR, "novatech")]:
        if not os.path.exists(source_dir):
            print(f"  ⚠ Dossier non trouvé : {source_dir}")
            continue

        pdf_files = sorted(Path(source_dir).glob("*.pdf"))
        print(f"\n  [{source_type.upper()}] {len(pdf_files)} PDF dans {source_dir}/")

        for pdf_path in pdf_files:
            print(f"    → {pdf_path.name}", end="")
            raw_text = extract_text_from_pdf(str(pdf_path))
            if not raw_text:
                print(" ⚠ vide")
                continue

            clean_text = clean_extracted_text(raw_text, source_type)

            if source_type == "novatech":
                chunk_results = chunk_novatech(clean_text)
            else:
                chunk_results = chunk_gouv(clean_text)

            print(f" → {len(chunk_results)} chunks")

            for i, chunk_data in enumerate(chunk_results):
                text = chunk_data["text"] if isinstance(chunk_data, dict) else chunk_data
                section = chunk_data.get("section_title", "") if isinstance(chunk_data, dict) else ""

                documents.append({
                    "text": text,
                    "metadata": {
                        "source": source_type,
                        "document": pdf_path.stem,
                        "filename": pdf_path.name,
                        "section": section,
                        "chunk_index": i,
                        "total_chunks": len(chunk_results),
                    }
                })

    return documents


# ============================================================
# 7. Indexation ChromaDB
# ============================================================
def index_documents(documents: list[dict]) -> None:
    print(f"\n  Modèle embedding : {EMBEDDING_MODEL}")
    print(f"  Collection : {CHROMA_COLLECTION_NAME}")

    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)

    try:
        client.delete_collection(name=CHROMA_COLLECTION_NAME)
        print("  Collection existante supprimée")
    except Exception:
        pass

    collection = client.create_collection(
        name=CHROMA_COLLECTION_NAME,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"}
    )

    ids, texts, metadatas = [], [], []
    for doc in documents:
        doc_id = hashlib.md5(
            f"{doc['metadata']['document']}_{doc['metadata']['chunk_index']}_{doc['text'][:100]}".encode()
        ).hexdigest()
        ids.append(doc_id)
        texts.append(doc["text"])
        metadatas.append(doc["metadata"])

    batch_size = 500
    for i in range(0, len(ids), batch_size):
        end = min(i + batch_size, len(ids))
        collection.add(ids=ids[i:end], documents=texts[i:end], metadatas=metadatas[i:end])
        print(f"  Indexé {end}/{len(ids)} chunks")

    print(f"\n  ✓ {len(ids)} chunks indexés → {CHROMA_PERSIST_DIR}/")

    gouv = sum(1 for m in metadatas if m["source"] == "gouv")
    nova = sum(1 for m in metadatas if m["source"] == "novatech")
    print(f"    Gouv : {gouv} chunks")
    print(f"    NovaTech : {nova} chunks")

    print(f"\n  Détail NovaTech :")
    for m in metadatas:
        if m["source"] == "novatech" and m["chunk_index"] == 0:
            print(f"    {m['document']} — {m['total_chunks']} chunks")


# ============================================================
# MAIN
# ============================================================
def main():
    print(f"\n{'='*50}")
    print(f"  HR Assistant — Ingestion Pipeline v2")
    print(f"  Chunking : ## headers (NovaTech) + questions (Gouv)")
    print(f"{'='*50}")

    print("\n[1/2] Chargement et chunking des PDF...")
    documents = load_all_documents()

    if not documents:
        print("\n  ✗ Aucun document. Vérifiez data/gouv/ et data/novatech/")
        return

    total = len(documents)
    gouv = sum(1 for d in documents if d["metadata"]["source"] == "gouv")
    nova = sum(1 for d in documents if d["metadata"]["source"] == "novatech")
    print(f"\n  Total : {total} chunks (gouv: {gouv}, novatech: {nova})")

    print("\n[2/2] Indexation ChromaDB...")
    index_documents(documents)

    print(f"\n{'='*50}")
    print(f"  ✓ Ingestion terminée !")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()