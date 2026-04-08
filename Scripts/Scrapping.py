#!/usr/bin/env python3
"""
Service-public.fr scraper v4
Saves in TWO formats:
  - Markdown to data/gouv_md/ (for RAG — structured headers)
  - PDF to data/gouv/ (for human display / sharing)

Usage:
    pip install requests beautifulsoup4 reportlab
    python scripts/scrape_service_public.py
"""


import os, re, time, requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib import colors
from src.config import (GOUV_DIR, GOUV_MD_DIR)

# ============================================================
# CONFIG
# ============================================================


THEMES = [
    {
        "filename": "gouv_01_conges_payes",
        "title": "Congés payés du salarié dans le secteur privé",
        "start_urls": ["https://www.service-public.fr/particuliers/vosdroits/F2258"],
        "follow_patterns": [r"/vosdroits/F2258"],
        "max_pages": 5,
    },
    {
        "filename": "gouv_02_conges_evenements_familiaux",
        "title": "Congés pour événements familiaux (secteur privé)",
        "start_urls": [
            "https://www.service-public.fr/particuliers/vosdroits/F2278",
            "https://code.travail.gouv.fr/contribution/les-conges-pour-evenements-familiaux",
        ],
        "follow_patterns": [r"/vosdroits/F2278"],
        "max_pages": 4,
    },
    {
        "filename": "gouv_03_teletravail",
        "title": "Télétravail dans le secteur privé",
        "start_urls": ["https://www.service-public.fr/particuliers/vosdroits/F13851"],
        "follow_patterns": [r"/vosdroits/F13851"],
        "max_pages": 5,
    },
    {
        "filename": "gouv_04_arret_maladie",
        "title": "Arrêt maladie : indemnités et démarches",
        "start_urls": [
            "https://www.service-public.fr/particuliers/vosdroits/F3053",
            "https://www.service-public.fr/particuliers/vosdroits/F303",
        ],
        "follow_patterns": [r"/vosdroits/F3053", r"/vosdroits/F303"],
        "max_pages": 6,
    },
    {
        "filename": "gouv_05_accident_travail",
        "title": "Accident du travail et maladie professionnelle",
        "start_urls": [
            "https://www.service-public.fr/particuliers/vosdroits/F175",
            "https://www.service-public.fr/particuliers/vosdroits/F176",
        ],
        "follow_patterns": [r"/vosdroits/F175", r"/vosdroits/F176"],
        "max_pages": 6,
    },
    {
        "filename": "gouv_06_demission",
        "title": "Démission d'un salarié",
        "start_urls": ["https://www.service-public.fr/particuliers/vosdroits/F2883"],
        "follow_patterns": [r"/vosdroits/F2883"],
        "max_pages": 4,
    },
    {
        "filename": "gouv_07_rupture_conventionnelle",
        "title": "Rupture conventionnelle",
        "start_urls": ["https://www.service-public.fr/particuliers/vosdroits/F19030"],
        "follow_patterns": [r"/vosdroits/F19030"],
        "max_pages": 5,
    },
    {
        "filename": "gouv_08_licenciement",
        "title": "Licenciement dans le secteur privé",
        "start_urls": [
            "https://www.service-public.fr/particuliers/vosdroits/F1848",
            "https://www.service-public.fr/particuliers/vosdroits/F133",
        ],
        "follow_patterns": [
            r"/vosdroits/F1848", r"/vosdroits/F133",
            r"/vosdroits/F36512", r"/vosdroits/F2835",
        ],
        "max_pages": 10,
    },
    {
        "filename": "gouv_09_cpf",
        "title": "Compte personnel de formation (CPF)",
        "start_urls": ["https://www.service-public.fr/particuliers/vosdroits/F10705"],
        "follow_patterns": [r"/vosdroits/F10705"],
        "max_pages": 4,
    },
    {
        "filename": "gouv_10_rqth",
        "title": "Reconnaissance de la qualité de travailleur handicapé (RQTH)",
        "start_urls": ["https://www.service-public.fr/particuliers/vosdroits/F1650"],
        "follow_patterns": [r"/vosdroits/F1650"],
        "max_pages": 4,
    },
]

