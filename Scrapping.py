#!/usr/bin/env python3
"""
Scraper avancé pour service-public.fr
Crawle les pages principales ET leurs sous-pages pour récupérer
tout le contenu détaillé. Génère un PDF complet par thème.

Usage:
    pip install requests beautifulsoup4 reportlab
    python scrape_service_public.py

Note: Le script attend ~2s entre chaque requête pour ne pas surcharger le serveur.
"""

import os
import re
import time
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
from reportlab.lib import colors

# ============================================================
# CONFIGURATION
# ============================================================

THEMES = [
    {
        "filename": "gouv_01_conges_payes",
        "title": "Congés payés du salarié dans le secteur privé",
        "start_urls": [
            "https://www.service-public.fr/particuliers/vosdroits/F2258",
        ],
        "follow_patterns": [r"/vosdroits/F2258", r"/vosdroits/F2930", r"/vosdroits/F33359"],
        "max_pages": 5,
    },
    {
        "filename": "gouv_02_conges_evenements_familiaux",
        "title": "Congés pour événements familiaux",
        "start_urls": [
            "https://www.service-public.fr/particuliers/vosdroits/F489",
        ],
        "follow_patterns": [r"/vosdroits/F489"],
        "max_pages": 3,
    },
    {
        "filename": "gouv_03_rtt",
        "title": "RTT — Réduction du Temps de Travail",
        "start_urls": [
            "https://www.service-public.fr/particuliers/vosdroits/F34049",
        ],
        "follow_patterns": [r"/vosdroits/F34049"],
        "max_pages": 3,
    },
    {
        "filename": "gouv_04_teletravail",
        "title": "Télétravail dans le secteur privé",
        "start_urls": [
            "https://www.service-public.fr/particuliers/vosdroits/F13851",
        ],
        "follow_patterns": [r"/vosdroits/F13851"],
        "max_pages": 5,
    },
    {
        "filename": "gouv_05_arret_maladie",
        "title": "Arrêt maladie : indemnités et démarches",
        "start_urls": [
            "https://www.service-public.fr/particuliers/vosdroits/F3053",
            "https://www.service-public.fr/particuliers/vosdroits/F303",
        ],
        "follow_patterns": [r"/vosdroits/F3053", r"/vosdroits/F303"],
        "max_pages": 6,
    },
    {
        "filename": "gouv_06_accident_travail",
        "title": "Accident du travail et maladie professionnelle",
        "start_urls": [
            "https://www.service-public.fr/particuliers/vosdroits/F175",
            "https://www.service-public.fr/particuliers/vosdroits/F176",
        ],
        "follow_patterns": [r"/vosdroits/F175", r"/vosdroits/F176"],
        "max_pages": 6,
    },
    {
        "filename": "gouv_07_demission",
        "title": "Démission d'un salarié",
        "start_urls": [
            "https://www.service-public.fr/particuliers/vosdroits/F2883",
        ],
        "follow_patterns": [r"/vosdroits/F2883"],
        "max_pages": 4,
    },
    {
        "filename": "gouv_08_rupture_conventionnelle",
        "title": "Rupture conventionnelle",
        "start_urls": [
            "https://www.service-public.fr/particuliers/vosdroits/F19030",
        ],
        "follow_patterns": [r"/vosdroits/F19030"],
        "max_pages": 5,
    },
    {
        "filename": "gouv_09_licenciement",
        "title": "Licenciement dans le secteur privé",
        "start_urls": [
            "https://www.service-public.fr/particuliers/vosdroits/F1848",
            "https://www.service-public.fr/particuliers/vosdroits/F133",
        ],
        "follow_patterns": [
            r"/vosdroits/F1848",
            r"/vosdroits/F133",
            r"/vosdroits/F36512",
            r"/vosdroits/F2835",
            r"/vosdroits/F987",
        ],
        "max_pages": 10,
    },
    {
        "filename": "gouv_10_cpf",
        "title": "Compte personnel de formation (CPF)",
        "start_urls": [
            "https://www.service-public.fr/particuliers/vosdroits/F10705",
        ],
        "follow_patterns": [r"/vosdroits/F10705"],
        "max_pages": 4,
    },
    {
        "filename": "gouv_11_rqth",
        "title": "Reconnaissance de la qualité de travailleur handicapé (RQTH)",
        "start_urls": [
            "https://www.service-public.fr/particuliers/vosdroits/F1650",
        ],
        "follow_patterns": [r"/vosdroits/F1650"],
        "max_pages": 4,
    },
]

