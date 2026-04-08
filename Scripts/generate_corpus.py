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
from Scripts.md_to_pdf import convert_all_to_pdf

from src.config import ( GEMINI_API_KEY , TEMPERATURES,MAX_RETRIES, BASE_WAIT, MAX_WAIT, SLEEP_BETWEEN_CALLS, GOUV_DIR, NOVATECH_DIR, NOVATECH_MD_DIR , GEMINI_MODEL,is_retryable_error)
import pdfplumber
from google import genai
from google.genai import types

# ============================================================
# GEMINI CALL WITH RETRY
# ============================================================
def call_gemini(client, system: str, prompt: str, temperature: float ) -> str:
    """Appelle Gemini avec retry et backoff."""
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
# SYSTEM PROMPTS
# ============================================================
SYSTEM_STRUCTURE = """You are an HR policy expert. When given a document theme and legal context, you return ONLY a JSON array of article titles that should compose the document. 

Rules:
- Return valid JSON only, no markdown, no explanation
- Each article should be a short title in French
- Include an introduction article and a contact block article at the end
- Typically 5-8 articles per document
- Example output: ["Introduction", "Article 1 — Champ d'application", "Article 2 — Droits à congés", "Article 3 — Procédure de demande", "Article 4 — Report et perte", "Contact"]"""

SYSTEM_ARTICLE = """You are the Director of Human Resources at NovaTech Solutions, a French tech company with 350 employees based in Paris (12 rue de l'Innovation, 75008).

You write ONE specific section of an internal policy document. Rules:
- Write in professional but accessible French
- Use Markdown (##, ###, bullet points, tables where relevant)
- Concrete figures (€, days, deadlines)
- Distinguish cadre vs non-cadre, CDI vs CDD, alternant where relevant
- Include special cases and exceptions
- Rules must be CONSISTENT with French labor law but may be MORE FAVORABLE
- Reference internal tools: MonEspace (HR portal), TravelNova (travel), NovAcademy (training), Slack
- Tables must be compact, properly formatted
- Output ONLY the section content in Markdown, no meta-commentary
- For the contact block: include a dedicated email, MonEspace form path, and a named contact person

HR Contacts:
- Sophie Martin: Responsable Administration du Personnel
- Lucas Dupont: Chargé de projet QVT
- Claire Lefebvre: Responsable Comptabilité Fournisseurs
- Amina Khelifi: Chargée de recrutement et intégration
- Thomas Bernard: Responsable Compensation & Benefits
- Isabelle Morel: Responsable Formation et Développement
- Marc Lefèvre: Référent Handicap
- Dr. Émilie Renaud: Médecin du travail
- Nathalie Brun: Référent harcèlement"""