# ============================================================
# NOISE FILTER
# ============================================================
SKIP_TEXTS = [
    'ajouter à mes favoris', 'partager la page', 'facebook', 'linkedin',
    'courriel', 'copier le lien', 'lien copié',
    'vous recevrez un courriel', 'vous recevrez un email',
    'vous devez vous connecter', 'votre abonnement',
    'ce sujet a été ajouté', 'ce sujet vous intéresse',
    'pour vous abonner aux mises à jour', 'activer votre espace personnel',
    'vous serez alerté', 'le lien vers cette page',
    'cette page vous a-t-elle été utile', 'pas du tout',
    'l\'équipe service public vous remercie',
    'je vais sur la page d\'accueil', 'je fais une remarque',
    'vos remarques pour améliorer', 'avez-vous rencontré une difficulté',
    'avez-vous des suggestions', 'vous avez noté',
    'allô service public', 'les informateurs qui vous répondent',
    'il ne répond pas aux questions portant sur l\'indemnisation',
    'être rappelé(e)', 'coût service gratuit',
    'horaireslundi', 'lundi : de 08h30', 'mardi : de 08h30',
    'mercredi : de 08h30', 'jeudi : de 08h30', 'vendredi : de 13h00',
    'questions ? réponses !', 'voir aussi', 'services en ligne et formulaires',
    'textes de loi et références', 'fiches pratiques par événement',
    'répondez aux questions successives',
    'vidéo désactivée', 'accepter les cookies',
    'qui peut m\'aider', 'vous avez une question',
    'vous souhaitez être accompagné',
    'code du travail : articles', 'code de la sécurité sociale : articles',
    'code de l\'action sociale', 'code rural et de la pêche',
    'circulaire du', 'circulaire n°', 'décret n°', 'arrêté du',
    'réponse ministérielle', 'service en ligne', 'formulaire',
    'modèle de document', 'outil de recherche',
    'correspond à tous les jours de la semaine',
    'correspond à la totalité des jours du calendrier',
    'accord écrit négocié entre les représentants',
    'résultat des négociations menées',
    'convention collective, accord collectif',
    'jour effectivement travaillé',
    'contrat de travail à durée indéterminée',
    'contrat à durée déterminée', 'caisse primaire',
    'mutualité sociale agricole', 'salaire minimum interprofessionnel',
    'maison départementale pour les personnes',
    'commission des droits pour l\'autonomie',
    'allemagne, autriche, belgique',
    'période écoulée entre 2 événements',
    'maladie grave et/ou chronique',
    'versées par la sécurité sociale aux salariés',
    'état de santé stabilisé où la lésion',
    'médecin intervenant à la fois',
    'personne désignée par la loi',
    'double, copie d\'un document',
    'opérateur de compétences',
    'association de gestion du fonds',
    'répertoire national des certifications',
    'centre national des arts et métiers',
    'personne dont la langue maternelle',
    'formalité par laquelle un acte',
]


def should_skip(text):
    lower = text.lower().strip()
    if len(lower) < 10:
        return True
    for p in SKIP_TEXTS:
        if p in lower:
            return True
    if len(lower) < 60 and not any(c in lower for c in ['?', '.', ',']):
        return True
    return False


# ============================================================
# SCRAPING
# ============================================================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9",
}


def clean_text(text):
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r':?\s*titleContent', '', text)
    return text


def scrape_page(url):
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')
    main = soup.find('main') or soup.find('article') or soup.find('div', {'id': 'main'}) or soup.body

    elements = []
    h1 = main.find('h1') # type: ignore
    if h1:
        t = clean_text(h1.get_text())
        if t and not should_skip(t):
            elements.append(('page_title', t))

    for tag in main.find_all(string=re.compile(r'Vérifié le')): # type: ignore
        t = clean_text(str(tag))
        if t:
            elements.append(('note', t))
            break

    seen = set()
    in_law_section = False

    for tag in main.find_all(['h2', 'h3', 'h4', 'p', 'ul', 'ol', 'table']): # type: ignore
        if tag.find_parent(['nav', 'footer', 'form', 'aside', 'header']):
            continue

        if tag.name == 'h2':
            t = clean_text(tag.get_text())
            if should_skip(t):
                in_law_section = True
                continue
            in_law_section = False
            if t and len(t) > 2 and t not in seen:
                seen.add(t)
                elements.append(('h2', t))

        elif tag.name in ['h3', 'h4']:
            if in_law_section: continue
            t = clean_text(tag.get_text())
            if should_skip(t): continue
            if t and len(t) > 2 and t not in seen:
                seen.add(t)
                elements.append(('h3', t))

        elif tag.name == 'p':
            if in_law_section: continue
            t = clean_text(tag.get_text())
            if should_skip(t): continue
            if t and len(t) > 15 and t not in seen:
                seen.add(t)
                elements.append(('body', t))

        elif tag.name in ['ul', 'ol']:
            if in_law_section: continue
            for li in tag.find_all('li', recursive=False):
                t = clean_text(li.get_text())
                if should_skip(t): continue
                if t and len(t) > 10 and t not in seen:
                    seen.add(t)
                    elements.append(('bullet', t))

        elif tag.name == 'table':
            if in_law_section: continue
            rows = []
            for tr in tag.find_all('tr'):
                cells = [clean_text(td.get_text()) for td in tr.find_all(['td', 'th'])]
                if any(c for c in cells):
                    rows.append(cells)
            if rows and len(rows) > 1:
                elements.append(('table', rows))

    return elements, soup