OUTPUT_DIR = "data/gouv"

# ============================================================
# STYLES PDF
# ============================================================
GOV_BLUE = HexColor("#000091")
GOV_RED = HexColor("#E1000F")
GOV_GRAY = HexColor("#666666")
GOV_TEXT = HexColor("#1E1E1E")
GOV_LIGHT = HexColor("#F0F0F0")
WHITE = colors.white


def create_gov_styles():
    return {
        'Title': ParagraphStyle(
            'GovTitle', fontName='Helvetica-Bold', fontSize=18,
            leading=24, textColor=GOV_BLUE, spaceAfter=4*mm),
        'Source': ParagraphStyle(
            'GovSource', fontName='Helvetica', fontSize=9,
            leading=12, textColor=GOV_GRAY, spaceAfter=6*mm),
        'PageTitle': ParagraphStyle(
            'GovPageTitle', fontName='Helvetica-Bold', fontSize=13,
            leading=17, textColor=GOV_RED, spaceBefore=4*mm, spaceAfter=3*mm),
        'H2': ParagraphStyle(
            'GovH2', fontName='Helvetica-Bold', fontSize=13,
            leading=17, textColor=GOV_BLUE, spaceBefore=8*mm, spaceAfter=3*mm),
        'H3': ParagraphStyle(
            'GovH3', fontName='Helvetica-Bold', fontSize=11,
            leading=15, textColor=GOV_TEXT, spaceBefore=5*mm, spaceAfter=2*mm),
        'Body': ParagraphStyle(
            'GovBody', fontName='Helvetica', fontSize=9.5,
            leading=13.5, textColor=GOV_TEXT, spaceAfter=2*mm, alignment=TA_JUSTIFY),
        'Bullet': ParagraphStyle(
            'GovBullet', fontName='Helvetica', fontSize=9.5,
            leading=13.5, textColor=GOV_TEXT, leftIndent=8*mm,
            spaceAfter=1.5*mm, bulletIndent=3*mm),
        'Note': ParagraphStyle(
            'GovNote', fontName='Helvetica-Oblique', fontSize=9,
            leading=12, textColor=GOV_GRAY, spaceAfter=2*mm, leftIndent=4*mm),
    }


def gov_header_footer(canvas, doc):
    canvas.saveState()
    w, h = A4
    canvas.setFillColor(GOV_BLUE)
    canvas.rect(0, h - 16*mm, w, 16*mm, fill=1, stroke=0)
    canvas.setFillColor(GOV_RED)
    canvas.rect(0, h - 17*mm, w, 1*mm, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(15*mm, h - 11*mm, "service-public.fr")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(w - 15*mm, h - 11*mm,
                           "Le site officiel de l'administration française")
    canvas.setStrokeColor(GOV_LIGHT)
    canvas.setLineWidth(0.5)
    canvas.line(15*mm, 12*mm, w - 15*mm, 12*mm)
    canvas.setFillColor(GOV_GRAY)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(15*mm, 7*mm,
                      "Source : service-public.fr — Direction de l'information légale et administrative")
    canvas.drawRightString(w - 15*mm, 7*mm, f"Page {doc.page}")
    canvas.restoreState()


# ============================================================
# SCRAPING
# ============================================================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9",
}

SKIP_PATTERNS = [
    'ajoutez cette page', 'vous serez alerté', 'service n\'a pas accès',
    'vous avez noté', 'l\'équipe service', 'pour des raisons de sécurité',
    'merci de recharger', 'erreur technique', 'vous recevrez un email',
    'vous pouvez à tout moment supprimer', 'votre abonnement',
    'vous devez activer votre espace', 'ce sujet vous intéresse',
    'connectez-vous à votre compte', 'pour vous abonner',
    'je suggère une modification', 'saisie complémentaire',
    'allô service public', 'les informateurs qui vous répondent',
]


def clean_text(text):
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r':?\s*titleContent', '', text)
    for p in SKIP_PATTERNS:
        if p in text.lower():
            return ''
    return text


