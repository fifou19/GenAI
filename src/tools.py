"""
Tool use / function calling for the HR assistant.
3 tools:
  - get_form_link: returns the link to the right MonEspace form
  - generate_checklist: generates generic practical next steps for the employee
  - route_to_contact: routes the employee to the appropriate HR contact
"""

import re
import unicodedata

# ============================================================
# INTERNAL FORMS
# ============================================================
FORMS = {
    "conges": {
        "name": "Leave request",
        "path": "MonEspace > My leave > New request",
        "url": "https://monespace.novatech-solutions.fr/conges/nouvelle-demande",
    },
    "rtt": {
        "name": "RTT request",
        "path": "MonEspace > My leave > RTT",
        "url": "https://monespace.novatech-solutions.fr/conges/rtt",
    },
    "teletravail": {
        "name": "Telework declaration",
        "path": "MonEspace > Telework > Weekly schedule",
        "url": "https://monespace.novatech-solutions.fr/teletravail/planning",
    },
    "frais": {
        "name": "Expense report",
        "path": "MonEspace > My expenses > New report",
        "url": "https://monespace.novatech-solutions.fr/frais/nouvelle-note",
    },
    "formation": {
        "name": "Training request",
        "path": "MonEspace > Training > New request",
        "url": "https://monespace.novatech-solutions.fr/formation/demande",
    },
    "arret_maladie": {
        "name": "Sick leave declaration",
        "path": "MonEspace > Absences > Sick leave",
        "url": "https://monespace.novatech-solutions.fr/absences/arret-maladie",
    },
    "accident_travail": {
        "name": "Work accident declaration",
        "path": "MonEspace > Absences > Work accident",
        "url": "https://monespace.novatech-solutions.fr/absences/accident-travail",
    },
    "demission": {
        "name": "Departure procedure",
        "path": "MonEspace > My departure > Start",
        "url": "https://monespace.novatech-solutions.fr/depart/initier",
    },
    "handicap": {
        "name": "Accommodation request",
        "path": "MonEspace > Disability > Accommodation request",
        "url": "https://monespace.novatech-solutions.fr/handicap/amenagement",
    },
    "entretien": {
        "name": "Annual review self-assessment",
        "path": "MonEspace > Reviews > Self-assessment",
        "url": "https://monespace.novatech-solutions.fr/entretiens/auto-evaluation",
    },
    "mutuelle": {
        "name": "Health insurance management",
        "path": "MonEspace > My insurance > Edit",
        "url": "https://monespace.novatech-solutions.fr/mutuelle/modifier",
    },
    "mobilite": {
        "name": "Internal mobility application",
        "path": "MonEspace > Career > Internal mobility",
        "url": "https://monespace.novatech-solutions.fr/carriere/mobilite",
    },
}


# ============================================================
# HR CONTACTS
# ============================================================
CONTACTS = {
    "administration": {
        "name": "Sophie Martin",
        "role": "Head of Personnel Administration",
        "email": "sophie.martin@novatech-solutions.fr",
        "topics": ["congés", "contrat", "attestation", "bulletin", "administration", "leave", "contract", "payslip", "payroll", "administrative"],
    },
    "qvt": {
        "name": "Lucas Dupont",
        "role": "QVT Project Manager",
        "email": "lucas.dupont@novatech-solutions.fr",
        "topics": ["bien-être", "qvt", "télétravail", "ergonomie", "well-being", "telework", "remote work", "ergonomics"],
    },
    "comptabilite": {
        "name": "Claire Lefebvre",
        "role": "Supplier Accounting Manager",
        "email": "claire.lefebvre@novatech-solutions.fr",
        "topics": ["frais", "remboursement", "note de frais", "déplacement", "voyage", "transport", "expense", "reimbursement", "travel", "business travel"],
    },
    "recrutement": {
        "name": "Amina Khelifi",
        "role": "Recruitment and Onboarding Specialist",
        "email": "amina.khelifi@novatech-solutions.fr",
        "topics": ["onboarding", "intégration", "recrutement", "période d'essai", "embauche", "recruitment", "hiring", "probation"],
    },
    "compensation": {
        "name": "Thomas Bernard",
        "role": "Compensation & Benefits Manager",
        "email": "thomas.bernard@novatech-solutions.fr",
        "topics": ["salaire", "augmentation", "variable", "prime", "mutuelle", "épargne", "pee", "perco", "rémunération", "salary", "raise", "bonus", "benefits", "insurance"],
    },
    "formation": {
        "name": "Isabelle Morel",
        "role": "Training and Development Manager",
        "email": "isabelle.morel@novatech-solutions.fr",
        "topics": ["formation", "cpf", "novacademy", "carrière", "mobilité", "développement", "training", "career", "learning", "development"],
    },
    "handicap": {
        "name": "Marc Lefèvre",
        "role": "Disability Advisor",
        "email": "marc.lefevre@novatech-solutions.fr",
        "phone": "Poste 7890",
        "topics": ["handicap", "rqth", "aménagement", "disability", "accommodation"],
    },
    "medecin": {
        "name": "Dr. Émilie Renaud",
        "role": "Occupational Physician",
        "email": "",
        "topics": ["visite médicale", "aptitude", "arrêt", "maladie", "accident", "medical visit", "fitness", "sick leave"],
    },
    "harcelement": {
        "name": "Nathalie Brun",
        "role": "Harassment Advisor",
        "email": "",
        "topics": ["harcèlement", "discrimination", "signalement", "harassment", "discrimination", "report"],
    },
}