def extract_sub_links(soup, base_url, follow_patterns):
    links = set()
    for a in soup.find_all('a', href=True):
        full_url = urljoin(base_url, a['href'])
        if 'service-public.fr/particuliers' not in full_url:
            continue
        for pattern in follow_patterns:
            if re.search(pattern, full_url):
                parsed = urlparse(full_url)
                links.add(f"{parsed.scheme}://{parsed.netloc}{parsed.path}")
                break
    return links


def crawl_theme(theme):
    all_elements = []
    visited = set()
    to_visit = list(theme["start_urls"])
    max_pages = theme.get("max_pages", 5)
    count = 0

    while to_visit and count < max_pages:
        url = to_visit.pop(0)
        norm = urlparse(url)
        norm_url = f"{norm.scheme}://{norm.netloc}{norm.path}"
        if norm_url in visited: continue
        visited.add(norm_url)

        print(f"    Scraping: {url}")
        try:
            elements, soup = scrape_page(url)
            count += 1
            if elements:
                if all_elements:
                    all_elements.append(('separator', None))
                all_elements.extend(elements)
            for link in extract_sub_links(soup, url, theme.get("follow_patterns", [])):
                ln = urlparse(link)
                if f"{ln.scheme}://{ln.netloc}{ln.path}" not in visited:
                    to_visit.append(link)
            time.sleep(2)
        except Exception as e:
            print(f"    ✗ Error: {e}")

    print(f"    → {count} page(s), {len(all_elements)} elements")
    return all_elements


# ============================================================
# SAVE AS MARKDOWN
# ============================================================
def to_markdown(elements, title, urls) -> str:
    """Convertit les éléments scrapés en Markdown structuré."""
    lines = []
    lines.append(f"# {title}")
    lines.append(f"")
    lines.append(f"*Sources : {' | '.join(urls)}*")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")

    for etype, content in elements:
        if etype == 'separator':
            lines.append(f"")
            lines.append(f"---")
            lines.append(f"")
        elif etype == 'page_title':
            lines.append(f"## {content}")
            lines.append(f"")
        elif etype == 'note':
            lines.append(f"*{content}*")
            lines.append(f"")
        elif etype == 'h2':
            lines.append(f"## {content}")
            lines.append(f"")
        elif etype == 'h3':
            lines.append(f"### {content}")
            lines.append(f"")
        elif etype == 'body':
            lines.append(content)
            lines.append(f"")
        elif etype == 'bullet':
            lines.append(f"- {content}")
        elif etype == 'table':
            if content and len(content) > 0:
                ncols = max(len(r) for r in content)
                # Header
                lines.append("| " + " | ".join(content[0]) + " |")
                lines.append("| " + " | ".join(["---"] * ncols) + " |")
                for row in content[1:]:
                    while len(row) < ncols:
                        row.append("")
                    lines.append("| " + " | ".join(row) + " |")
                lines.append(f"")

    return "\n".join(lines)


# ============================================================
# SAVE AS PDF (same as before, simplified)
# ============================================================
GOV_BLUE = HexColor("#000091")
GOV_RED = HexColor("#E1000F")
GOV_GRAY = HexColor("#666666")
GOV_TEXT = HexColor("#1E1E1E")
GOV_LIGHT = HexColor("#F0F0F0")
WHITE = colors.white


def create_styles():
    return {
        'Title': ParagraphStyle('T', fontName='Helvetica-Bold', fontSize=18, leading=24, textColor=GOV_BLUE, spaceAfter=4*mm),
        'Source': ParagraphStyle('S', fontName='Helvetica', fontSize=9, leading=12, textColor=GOV_GRAY, spaceAfter=6*mm),
        'H2': ParagraphStyle('H2', fontName='Helvetica-Bold', fontSize=13, leading=17, textColor=GOV_BLUE, spaceBefore=8*mm, spaceAfter=3*mm),
        'H3': ParagraphStyle('H3', fontName='Helvetica-Bold', fontSize=11, leading=15, textColor=GOV_TEXT, spaceBefore=5*mm, spaceAfter=2*mm),
        'Body': ParagraphStyle('B', fontName='Helvetica', fontSize=9.5, leading=13.5, textColor=GOV_TEXT, spaceAfter=2*mm, alignment=TA_JUSTIFY),
        'Bullet': ParagraphStyle('BL', fontName='Helvetica', fontSize=9.5, leading=13.5, textColor=GOV_TEXT, leftIndent=8*mm, spaceAfter=1.5*mm, bulletIndent=3*mm),
        'Note': ParagraphStyle('N', fontName='Helvetica-Oblique', fontSize=9, leading=12, textColor=GOV_GRAY, spaceAfter=2*mm),
    }


