#!/usr/bin/env python3
"""
Scraper v3 pour service-public.fr — CORRIGÉ
Corrections appliquées:
- gouv_02: URL corrigée (F2278 = congés décès secteur privé + code.travail.gouv.fr pour événements familiaux)
- gouv_03: supprimé (pas de fiche RTT dédiée sur service-public.fr)
- Filtrage agressif du bruit (partage, glossaire, horaires, feedback, textes de loi dupliqués)
- Dédoublonnage des tableaux de loi

Usage:
    pip install requests beautifulsoup4 reportlab
    python scrape_service_public.py
"""

import os, re, time, requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib import colors

# ============================================================
# CONFIGURATION — URLs CORRIGÉES
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
        "title": "Congés pour événements familiaux (secteur privé)",
        "start_urls": [
            # Congé décès famille (secteur privé)
            "https://www.service-public.fr/particuliers/vosdroits/F2278",
            # Page complète événements familiaux (ministère du travail)
            "https://code.travail.gouv.fr/contribution/les-conges-pour-evenements-familiaux",
        ],
        "follow_patterns": [r"/vosdroits/F2278", r"/vosdroits/F2812"],
        "max_pages": 4,
    },
    # gouv_03 RTT SUPPRIMÉ — pas de fiche dédiée sur service-public.fr
    # Les RTT sont couverts par les documents NovaTech internes
    {
        "filename": "gouv_03_teletravail",
        "title": "Télétravail dans le secteur privé",
        "start_urls": [
            "https://www.service-public.fr/particuliers/vosdroits/F13851",
        ],
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
        "start_urls": [
            "https://www.service-public.fr/particuliers/vosdroits/F2883",
        ],
        "follow_patterns": [r"/vosdroits/F2883"],
        "max_pages": 4,
    },
    {
        "filename": "gouv_07_rupture_conventionnelle",
        "title": "Rupture conventionnelle",
        "start_urls": [
            "https://www.service-public.fr/particuliers/vosdroits/F19030",
        ],
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
            r"/vosdroits/F987", r"/vosdroits/F31209",
        ],
        "max_pages": 10,
    },
    {
        "filename": "gouv_09_cpf",
        "title": "Compte personnel de formation (CPF)",
        "start_urls": [
            "https://www.service-public.fr/particuliers/vosdroits/F10705",
        ],
        "follow_patterns": [r"/vosdroits/F10705"],
        "max_pages": 4,
    },
    {
        "filename": "gouv_10_rqth",
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
# NOISE PATTERNS — tout ce qu'on veut SUPPRIMER
# ============================================================
SKIP_TEXTS = [
    # Boutons de partage et favoris
    'ajouter à mes favoris', 'partager la page', 'facebook', 'linkedin',
    'courriel', 'copier le lien', 'lien copié',
    # Alertes et abonnements
    'vous recevrez un courriel', 'vous recevrez un email',
    'vous devez vous connecter', 'votre abonnement',
    'vous pouvez à tout moment supprimer', 'ce sujet a été ajouté',
    'ce sujet vous intéresse', 'connectez-vous à votre compte',
    'pour vous abonner aux mises à jour', 'activer votre espace personnel',
    'vous serez alerté', 'le lien vers cette page',
    # Feedback et notation
    'cette page vous a-t-elle été utile', 'pas du tout', 'un peu',
    'beaucoup', 'parfait !', 'l\'équipe service public vous remercie',
    'je vais sur la page d\'accueil', 'je fais une remarque',
    'vos remarques pour améliorer', 'avez-vous rencontré une difficulté',
    'avez-vous des suggestions', 'vous avez noté',
    'pour des raisons de sécurité, nous ne pouvons valider',
    'merci de recharger la page', 'une erreur technique',
    # Allô Service Public / contacts génériques
    'allô service public', 'les informateurs qui vous répondent',
    'il ne répond pas aux questions portant sur l\'indemnisation',
    'être rappelé(e)', 'coût service gratuit',
    'horaireslundi', 'lundi : de 08h30', 'mardi : de 08h30',
    'mercredi : de 08h30', 'jeudi : de 08h30', 'vendredi : de 13h00',
    # Sections de navigation
    'questions ? réponses !', 'voir aussi', 'services en ligne et formulaires',
    'textes de loi et références', 'fiches pratiques par événement',
    'voir toutes les situations',
    # Instructions interactives
    'répondez aux questions successives', 'veuillez patienter',
    'accéder aux informations générales',
    # Cookies et vidéo
    'vidéo désactivée', 'accepter les cookies', 'pour lire la vidéo',
    # Navigation service-public
    'autres cas ?', 'dans le secteur public',
    'qui peut m\'aider', 'vous avez une question',
    'vous souhaitez être accompagné',
    'si vous dépendez du régime général', 'si vous dépendez du régime agricole',
    'renseignement administratif par téléphone',
    # Glossaire / définitions en fin de page
    'correspond à tous les jours de la semaine',
    'correspond à la totalité des jours du calendrier',
    'accord écrit négocié entre les représentants syndicaux',
    'résultat des négociations menées entre les partenaires sociaux',
    'convention collective, accord collectif, accord de branche',
    'pratique d\'application générale, constante et fixe',
    'jour effectivement travaillé dans une entreprise',
    'intervalle durant lequel le salarié doit avoir accompli',
    'enfant qui vit au foyer et qui a moins de',
    'personne désignée par la loi pour représenter',
    'lorsque l\'administration ne répond pas',
    'décision clairement exprimée par écrit',
    'période écoulée entre 2 événements',
    'janvier, février, mars, etc.',
    'période qui se déroule entre l\'ouverture',
    'maladie grave et/ou chronique ouvrant droit',
    'versées par la sécurité sociale aux salariés',
    'allemagne, autriche, belgique, bulgarie',
    'acronyme de système d\'identification',
    'formalité par laquelle un acte de procédure',
    'situation durant laquelle le paiement du salaire',
    'expiration d\'un droit après un certain délai',
    'première présentation au salarié du courrier',
    'un critère est discriminatoire s\'il fait partie',
    'licenciement annulé par un juge',
    'droits primordiaux visant à protéger',
    'juge qui assiste le président',
    'acte interdit par la loi et puni',
    'infraction la plus grave punissable',
    'double, copie d\'un document',
    'commune, département, région',
    'le répertoire spécifique recense',
    'personne dont la langue maternelle',
    'versement d\'une somme d\'argent',
    'finance l\'apprentissage, apporte',
    'état de santé stabilisé où la lésion',
    'médecin intervenant à la fois',
    'mariage, pacs ou concubinage',
    'raisons objectives et particulières',
    'du 1er janvier au 31 décembre',
    'opérateur de compétences',  # glossaire OPCO
    'association de gestion du fonds',  # glossaire Agefiph
    'répertoire national des certifications',  # glossaire RNCP
    'centre national des arts et métiers',  # glossaire CNAM
    'diplôme professionnel ou certification',
    'personne qui s\'occupe d\'un membre',
    'obligations alimentaires, devoirs de garde',
    'contrat de travail à durée indéterminée',  # glossaire CDI
    'contrat à durée déterminée',  # glossaire CDD
    'caisse primaire d\'assurance maladie',  # glossaire CPAM
    'mutualité sociale agricole',  # glossaire MSA
    'salaire minimum interprofessionnel',  # glossaire SMIC
    'maison départementale pour les personnes',  # glossaire MDPH
    'commission des droits pour l\'autonomie',  # glossaire CDAPH
    'comité social et économique',  # glossaire CSE (seul)
    'accord collectif conclu au niveau d\'une branche',
    'temps pendant lequel un salarié ou un agent',
    'correspond au temps de travail durant lequel',
    # Textes de loi dupliqués (la deuxième occurrence, sans bullet)
    'code du travail : articles',
    'code de la sécurité sociale : articles',
    'code de l\'action sociale',
    'code rural et de la pêche maritime',
    'code général de la fonction publique',
    'circulaire du', 'circulaire n°',
    'décret n°', 'arrêté du',
    'réponse ministérielle',
    # Liens "Service en ligne" / "Formulaire" / "Outil de recherche"
    'service en ligne', 'formulaire', 'outil de recherche',
    'modèle de document', 'simulateur',
    # Liens "Voir aussi" items
    'service public', 'ministère chargé',
    'caisse nationale', 'caisse des dépôts',
    'je suggère une modification',
    'saisie complémentaire requise',
    # Focus tag
    'focus',
]


def should_skip(text):
    """Returns True if the text is noise that should be filtered out."""
    lower = text.lower().strip()
    # Skip very short texts
    if len(lower) < 10:
        return True
    # Check against skip patterns
    for pattern in SKIP_TEXTS:
        if pattern in lower:
            return True
    # Skip standalone article references (e.g., "Droit au congé" after a code reference)
    if len(lower) < 60 and not any(c in lower for c in ['?', '.', ',']):
        # Likely a standalone label/title from law references
        return True
    return False


# ============================================================
# STYLES PDF
# ============================================================
GOV_BLUE = HexColor("#000091")
GOV_RED = HexColor("#E1000F")
GOV_GRAY = HexColor("#666666")
GOV_TEXT = HexColor("#1E1E1E")
GOV_LIGHT = HexColor("#F0F0F0")
WHITE = colors.white


def create_styles():
    return {
        'Title': ParagraphStyle('T', fontName='Helvetica-Bold', fontSize=18,
            leading=24, textColor=GOV_BLUE, spaceAfter=4*mm),
        'Source': ParagraphStyle('S', fontName='Helvetica', fontSize=9,
            leading=12, textColor=GOV_GRAY, spaceAfter=6*mm),
        'PageTitle': ParagraphStyle('PT', fontName='Helvetica-Bold', fontSize=13,
            leading=17, textColor=GOV_RED, spaceBefore=4*mm, spaceAfter=3*mm),
        'H2': ParagraphStyle('H2', fontName='Helvetica-Bold', fontSize=13,
            leading=17, textColor=GOV_BLUE, spaceBefore=8*mm, spaceAfter=3*mm),
        'H3': ParagraphStyle('H3', fontName='Helvetica-Bold', fontSize=11,
            leading=15, textColor=GOV_TEXT, spaceBefore=5*mm, spaceAfter=2*mm),
        'Body': ParagraphStyle('B', fontName='Helvetica', fontSize=9.5,
            leading=13.5, textColor=GOV_TEXT, spaceAfter=2*mm, alignment=TA_JUSTIFY),
        'Bullet': ParagraphStyle('BL', fontName='Helvetica', fontSize=9.5,
            leading=13.5, textColor=GOV_TEXT, leftIndent=8*mm,
            spaceAfter=1.5*mm, bulletIndent=3*mm),
        'Note': ParagraphStyle('N', fontName='Helvetica-Oblique', fontSize=9,
            leading=12, textColor=GOV_GRAY, spaceAfter=2*mm, leftIndent=4*mm),
    }


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
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(w-15*mm, h-11*mm, "Le site officiel de l'administration française")
    canvas.setStrokeColor(GOV_LIGHT)
    canvas.setLineWidth(0.5)
    canvas.line(15*mm, 12*mm, w-15*mm, 12*mm)
    canvas.setFillColor(GOV_GRAY)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(15*mm, 7*mm, "Source : service-public.fr — DILA")
    canvas.drawRightString(w-15*mm, 7*mm, f"Page {doc.page}")
    canvas.restoreState()


# ============================================================
# SCRAPING
# ============================================================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
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
    main = (soup.find('main') or soup.find('article') or
            soup.find('div', {'id': 'main'}) or soup.body)

    elements = []

    # Title
    h1 = main.find('h1')
    if h1:
        t = clean_text(h1.get_text())
        if t and not should_skip(t):
            elements.append(('page_title', t))

    # Date
    for tag in main.find_all(string=re.compile(r'Vérifié le')):
        t = clean_text(str(tag))
        if t:
            elements.append(('note', t))
            break

    # Content
    seen = set()
    in_law_section = False

    for tag in main.find_all(['h2', 'h3', 'h4', 'p', 'ul', 'ol', 'table']):
        if tag.find_parent(['nav', 'footer', 'form', 'aside', 'header']):
            continue

        if tag.name == 'h2':
            t = clean_text(tag.get_text())
            if should_skip(t):
                in_law_section = True  # Everything after "Textes de loi" is noise
                continue
            in_law_section = False
            if t and len(t) > 2 and t not in seen:
                seen.add(t)
                elements.append(('h2', t))

        elif tag.name in ['h3', 'h4']:
            if in_law_section:
                continue
            t = clean_text(tag.get_text())
            if should_skip(t):
                continue
            if t and len(t) > 2 and t not in seen:
                seen.add(t)
                elements.append(('h3', t))

        elif tag.name == 'p':
            if in_law_section:
                continue
            t = clean_text(tag.get_text())
            if should_skip(t):
                continue
            if t and len(t) > 15 and t not in seen:
                seen.add(t)
                elements.append(('body', t))

        elif tag.name in ['ul', 'ol']:
            if in_law_section:
                continue
            for li in tag.find_all('li', recursive=False):
                t = clean_text(li.get_text())
                if should_skip(t):
                    continue
                if t and len(t) > 10 and t not in seen:
                    seen.add(t)
                    elements.append(('bullet', t))

        elif tag.name == 'table':
            if in_law_section:
                continue
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
        if 'entreprendre.service-public' in full_url:
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
    follow_patterns = theme.get("follow_patterns", [])
    count = 0

    while to_visit and count < max_pages:
        url = to_visit.pop(0)
        norm = urlparse(url)
        norm_url = f"{norm.scheme}://{norm.netloc}{norm.path}"
        if norm_url in visited:
            continue
        visited.add(norm_url)

        print(f"    Scraping: {url}")
        try:
            elements, soup = scrape_page(url)
            count += 1
            if elements:
                if all_elements:
                    all_elements.append(('separator', None))
                all_elements.extend(elements)
            if follow_patterns:
                for link in extract_sub_links(soup, url, follow_patterns):
                    ln = urlparse(link)
                    if f"{ln.scheme}://{ln.netloc}{ln.path}" not in visited:
                        to_visit.append(link)
            time.sleep(2)
        except Exception as e:
            print(f"    ✗ Error: {e}")

    print(f"    → {count} page(s), {len(all_elements)} elements")
    return all_elements


# ============================================================
# PDF
# ============================================================
def safe_xml(text):
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def build_table(rows):
    if not rows:
        return None
    ncols = max(len(r) for r in rows)
    for r in rows:
        while len(r) < ncols:
            r.append('')
    cs = ParagraphStyle('TC', fontName='Helvetica', fontSize=8.5, leading=11, textColor=GOV_TEXT)
    fmt = [[Paragraph(safe_xml(c), cs) for c in row] for row in rows]
    avail = A4[0] - 30*mm
    t = Table(fmt, colWidths=[avail/ncols]*ncols, repeatRows=1)
    cmds = [
        ('BACKGROUND', (0,0), (-1,0), GOV_BLUE),
        ('TEXTCOLOR', (0,0), (-1,0), WHITE),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, GOV_LIGHT),
        ('LINEBELOW', (0,0), (-1,0), 1, GOV_RED),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]
    for i in range(1, len(fmt)):
        if i % 2 == 0:
            cmds.append(('BACKGROUND', (0,i), (-1,i), GOV_LIGHT))
    t.setStyle(TableStyle(cmds))
    return t


