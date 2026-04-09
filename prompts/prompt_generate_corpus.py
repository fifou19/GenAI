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