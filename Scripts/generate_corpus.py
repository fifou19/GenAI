#!/usr/bin/env python3
"""
Génération du corpus NovaTech Solutions via Gemini API.
Approche article-par-article :
  1. Pour chaque thème, demande à Gemini la structure (liste d'articles)
  2. Puis génère chaque article séparément
  3. Concatène le tout en un Markdown complet

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

from src.config import ( GEMINI_API_KEY , MAX_RETRIES, BASE_WAIT, MAX_WAIT, SLEEP_BETWEEN_CALLS, GOUV_DIR, NOVATECH_DIR, NOVATECH_MD_DIR , MODEL)
import pdfplumber
from google import genai
from google.genai import types

# ============================================================
# CONFIG
# ============================================================




def is_retryable_error(e):
    s = str(e).lower()
    return any(x in s for x in ["503", "429", "overloaded", "resource exhausted", "rate limit", "unavailable"])


# ============================================================
# GEMINI CALL WITH RETRY
# ============================================================
def call_gemini(client, system: str, prompt: str, temperature: float = 0.3) -> str:
    """Appelle Gemini avec retry et backoff."""
    last_exc = None
    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    temperature=temperature,
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
    {
        "filename": "01_conges_payes_rtt",
        "title": "Politique de Congés Payés et RTT",
        "gouv_keys": ["gouv_01_conges_payes", "gouv_02_conges_evenements_familiaux"],
        "description": "Paid leave (25 days), seniority leave (5/10/15/20 years), leave request procedure via MonEspace, RTT (11 days cadres forfait jours 2025, 12 days non-cadres), half RTT fixed by employer, RTT during probation (max 2), exceptional leave table (marriage, death, birth, sick child), leave donation (anonymous, 5 days max/year), carry-over and loss rules."
    },
    {
        "filename": "02_teletravail",
        "title": "Politique de Télétravail",
        "gouv_keys": ["gouv_03_teletravail"],
        "description": "Eligibility (CDI or CDD >6 months, probation completed), special cases (alternants 1 day/week after 3 months, probation 1 day/week after 1st month, part-time ≤80% = 1 day/week), days table (cadres 3, non-cadres 2, managers ≥5 reports 2), mandatory office day, declaration via MonEspace by Friday, location (home, other on request, abroad prohibited except EU 4 weeks/year), hours (9:30-12, 14-17), disconnect right, equipment provided, monthly allowance (10/20/30€), furniture 50% capped 200€, reversibility 2 weeks notice."
    },
    {
        "filename": "03_frais_deplacements",
        "title": "Politique de Remboursement de Frais et Déplacements",
        "gouv_keys": [],
        "description": "Commuting 75% (vs 50% legal, CDI post-probation only), personal vehicle (authorization required, tax mileage table 3CV-7CV+), train (2nd class, 1st class cadres ≥3h, TravelNova 7 days advance), flights (economy <6h, premium economy cadres ≥6h, business director approval ≥8h), taxi/VTC (60€ provinces, 80€ Paris), meal vouchers 10€ (60%/40%), travel meals table (lunch France 20€, dinner 30€, international 40-50€), client meals (60€/person cadres, 40€ non-cadres with approval), accommodation table (Paris 150€, major cities 120€, others 100€, Europe 180€, outside 250€), MonEspace submission 30 days, advance >500€."
    },
    {
        "filename": "04_onboarding",
        "title": "Guide d'Onboarding",
        "gouv_keys": [],
        "description": "Before arrival D-7 (DocuSign contract, admin file MonEspace, schedule, buddy), required documents, Day 1 (welcome 9:30, badge, kit, IT equipment, integration morning, IT security training), first week day-by-day, first month (NovAcademy: GDPR 2h, code of conduct 1h, harassment 1h30, CSR 45min, weekly manager check-ins), probation table (CDI cadre 4+4 months, non-cadre 2+2, CDD <6m 2 weeks, ≥6m 1 month), mid and final evaluation, practical info (hours 7:30-21:00, cafeteria, lost badge 15€), tools and contacts table."
    },
    {
        "filename": "05_mutuelle_avantages",
        "title": "Mutuelle et Avantages Sociaux",
        "gouv_keys": [],
        "description": "Harmonie Mutuelle mandatory from Day 1, 2 plans table (Essential 35€/month, Family 85€/month), 60% employer, coverage (hospitalization, consultations, dental, optical 200-300€, alternative medicine 4x30€), exemptions, portability 12 months, insurance table cadres/non-cadres (0.80% vs 0.50%, death 4x vs 3x, maintenance 180 vs 90 days), CSE (holiday vouchers 200€, gifts 170€+50€/child, sport 50% cap 200€), profit sharing, PEE (100% match to 500€, 50% to 1000€, max 750€), PERCO 50% cap 300€, mobility 500€/year, solidarity leave 2 days, well-being (MindCare, yoga, fruit)."
    },
    {
        "filename": "06_faq_rh",
        "title": "FAQ RH",
        "gouv_keys": [],
        "description": "~20 Q&A in categories: leave (urgent leave, manager no response = approved after 5 days, RTT lost Dec 31, combine RTT+leave, sick leave and leave), remote work (new hires, abroad, manager withdrawal, allowance if absent), expenses (lost receipt max 2/semester, personal car, >30 days not guaranteed >3 months refused, parking 15€/day), health (add spouse 30 days, portability 12 months, psychologist 4x30€ + MindCare), compensation (payslip 25th, payment last day, PEE example, PEE vs PERCO), office (badge lost 15€, IT desk 5678, bike parking + mobility 500€). Concise answers with form references."
    },
    {
        "filename": "07_arrets_maladie",
        "title": "Politique Arrêts Maladie et Accidents du Travail",
        "gouv_keys": ["gouv_04_arret_maladie", "gouv_05_arret_maladie_ij", "gouv_05_accident_travail"],
        "description": "Employee obligations (notify 24h, certificate 48h via MonEspace), salary maintenance (1 year seniority required), waiting period (0 cadres, 3 days non-cadres, none for work accidents), maintenance table by seniority AND status, medical counter-visit, repeated absences ≥3/12months → HR meeting, work accident (definition, process, declaration 48h), AT/MP compensation (no seniority, no waiting, 100% 90 days then 80% max 12 months), return visit (60 days illness, 30 days accident), pre-return ≥3 months, therapeutic part-time, impact on leave/RTT/seniority."
    },
    {
        "filename": "08_formation_carriere",
        "title": "Formation Continue et Évolution de Carrière",
        "gouv_keys": ["gouv_09_cpf"],
        "description": "Skills plan table (mandatory, job, transversal, degree with examples), budget 2% payroll cap 3000€/year, request procedure, CPF (500€/year cap 5000€, work time 60/120 days, no response 30 days = approved, company top-up), career interview every 2 years (distinct from annual), 6-year review (3000€ corrective), internal mobility (2 weeks internal posting, 18 months seniority, confidential, 3 months adaptation), NovAcademy 500+ modules 2h/month."
    },
    {
        "filename": "09_entretiens_remuneration",
        "title": "Entretiens Annuels, Objectifs et Rémunération",
        "gouv_keys": [],
        "description": "Annual review Jan-Feb (review, competencies, objectives), self-assessment 1 week before MonEspace, competency scale 1-5 table, 3 categories (technical, behavioral, managerial), improvement plan if ≤2 (3-month follow-up), objectives 3-5 SMART + collective 20%, quarterly check-ins, salary grid N1-N8 table (25k-120k), increases March (general 2.5%, individual ~1.5%, promotion ≥5%, none if ≤2), variable table (sales 15-30%, managers 10-15%, cadres 5-10%, non-cadres none), exceptional bonus max 3000€ 2/year, feedback, 360° managers every 2 years."
    },
    {
        "filename": "10_depart_entreprise",
        "title": "Départ de l'Entreprise",
        "gouv_keys": ["gouv_06_demission", "gouv_07_rupture_conventionnelle", "gouv_08_licenciement"],
        "description": "Resignation (registered letter, email not valid, notice 1 month non-cadre / 3 months cadre, waiver), mutual termination (full process, indemnities, 15-day retraction, 15-day approval, timeline 5-8 weeks), dismissal (personal and economic, process, notice table, legal indemnity), CDD end (10% precarity bonus), exit checklist (IT return, expenses, handover, exit interview, access disabled 6pm), documents within 7 days, non-compete clause."
    },
    {
        "filename": "11_handicap_rqth",
        "title": "Handicap, RQTH et Aménagements de Poste",
        "gouv_keys": ["gouv_10_rqth"],
        "description": "Disability agreement 2024-2027, RQTH (definition, benefits: accommodation, Agefiph, doubled notice, absence days, priority training), RQTH process (personal, confidential, MDPH, 4-6 months, 1-10 years or lifetime), strict confidentiality (only disability liaison + HR + occupational physician with written consent), accommodations table (equipment, software, organizational, environment, human), procedure (3-6 weeks), funding company + Agefiph >5000€, enhanced remote work up to 4 days/week, 2 paid absence days/year + 3 additional, SEEPH awareness November, mandatory manager training, liaison Marc Lefèvre contact details."
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

    result = call_gemini(client, SYSTEM_STRUCTURE, prompt, temperature=0.2)

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

    return call_gemini(client, SYSTEM_ARTICLE, prompt, temperature=0.3)


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
    header += f"**Document interne — Version 2025**\n"
    header += f"**Direction des Ressources Humaines**\n\n---\n\n"

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
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not set")
        print("   export GEMINI_API_KEY=your_key_here")
        return

    client = genai.Client(api_key=api_key)
    NOVATECH_MD_DIR.mkdir(parents=True, exist_ok=True)
    NOVATECH_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  NovaTech Solutions — Corpus Generation")
    print(f"  Model: {MODEL}")
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