def safe_xml(text):
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def header_footer(canvas, doc):
    canvas.saveState()
    w, h = A4
    canvas.setFillColor(GOV_BLUE)
    canvas.rect(0, h-16*mm, w, 16*mm, fill=1, stroke=0)
    canvas.setFillColor(GOV_RED)
    canvas.rect(0, h-17*mm, w, 1*mm, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(15*mm, h-11*mm, "service-public.fr")
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(GOV_GRAY)
    canvas.drawString(15*mm, 7*mm, "Source : service-public.fr — DILA")
    canvas.drawRightString(w-15*mm, 7*mm, f"Page {doc.page}")
    canvas.restoreState()


def to_pdf(elements, path, title, urls):
    styles = create_styles()
    doc = SimpleDocTemplate(path, pagesize=A4, topMargin=22*mm, bottomMargin=18*mm, leftMargin=15*mm, rightMargin=15*mm)
    story = [Spacer(1, 3*mm)]
    story.append(Paragraph(safe_xml(title), styles['Title'])) # type: ignore
    story.append(HRFlowable(width="30%", thickness=3, color=GOV_RED, spaceAfter=2*mm, hAlign='LEFT')) # type: ignore
    story.append(Paragraph(safe_xml("Sources : " + " | ".join(urls)), styles['Source'])) # type: ignore

    seen = set()
    for etype, content in elements:
        if etype == 'separator':
            story.append(Spacer(1, 4*mm))
            story.append(HRFlowable(width="80%", thickness=1, color=GOV_BLUE, spaceAfter=4*mm, hAlign='CENTER')) # type: ignore
        elif etype == 'h2':
            if content not in seen:
                seen.add(content)
                story.append(Paragraph(safe_xml(content), styles['H2'])) # type: ignore
        elif etype == 'h3':
            if content not in seen:
                seen.add(content)
                story.append(Paragraph(safe_xml(content), styles['H3'])) # type: ignore
        elif etype == 'body':
            if content not in seen:
                seen.add(content)
                story.append(Paragraph(safe_xml(content), styles['Body'])) # type: ignore
        elif etype == 'bullet':
            if content not in seen:
                seen.add(content)
                story.append(Paragraph(f'• {safe_xml(content)}', styles['Bullet'])) # type: ignore
        elif etype == 'note':
            story.append(Paragraph(safe_xml(content), styles['Note'])) # type: ignore
        elif etype == 'table':
            ncols = max(len(r) for r in content)
            for r in content:
                while len(r) < ncols: r.append('')
            cs = ParagraphStyle('TC', fontName='Helvetica', fontSize=8.5, leading=11)
            fmt = [[Paragraph(safe_xml(c), cs) for c in row] for row in content]
            avail = A4[0] - 30*mm
            t = Table(fmt, colWidths=[avail/ncols]*ncols, repeatRows=1)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), GOV_BLUE),
                ('TEXTCOLOR', (0,0), (-1,0), WHITE),
                ('GRID', (0,0), (-1,-1), 0.5, GOV_LIGHT),
                ('TOPPADDING', (0,0), (-1,-1), 4),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ]))
            story.append(Spacer(1, 2*mm))
            story.append(t) # type: ignore
            story.append(Spacer(1, 3*mm))

    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer) # type: ignore


# ============================================================
# MAIN
# ============================================================
def main():
    GOUV_MD_DIR.mkdir(parents=True, exist_ok=True)
    GOUV_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  Scraping service-public.fr v4")
    print(f"  {len(THEMES)} thèmes → Markdown + PDF")
    print(f"{'='*60}\n")

    for i, theme in enumerate(THEMES):
        print(f"[{i+1}/{len(THEMES)}] {theme['title']}")
        elements = crawl_theme(theme)
        if not elements:
            print(f"    ⚠ Aucun contenu\n")
            continue

        # Save Markdown
        md_content = to_markdown(elements, theme['title'], theme['start_urls'])
        md_path = GOUV_MD_DIR / f"{theme['filename']}.md"
        md_path.write_text(md_content, encoding="utf-8")
        print(f"    ✓ MD: {md_path}")

        # Save PDF
        pdf_path = GOUV_DIR / f"{theme['filename']}.pdf"
        try:
            to_pdf(elements, str(pdf_path), theme['title'], theme['start_urls'])
            print(f"    ✓ PDF: {pdf_path}\n")
        except Exception as e:
            print(f"    ✗ PDF error: {e}\n")

    print(f"\n{'='*60}")
    print(f"  ✓ Terminé !")
    print(f"  Markdown : {GOUV_MD_DIR}/")
    print(f"  PDF : {GOUV_DIR}/")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()