def extract_sub_links(soup, base_url, follow_patterns):
    links = set()
    for a in soup.find_all('a', href=True):
        href = a['href']
        full_url = urljoin(base_url, href)
        if 'service-public.fr/particuliers' not in full_url:
            continue
        # Exclure les pages entreprendre.service-public.fr
        if 'entreprendre.service-public' in full_url:
            continue
        for pattern in follow_patterns:
            if re.search(pattern, full_url):
                parsed = urlparse(full_url)
                clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                links.add(clean_url)
                break
    return links


def scrape_page(url):
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')

    main = (soup.find('main') or soup.find('article') or
            soup.find('div', {'id': 'main'}) or soup.body)

    elements = []

    # Titre
    h1 = main.find('h1')
    if h1:
        t = clean_text(h1.get_text())
        if t:
            elements.append(('page_title', t))

    # Date
    for tag in main.find_all(string=re.compile(r'Vérifié le')):
        t = clean_text(str(tag))
        if t:
            elements.append(('note', t))
            break

    # Contenu
    seen = set()
    for tag in main.find_all(['h2', 'h3', 'h4', 'p', 'ul', 'ol', 'table']):
        if tag.find_parent(['nav', 'footer', 'form', 'aside', 'header']):
            continue

        if tag.name == 'h2':
            t = clean_text(tag.get_text())
            if t and len(t) > 2 and t not in seen:
                seen.add(t)
                elements.append(('h2', t))

        elif tag.name in ['h3', 'h4']:
            t = clean_text(tag.get_text())
            if t and len(t) > 2 and t not in seen:
                seen.add(t)
                elements.append(('h3', t))

        elif tag.name == 'p':
            t = clean_text(tag.get_text())
            if t and len(t) > 10 and t not in seen:
                seen.add(t)
                elements.append(('body', t))

        elif tag.name in ['ul', 'ol']:
            for li in tag.find_all('li', recursive=False):
                t = clean_text(li.get_text())
                if t and len(t) > 5 and t not in seen:
                    seen.add(t)
                    elements.append(('bullet', t))

        elif tag.name == 'table':
            rows = []
            for tr in tag.find_all('tr'):
                cells = [clean_text(td.get_text()) for td in tr.find_all(['td', 'th'])]
                if any(c for c in cells):
                    rows.append(cells)
            if rows and len(rows) > 1:
                elements.append(('table', rows))

    return elements, soup


def crawl_theme(theme):
    all_elements = []
    visited = set()
    to_visit = list(theme["start_urls"])
    max_pages = theme.get("max_pages", 5)
    follow_patterns = theme.get("follow_patterns", [])
    pages_crawled = 0

    while to_visit and pages_crawled < max_pages:
        url = to_visit.pop(0)
        parsed = urlparse(url)
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if normalized in visited:
            continue
        visited.add(normalized)

        print(f"    Scraping: {url}")
        try:
            elements, soup = scrape_page(url)
            pages_crawled += 1

            if elements:
                if all_elements:
                    all_elements.append(('separator', normalized))
                all_elements.extend(elements)

            if follow_patterns:
                sub_links = extract_sub_links(soup, url, follow_patterns)
                for link in sub_links:
                    ln = urlparse(link)
                    ln_norm = f"{ln.scheme}://{ln.netloc}{ln.path}"
                    if ln_norm not in visited:
                        to_visit.append(link)

            time.sleep(2)

        except requests.RequestException as e:
            print(f"    ✗ Erreur réseau: {e}")
        except Exception as e:
            print(f"    ✗ Erreur: {e}")

    print(f"    → {pages_crawled} page(s), {len(all_elements)} éléments")
    return all_elements


# ============================================================
# PDF GENERATION
# ============================================================

def safe_xml(text):
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def build_gov_table(rows):
    if not rows:
        return None
    num_cols = max(len(r) for r in rows)
    for row in rows:
        while len(row) < num_cols:
            row.append('')

    cell_style = ParagraphStyle('TC', fontName='Helvetica', fontSize=8.5,
                                leading=11, textColor=GOV_TEXT)
    formatted = [[Paragraph(safe_xml(c), cell_style) for c in row] for row in rows]

    avail = A4[0] - 30*mm
    table = Table(formatted, colWidths=[avail/num_cols]*num_cols, repeatRows=1)
    cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), GOV_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, GOV_LIGHT),
        ('LINEBELOW', (0, 0), (-1, 0), 1, GOV_RED),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]
    for i in range(1, len(formatted)):
        if i % 2 == 0:
            cmds.append(('BACKGROUND', (0, i), (-1, i), GOV_LIGHT))
    table.setStyle(TableStyle(cmds))
    return table


