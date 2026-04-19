#!/usr/bin/env python3
"""
Generate the NovaTech Solutions corpus via Gemini API.
Article-by-article approach:
  1. For each theme, request the structure from Gemini (list of articles)
  2. Then generate each article separately
  3. Concatenate everything into a complete Markdown file

Usage:
    pip install google-genai pdfplumber
    export GEMINI_API_KEY=your_key_here
    python scripts/generate_corpus.py
"""

import os
import re
import json
import time
import random
from pathlib import Path
import pdfplumber
from google import genai
from google.genai import types
from Scripts.md_to_pdf import convert_all_to_pdf

from src.config import ( GEMINI_API_KEY , TEMPERATURES,MAX_RETRIES, BASE_WAIT, MAX_WAIT, SLEEP_BETWEEN_CALLS, GOUV_DIR, NOVATECH_DIR, NOVATECH_MD_DIR , GEMINI_MODEL,is_retryable_error)

from prompts.prompt_generate_corpus import SYSTEM_STRUCTURE, SYSTEM_ARTICLE,THEMES

# ============================================================
# GEMINI CALL WITH RETRY
# ============================================================
def call_gemini(client, system: str, prompt: str, temperature: float ) -> str:
    """Call Gemini with retry and backoff."""
    last_exc = None
    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    temperature=TEMPERATURES,
                    max_output_tokens=4096,
                ),
            )
            text = response.text
            if text is None:
                print(f"    Empty response (attempt {attempt+1})")
                time.sleep(BASE_WAIT)
                continue
            return text.strip()
        except Exception as e:
            last_exc = e
            if not is_retryable_error(e):
                raise
            wait = min(BASE_WAIT * (2 ** attempt) + random.uniform(0, 1.5), MAX_WAIT)
            print(f"    Retry {attempt+1}/{MAX_RETRIES} — waiting {wait:.0f}s ({e})")
            time.sleep(wait)

    raise RuntimeError(f"Failed after {MAX_RETRIES} retries") from last_exc


# ============================================================
# PDF EXTRACTION
# ============================================================
def extract_pdf_text(pdf_path: str, max_chars: int = 8000) -> str:
    """Extract text from a PDF file."""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
                if len(text) > max_chars:
                    break
    except Exception as e:
        print(f"  ⚠ Error reading {pdf_path}: {e}")
    return text[:max_chars].strip()


def load_gouv_texts() -> dict:
    """Load text from government PDF files."""
    texts = {}
    if not GOUV_DIR.exists():
        print(f"  ⚠ {GOUV_DIR} not found")
        return texts
    for pdf in sorted(GOUV_DIR.glob("*.pdf")):
        text = extract_pdf_text(str(pdf))
        if text:
            texts[pdf.stem] = text
            print(f"  ✓ {pdf.name} ({len(text)} chars)")
    return texts