# ============================================================
# KEYWORD MATCHERS
# ============================================================
FORM_KEYWORDS = {
    "conges": ["congé", "congés", "vacances", "repos", "leave", "vacation", "paid leave"],
    "rtt": ["rtt", "réduction du temps", "temps de travail", "time off", "reduced working time"],
    "teletravail": ["télétravail", "remote", "télé", "travail à distance", "telework", "teleworking", "remote work"],
    "frais": ["frais", "note de frais", "remboursement", "déplacement", "transport", "expense", "expenses", "expense report", "travel expense"],
    "formation": ["formation", "cpf", "novacademy", "compte personnel", "training", "development", "learning"],
    "arret_maladie": ["maladie", "arrêt maladie", "certificat médical", "arrêt", "sick leave", "illness", "medical certificate"],
    "accident_travail": ["accident", "accident du travail", "travaill", "work accident", "accident at work", "occupational accident"],
    "demission": ["démission", "départ", "rupture", "preavis", "resignation", "departure", "quit", "notice"],
    "handicap": ["handicap", "rqth", "aménagement", "disability", "accommodation"],
    "entretien": ["entretien", "auto-évaluation", "objectif", "bilan", "review", "performance review", "appraisal", "goals"],
    "mutuelle": ["mutuelle", "prévoyance", "complémentaire santé", "health insurance", "benefits"],
    "mobilite": ["mobilité", "candidature interne", "mobilité interne", "internal mobility", "internal transfer", "career move"],
}

CHECKLIST_KEYWORDS = {
    "leave": ["congé", "congés", "vacances", "repos", "leave", "vacation"],
    "telework": ["télétravail", "remote", "travail à distance", "home office", "telework", "teleworking", "remote work"],
    "sick_leave": ["arrêt maladie", "maladie", "certificat médical", "arrêt", "sick leave", "illness"],
    "departure": ["démission", "départ", "rupture", "préavis", "resignation", "departure", "notice"],
    "accident": ["accident", "accident du travail", "work accident", "accident at work"],
    "training": ["formation", "cpf", "novacademy", "training", "learning"],
    "onboarding": ["onboarding", "intégration", "nouvel arrivant", "arrivée", "new hire", "arrival"],
}


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.lower()


def contains_keyword(text: str, keyword: str) -> bool:
    text = normalize_text(text)
    keyword = normalize_text(keyword)
    if " " in keyword or "-" in keyword:
        return keyword in text
    return bool(re.search(rf"\b{re.escape(keyword)}\b", text))


def find_matching_key(keyword_map: dict, topic: str) -> str | None:
    topic_normalized = normalize_text(topic)
    for key, keywords in keyword_map.items():
        for keyword in keywords:
            if contains_keyword(topic_normalized, keyword):
                return key
    return None


# ============================================================
# TOOL FUNCTIONS
# ============================================================
def get_form_link(topic: str) -> dict:
    """Return the form that matches the topic."""
    form_key = find_matching_key(FORM_KEYWORDS, topic)
    if not form_key:
        return {
            "found": False,
            "message": "No form found. Contact Sophie Martin (sophie.martin@novatech-solutions.fr).",
        }

    form = FORMS[form_key]
    return {
        "found": True,
        "name": form["name"],
        "path": form["path"],
        "url": form["url"],
        "match": form_key,
    }