def elements_to_pdf(elements, pdf_path, theme_title, start_urls):
    styles = create_gov_styles()
    doc = SimpleDocTemplate(pdf_path, pagesize=A4,
                            topMargin=22*mm, bottomMargin=18*mm,
                            leftMargin=15*mm, rightMargin=15*mm)

    story = [Spacer(1, 3*mm)]
    story.append(Paragraph(safe_xml(theme_title), styles['Title']))
    story.append(HRFlowable(width="30%", thickness=3, color=GOV_RED,
                            spaceAfter=2*mm, spaceBefore=1*mm, hAlign='LEFT'))
    src = "Sources : " + " | ".join(start_urls)
    story.append(Paragraph(safe_xml(src), styles['Source']))

    seen = set()
    for etype, content in elements:
        if etype == 'separator':
            story.append(Spacer(1, 4*mm))
            story.append(HRFlowable(width="80%", thickness=1, color=GOV_BLUE,
                                    spaceAfter=4*mm, spaceBefore=2*mm, hAlign='CENTER'))
        elif etype == 'page_title':
            if content not in seen:
                seen.add(content)
                story.append(Paragraph(safe_xml(content), styles['PageTitle']))
        elif etype == 'note':
            story.append(Paragraph(safe_xml(content), styles['Note']))
        elif etype == 'h2':
            if content not in seen:
                seen.add(content)
                story.append(Paragraph(safe_xml(content), styles['H2']))
                story.append(HRFlowable(width="100%", thickness=0.5,
                                        color=GOV_LIGHT, spaceAfter=2*mm))
        elif etype == 'h3':
            if content not in seen:
                seen.add(content)
                story.append(Paragraph(safe_xml(content), styles['H3']))
        elif etype == 'body':
            if content not in seen:
                seen.add(content)
                story.append(Paragraph(safe_xml(content), styles['Body']))
        elif etype == 'bullet':
            if content not in seen:
                seen.add(content)
                b = f'<font color="{GOV_BLUE.hexval()}">\u2022</font>  {safe_xml(content)}'
                story.append(Paragraph(b, styles['Bullet']))
        elif etype == 'table':
            t = build_gov_table(content)
            if t:
                story.append(Spacer(1, 2*mm))
                story.append(t)
                story.append(Spacer(1, 3*mm))

    doc.build(story, onFirstPage=gov_header_footer, onLaterPages=gov_header_footer)


# ============================================================
# MAIN
# ============================================================
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  Scraping service-public.fr — {len(THEMES)} thèmes")
    print(f"  Avec crawling récursif des sous-pages")
    print(f"{'='*60}\n")

    for i, theme in enumerate(THEMES):
        print(f"[{i+1}/{len(THEMES)}] {theme['title']}")
        elements = crawl_theme(theme)
        if not elements:
            print(f"    ⚠ Aucun contenu\n")
            continue
        pdf_path = os.path.join(OUTPUT_DIR, f"{theme['filename']}.pdf")
        try:
            elements_to_pdf(elements, pdf_path, theme['title'], theme['start_urls'])
            print(f"    ✓ PDF: {pdf_path}\n")
        except Exception as e:
            print(f"    ✗ Erreur PDF: {e}\n")

    print(f"\n{'='*60}")
    print(f"  Terminé ! PDFs dans '{OUTPUT_DIR}/'")
    print(f"{'='*60}")
    print(f"\nStructure de data/ :")
    print(f"  data/")
    print(f"  ├── gouv/          ← Documents légaux")
    for t in THEMES:
        print(f"  │   ├── {t['filename']}.pdf")
    print(f"  └── novatech/      ← Documents internes NovaTech")
    print(f"      ├── 01_conges_payes_rtt.pdf ... 11_handicap_rqth.pdf")


if __name__ == "__main__":
    main()