# ============================================================
# STEP 1: GET DOCUMENT STRUCTURE
# ============================================================
def get_document_structure(client, theme: dict, gouv_context: str) -> list[str]:
    """Asks Gemini to return a JSON list of article titles for the document."""
    prompt = f"""Document theme: {theme['title']}

Content to cover: {theme['description']}

{gouv_context}

Return a JSON array of article titles (in French) that should compose this HR policy document. Include an introduction and a contact block at the end. Typically 5-8 articles."""

    result = call_gemini(client, SYSTEM_STRUCTURE, prompt, temperature=TEMPERATURES)

    # Parse JSON from response (handle markdown code blocks)
    result = result.strip()
    if result.startswith("```"):
        result = re.sub(r"```(?:json)?\s*", "", result)
        result = result.rstrip("`").strip()

    try:
        articles = json.loads(result)
        if isinstance(articles, list) and all(isinstance(a, str) for a in articles):
            return articles
    except json.JSONDecodeError:
        pass

    # Fallback: try to extract array from text
    match = re.search(r'\[.*\]', result, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    print(f"    ⚠ Could not parse structure, using default")
    return [
        "Introduction",
        "Article 1 — Dispositions générales",
        "Article 2 — Règles applicables",
        "Article 3 — Procédures",
        "Article 4 — Cas particuliers",
        "Contact"
    ]


# ============================================================
# STEP 2: GENERATE EACH ARTICLE
# ============================================================
def generate_article(client, theme: dict, article_title: str, article_index: int,
                     total_articles: int, gouv_context: str, previous_articles: str) -> str:
    """Generates one article/section of the document."""

    prompt = f"""You are writing the document: "{theme['title']}" for NovaTech Solutions.

The full document has {total_articles} sections. You are writing section {article_index + 1}: "{article_title}".

Content guidelines for this document: {theme['description']}

{gouv_context}

Here are the sections already written (for context and consistency):
---
{previous_articles if previous_articles else "(This is the first section)"}
---

Now write ONLY the section "{article_title}". Use ## for the section title. Be thorough and detailed for this specific section. Include tables where relevant. Write 150-400 words for this section."""

    return call_gemini(client, SYSTEM_ARTICLE, prompt, temperature=TEMPERATURES)


# ============================================================
# BUILD LEGAL CONTEXT
# ============================================================
def build_gouv_context(theme: dict, gouv_texts: dict) -> str:
    """Build legal context from government texts."""
    gouv_keys = theme.get("gouv_keys", [])
    matched = [gouv_texts[k] for k in gouv_keys if k in gouv_texts]
    if not matched:
        return ""
    context = "Here is the relevant French labor law context (from service-public.fr):\n\n"
    context += "--- LEGAL CONTEXT START ---\n"
    for text in matched:
        context += text[:4000] + "\n---\n"
    context += "--- LEGAL CONTEXT END ---\n"
    return context


# ============================================================
# MAIN GENERATION PIPELINE
# ============================================================
def generate_document(client, theme: dict, gouv_texts: dict) -> str:
    """Generates a complete document article by article."""
    gouv_context = build_gouv_context(theme, gouv_texts)
    has_context = bool(gouv_context)

    print(f"\n  {'='*50}")
    print(f"  {theme['title']}")
    print(f"  {'+ legal context' if has_context else '(no legal context)'}")
    print(f"  {'='*50}")

    # Step 1: Get structure
    print(f"  [1] Getting document structure...")
    articles = get_document_structure(client, theme, gouv_context)
    print(f"      → {len(articles)} sections: {', '.join(articles)}")
    time.sleep(SLEEP_BETWEEN_CALLS)

    # Step 2: Generate each article
    header = f"# {theme['title']} — NovaTech Solutions\n\n"
    header += f"**Internal document — Version 2025**\n"
    header += f"**Human Resources Department**\n\n---\n\n"

    full_document = header
    generated_so_far = ""

    for i, article_title in enumerate(articles):
        print(f"  [{i+2}] Generating: {article_title}...")

        article_content = generate_article(
            client, theme, article_title, i,
            len(articles), gouv_context, generated_so_far
        )

        full_document += article_content + "\n\n"
        generated_so_far += article_content + "\n\n"

        print(f"      → {len(article_content)} chars")
        time.sleep(SLEEP_BETWEEN_CALLS)

    return full_document


# ============================================================
# MAIN
# ============================================================
def main():
    """Main function to generate the corpus."""
    api_key = GEMINI_API_KEY
    if not api_key:
        print("❌ GEMINI_API_KEY not set")
        print("   export GEMINI_API_KEY=your_key_here")
        return

    client = genai.Client(api_key=api_key)
    NOVATECH_MD_DIR.mkdir(parents=True, exist_ok=True)
    NOVATECH_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  NovaTech Solutions — Corpus Generation")
    print(f"  Model: {GEMINI_MODEL}")
    print(f"  Documents: {len(THEMES)}")
    print(f"  Mode: article-by-article")
    print(f"{'='*60}")

    # Load gov texts
    print(f"\n[STEP 1] Loading legal documents...")
    gouv_texts = load_gouv_texts()
    print(f"  → {len(gouv_texts)} documents loaded")

    # Generate each document
    print(f"\n[STEP 2] Generating NovaTech documents...\n")
    generated = []

    for i, theme in enumerate(THEMES):
        filename = theme["filename"]
        md_path = NOVATECH_MD_DIR / f"{filename}.md"

        # Skip if already generated
        if md_path.exists() and md_path.stat().st_size > 500:
            print(f"[{i+1}/{len(THEMES)}] {filename} — already exists, skipping")
            generated.append(filename)
            continue

        print(f"[{i+1}/{len(THEMES)}] {filename}")

        try:
            content = generate_document(client, theme, gouv_texts)
            md_path.write_text(content, encoding="utf-8")
            print(f"  ✓ Saved: {md_path} ({len(content)} chars)")
            generated.append(filename)
        except Exception as e:
            print(f"  ✗ Error: {e}")

    # Summary
    print(f"\n{'='*60}")
    print(f"  ✓ {len(generated)}/{len(THEMES)} documents generated")
    print(f"  Markdown: {NOVATECH_MD_DIR}/")
    print(f"{'='*60}")

    # PDF conversion
    print(f"\n[STEP 3] Converting to PDF...")
    try:
        convert_all_to_pdf(str(NOVATECH_MD_DIR), str(NOVATECH_DIR))
        print(f"  ✓ PDFs in {NOVATECH_DIR}/")
    except ImportError:
        print(f"  ℹ md_to_pdf.py not found — skipping PDF conversion")
        print(f"    Markdown files are in {NOVATECH_MD_DIR}/")

    print()


if __name__ == "__main__":
    main()