def to_pdf(elements, path, title, urls):
    styles = create_styles()
    doc = SimpleDocTemplate(path, pagesize=A4,
        topMargin=22*mm, bottomMargin=18*mm, leftMargin=15*mm, rightMargin=15*mm)

    story = [Spacer(1, 3*mm)]
    story.append(Paragraph(safe_xml(title), styles['Title']))
    story.append(HRFlowable(width="30%", thickness=3, color=GOV_RED,
        spaceAfter=2*mm, spaceBefore=1*mm, hAlign='LEFT'))
    story.append(Paragraph(safe_xml("Sources : " + " | ".join(urls)), styles['Source']))

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
                story.append(HRFlowable(width="100%", thickness=0.5, color=GOV_LIGHT, spaceAfter=2*mm))
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
                story.append(Paragraph(
                    f'<font color="{GOV_BLUE.hexval()}">\u2022</font>  {safe_xml(content)}',
                    styles['Bullet']))
        elif etype == 'table':
            t = build_table(content)
            if t:
                story.append(Spacer(1, 2*mm))
                story.append(t)
                story.append(Spacer(1, 3*mm))

    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)


# ============================================================
# MAIN
# ============================================================
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"\n{'='*60}")
    print(f"  Scraping service-public.fr v3 — {len(THEMES)} thèmes")
    print(f"  Avec filtrage du bruit + URLs corrigées")
    print(f"{'='*60}\n")

    for i, theme in enumerate(THEMES):
        print(f"[{i+1}/{len(THEMES)}] {theme['title']}")
        elements = crawl_theme(theme)
        if not elements:
            print(f"    ⚠ Aucun contenu\n")
            continue
        path = os.path.join(OUTPUT_DIR, f"{theme['filename']}.pdf")
        try:
            to_pdf(elements, path, theme['title'], theme['start_urls'])
            print(f"    ✓ PDF: {path}\n")
        except Exception as e:
            print(f"    ✗ Erreur PDF: {e}\n")

    print(f"\n{'='*60}")
    print(f"  Terminé ! {len(THEMES)} PDFs dans '{OUTPUT_DIR}/'")
    print(f"{'='*60}")
    print(f"\nStructure de data/ :")
    print(f"  data/")
    print(f"  ├── gouv/          ← Documents légaux (service-public.fr)")
    for t in THEMES:
        print(f"  │   ├── {t['filename']}.pdf")
    print(f"  └── novatech/      ← Documents internes NovaTech")
    print(f"      ├── 01_conges_payes_rtt.pdf ... 11_handicap_rqth.pdf")


if __name__ == "__main__":
    main()