# ============================================================
# THEMES
# ============================================================
THEMES = [
    # =========================================================
    # 1) THEMES REGLEMENTAIRES ALIGNS AVEC LES SOURCES GOUV
    # =========================================================
    {
        "theme_id": "conges_payes",
        "filename": "01_conges_payes",
        "title": "Congés payés",
        "category": "reglementaire",
        "source_type": "mixed",
        "gouv_keys": ["gouv_01_conges_payes"],
        "description": (
            "Rules related to paid annual leave: acquisition, duration, leave counting, "
            "employee rights, employer obligations, scheduling, carry-over, and paid leave management."
        ),
    },
    {
        "theme_id": "conges_evenements_familiaux",
        "filename": "02_conges_evenements_familiaux",
        "title": "Congés pour événements familiaux",
        "category": "reglementaire",
        "source_type": "mixed",
        "gouv_keys": ["gouv_02_conges_evenements_familiaux"],
        "description": (
            "Special leave related to family events such as marriage, PACS, birth, adoption, "
            "death of a relative, and child illness."
        ),
    },
    {
        "theme_id": "teletravail",
        "filename": "03_teletravail",
        "title": "Télétravail",
        "category": "reglementaire",
        "source_type": "mixed",
        "gouv_keys": ["gouv_03_teletravail"],
        "description": (
            "Remote work rules: eligibility, frequency, request process, working conditions, "
            "approved workplace, employer obligations, working hours, and associated allowances."
        ),
    },
    {
        "theme_id": "arret_maladie",
        "filename": "04_arret_maladie",
        "title": "Arrêt maladie",
        "category": "reglementaire",
        "source_type": "mixed",
        "gouv_keys": ["gouv_04_arret_maladie"],
        "description": (
            "Rules applicable in case of sick leave: employee notification, medical certificate deadlines, "
            "salary maintenance, waiting period, return-to-work obligations, and leave impacts."
        ),
    },
    {
        "theme_id": "accident_travail",
        "filename": "05_accident_travail",
        "title": "Accident du travail",
        "category": "reglementaire",
        "source_type": "mixed",
        "gouv_keys": ["gouv_05_accident_travail"],
        "description": (
            "Definition and management of work accidents: declaration process, deadlines, employer duties, "
            "specific compensation regime, medical follow-up, and return-to-work rules."
        ),
    },
    {
        "theme_id": "demission",
        "filename": "06_demission",
        "title": "Démission",
        "category": "reglementaire",
        "source_type": "mixed",
        "gouv_keys": ["gouv_06_demission"],
        "description": (
            "Rules related to resignation: formalism, notice period, rights and obligations of the employee, "
            "and employment contract termination process."
        ),
    },
    {
        "theme_id": "rupture_conventionnelle",
        "filename": "07_rupture_conventionnelle",
        "title": "Rupture conventionnelle",
        "category": "reglementaire",
        "source_type": "mixed",
        "gouv_keys": ["gouv_07_rupture_conventionnelle"],
        "description": (
            "Mutual termination process: conditions, procedure, timeline, indemnities, withdrawal period, "
            "approval, and end-of-contract consequences."
        ),
    },
    {
        "theme_id": "licenciement",
        "filename": "08_licenciement",
        "title": "Licenciement",
        "category": "reglementaire",
        "source_type": "mixed",
        "gouv_keys": ["gouv_08_licenciement"],
        "description": (
            "Dismissal rules: personal or economic dismissal, procedure, mandatory meetings, notice period, "
            "indemnities, and employee rights."
        ),
    },
    {
        "theme_id": "cpf",
        "filename": "09_cpf",
        "title": "Compte Personnel de Formation (CPF)",
        "category": "reglementaire",
        "source_type": "mixed",
        "gouv_keys": ["gouv_09_cpf"],
        "description": (
            "Rules governing the CPF: annual credit, use conditions, employee request process, employer response, "
            "training during working time, and possible employer top-up."
        ),
    },
    {
        "theme_id": "rqth_handicap",
        "filename": "10_rqth_handicap",
        "title": "RQTH, handicap et aménagements de poste",
        "category": "reglementaire",
        "source_type": "mixed",
        "gouv_keys": ["gouv_10_rqth"],
        "description": (
            "Recognition of disability status (RQTH), related rights, confidentiality principles, workplace "
            "accommodations, dedicated leave, funding support, and associated HR process."
        ),
    },

    # =========================================================
    # 2) THEMES INTERNES COMPLEMENTAIRES
    # =========================================================
    {
        "theme_id": "rtt",
        "filename": "11_rtt",
        "title": "RTT",
        "category": "interne",
        "source_type": "internal",
        "gouv_keys": [],
        "description": (
            "RTT policy: number of days by status, allocation rules, employer-fixed RTT, use during probation, "
            "request process, carry-over rules, and expiry conditions."
        ),
    },
    {
        "theme_id": "frais_deplacements",
        "filename": "12_frais_deplacements",
        "title": "Frais et déplacements professionnels",
        "category": "interne",
        "source_type": "internal",
        "gouv_keys": [],
        "description": (
            "Travel and expense reimbursement policy: commuting reimbursement, mileage allowance, train and flight "
            "rules, taxi/VTC caps, meals, accommodation caps, submission deadlines, and travel advance rules."
        ),
    },
    {
        "theme_id": "onboarding",
        "filename": "13_onboarding",
        "title": "Onboarding et intégration",
        "category": "interne",
        "source_type": "internal",
        "gouv_keys": [],
        "description": (
            "New hire onboarding process: pre-arrival steps, required documents, day 1, first week, training plan, "
            "probation follow-up, tools, and useful internal contacts."
        ),
    },
    {
        "theme_id": "mutuelle_avantages",
        "filename": "14_mutuelle_avantages",
        "title": "Mutuelle et avantages sociaux",
        "category": "interne",
        "source_type": "internal",
        "gouv_keys": [],
        "description": (
            "Health insurance and social benefits: mandatory coverage, contribution split, plan options, portability, "
            "provident scheme, CSE benefits, savings plans, mobility package, and well-being initiatives."
        ),
    },
    {
        "theme_id": "formation_carriere",
        "filename": "15_formation_carriere",
        "title": "Formation continue et évolution de carrière",
        "category": "interne",
        "source_type": "mixed",
        "gouv_keys": ["gouv_09_cpf"],
        "description": (
            "Internal training policy and career development: skills plan, training budget, request workflow, "
            "career interviews, internal mobility, and articulation with CPF rights."
        ),
    },
    {
        "theme_id": "entretiens_remuneration",
        "filename": "16_entretiens_remuneration",
        "title": "Entretiens annuels, objectifs et rémunération",
        "category": "interne",
        "source_type": "internal",
        "gouv_keys": [],
        "description": (
            "Annual review process, objective setting, competency evaluation, salary review principles, bonus policy, "
            "promotion rules, and managerial feedback framework."
        ),
    },
    {
        "theme_id": "faq_rh",
        "filename": "17_faq_rh",
        "title": "FAQ RH",
        "category": "interne",
        "source_type": "internal",
        "gouv_keys": [],
        "description": (
            "Operational HR FAQ covering recurring employee questions about leave, remote work, expenses, health "
            "coverage, payroll, badges, support contacts, and practical company rules."
        ),
    },
    {
        "theme_id": "depart_entreprise",
        "filename": "18_depart_entreprise",
        "title": "Départ de l'entreprise",
        "category": "interne",
        "source_type": "mixed",
        "gouv_keys": [
            "gouv_06_demission",
            "gouv_07_rupture_conventionnelle",
            "gouv_08_licenciement",
        ],
        "description": (
            "Internal offboarding policy covering resignation, mutual termination, dismissal, end-of-contract "
            "formalities, company asset return, expense closure, handover, final documents, and non-compete clauses."
        ),
    },
]


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