def generate_checklist(topic: str) -> dict:
    """Generate generic next steps without asserting policy or legal rules."""
    checklist_key = find_matching_key(CHECKLIST_KEYWORDS, topic)
    if not checklist_key:
        return {"found": False, "message": "No checklist available for this topic."}

    checklists = {
        "leave": [
            "Review the policy details given in the answer above before taking action",
            "Open the relevant leave form in MonEspace if you are ready to submit a request",
            "Prepare any supporting documents that may be needed for your case",
            "Inform your manager if coordination is required",
            "Contact HR if your situation is unusual or urgent",
        ],
        "telework": [
            "Review the telework conditions mentioned in the answer above",
            "Open the telework planning form in MonEspace if you need to declare days",
            "Confirm your schedule with your manager if needed",
            "Make sure you have the required equipment and a suitable setup",
            "Contact HR if your case requires an exception",
        ],
        "sick_leave": [
            "Inform your manager as soon as possible",
            "Use the dedicated absence form in MonEspace if a declaration is needed",
            "Prepare the medical documents requested by HR or the relevant administration",
            "Keep copies of the supporting documents you submit",
            "Contact HR if you need help with follow-up or return-to-work steps",
        ],
        "departure": [
            "Review the departure information given in the answer above",
            "Start the departure workflow in MonEspace if you are ready to proceed",
            "List the documents, equipment, and ongoing work that may need handover",
            "Coordinate the next steps with your manager and HR",
            "Contact HR directly if your departure case is urgent or atypical",
        ],
        "accident": [
            "Inform your manager and HR as soon as possible",
            "Seek medical attention if needed and keep the related documents",
            "Use the dedicated declaration process in MonEspace if applicable",
            "Keep a record of the key facts and supporting information",
            "Contact HR if you need help with the administrative follow-up",
        ],
        "training": [
            "Review the training information mentioned in the answer above",
            "Discuss the request with your manager if validation is needed",
            "Open the training request form in MonEspace if you want to proceed",
            "Gather the information needed to describe the training and its objective",
            "Contact the training team if you need guidance on eligibility or funding",
        ],
        "onboarding": [
            "Review the onboarding information available to you",
            "Complete the required administrative steps in MonEspace",
            "Prepare the personal documents requested by HR",
            "Reach out to your manager or HR if practical information is missing",
            "Use your onboarding contact if you hit a blocker before your first days",
        ],
    }

    return {
        "found": True,
        "topic": checklist_key,
        "items": checklists[checklist_key],
        "scope": "generic_next_steps",
    }


def route_to_contact(topic: str) -> dict:
    """Find the right HR contact for the given topic."""
    topic_normalized = normalize_text(topic)
    scores = {}

    for key, contact in CONTACTS.items():
        for keyword in contact["topics"]:
            if contains_keyword(topic_normalized, keyword):
                scores[key] = scores.get(key, 0) + 1

    if not scores:
        return {"found": False, "message": "No specific contact found."}

    best_key = max(scores, key=scores.get) # type: ignore
    contact = CONTACTS[best_key]
    return {
        "found": True,
        "name": contact["name"],
        "role": contact["role"],
        "email": contact["email"],
        "match_count": scores[best_key],
    }


def detect_tools(topic: str) -> list[dict]:
    """Detect relevant HR tools from the question."""
    tools = []

    form = get_form_link(topic)
    if form["found"]:
        tools.append({
            "type": "form",
            "name": form["name"],
            "path": form["path"],
            "url": form["url"],
            "match": form["match"],
        })

    checklist = generate_checklist(topic)
    if checklist["found"]:
        tools.append({
            "type": "checklist",
            "items": checklist["items"],
            "topic": checklist["topic"],
        })

    contact = route_to_contact(topic)
    if contact["found"]:
        tools.append({
            "type": "contact",
            "name": contact["name"],
            "role": contact["role"],
            "email": contact["email"],
            "match_count": contact["match_count"],
        })

    return tools




def execute_tool_call(tool_name: str, arguments: dict) -> dict:
    """Execute the tool requested by the model."""
    if tool_name == "get_form_link":
        return get_form_link(arguments.get("topic", ""))
    if tool_name == "generate_checklist":
        return generate_checklist(arguments.get("topic", ""))
    if tool_name == "route_to_contact":
        return route_to_contact(arguments.get("topic", ""))

    return {"found": False, "message": f"Tool '{tool_name}' is not recognized."}


# ============================================================
# TOOL DEFINITIONS (for function calling with LLMs)
# ============================================================
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_form_link",
            "description": "Returns the link to the appropriate MonEspace HR form for a given topic",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "The HR topic (e.g. 'leave', 'telework', 'expenses')"}
                },
                "required": ["topic"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_checklist",
            "description": "Generates generic practical next steps for the employee based on the HR topic",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "The HR topic (e.g. 'departure', 'sick leave', 'onboarding')"}
                },
                "required": ["topic"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "route_to_contact",
            "description": "Routes the employee to the appropriate HR contact person",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "The HR topic to find the right contact for"}
                },
                "required": ["topic"]
            }
        }
    },
]

# ============================================================
# END OF FILE
# ============================================================

