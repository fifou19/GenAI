# Projet GenAI — Assistant RH Interne
## Résumé complet du projet (état actuel)

---

## 1. Contexte académique

Ce projet est l'évaluation finale du cours **Generative AI** (ESIEA, Master). Le sujet est libre mais doit être un **assistant IA spécialisé pour une industrie spécifique**, avec un prototype fonctionnel.

### Critères de notation (3 livrables, chacun = 1/3 de la note) :

**Code (1/3)** :
- Prototype fonctionnel avec interface web (Streamlit/Gradio)
- Prompt engineering avancé (system prompt, persona, few-shot, format JSON)
- RAG avec vector database locale et chunking pertinent
- Agents & Tool Use (au moins 1 outil externe : function calling, web search, ou code execution)

**Rapport (1/3)** :
- Architecture et choix techniques documentés
- Évaluation de fiabilité et biais
- Tracking d'hallucinations et tests de prompt injection

**Oral (1/3)** :
- Pitch business clair
- Démo live interactive
- Gestion du temps et Q&A

---

## 2. Sujet choisi : Assistant RH interne

### Le problème
Les salariés posent toujours les mêmes questions aux RH : congés, télétravail, remboursement de frais, arrêt maladie, onboarding, etc. Ça mobilise du temps RH sur des réponses répétitives qui existent déjà dans les documents de politique interne.

### La solution
Un assistant IA qui :
- **Répond aux questions RH** à partir des politiques internes ET du droit du travail
- **Cite les passages sources** (quel document, quel article)
- **Renvoie vers le bon formulaire** (MonEspace > Congés > Nouvelle demande, etc.)
- **Génère une checklist d'action** pour guider le salarié
- **Sait dire "je ne sais pas"** quand l'information n'est pas dans sa base

### Pourquoi c'est un bon sujet
- RAG naturel sur un corpus de documents structurés
- Tool use simple et concret (formulaire, checklist, routage vers le bon service)
- Facile à évaluer : bonne réponse vs mauvaise réponse (les règles sont objectives)
- Business case clair : réduction du temps RH, satisfaction employé
- Risques intéressants à tester : hallucination, confusion cadre/non-cadre, prompt injection

---

## 3. Corpus de données (ce qui est fait ✅)

### Approche hybride : Droit du travail (gouv) + Politique interne (entreprise fictive)

C'est exactement comme fonctionne un vrai service RH : il y a la loi (identique pour tous) et les règles spécifiques de l'entreprise (propres à chaque société). Notre assistant a les deux couches.

### Couche 1 — Documents légaux (service-public.fr)
10 PDF scrapés depuis service-public.fr, couvrant :

| # | Thème | Source |
|---|---|---|
| 01 | Congés payés | service-public.fr/F2258 |
| 02 | Congés événements familiaux | service-public.fr/F2278 + code.travail.gouv.fr |
| 03 | Télétravail secteur privé | service-public.fr/F13851 |
| 04 | Arrêt maladie (IJ + démarches) | service-public.fr/F3053 + F303 |
| 05 | Accident du travail / maladie pro | service-public.fr/F175 + F176 |
| 06 | Démission | service-public.fr/F2883 |
| 07 | Rupture conventionnelle | service-public.fr/F19030 |
| 08 | Licenciement | service-public.fr/F1848 + F133 + sous-pages |
| 09 | CPF (compte personnel de formation) | service-public.fr/F10705 |
| 10 | RQTH (handicap) | service-public.fr/F1650 |

Un script Python (`scrape_service_public.py`) scrape ces pages, suit les sous-pages liées, filtre le bruit (boutons de partage, glossaire, textes de loi dupliqués), et génère un PDF propre par thème.

### Couche 2 — Documents internes NovaTech Solutions (entreprise fictive)
11 PDF au style corporate (en-tête, tableaux, pieds de page) pour une entreprise tech fictive :

| # | Document | Contenu clé |
|---|---|---|
| 01 | Congés payés & RTT | 25 CP + 11 RTT cadres / 12 non-cadres, congés exceptionnels, don de jours |
| 02 | Télétravail | 3j cadres / 2j non-cadres, indemnité 10-30€/mois, interdit à l'étranger |
| 03 | Frais & déplacements | Barèmes train/avion (1ère classe cadres), plafonds repas/hôtel, TravelNova |
| 04 | Onboarding | Premier jour, période d'essai (2-8 mois), formations obligatoires, outils |
| 05 | Mutuelle & avantages | Harmonie Mutuelle 60% employeur, CSE, PEE/PERCO, mobilité durable |
| 06 | FAQ RH | Questions transversales les plus fréquentes |
| 07 | Arrêts maladie | Carence 0j cadres / 3j non-cadres, maintien salaire selon ancienneté, AT/MP |
| 08 | Formation & carrière | CPF, plan de formation 2% masse salariale, NovAcademy, mobilité interne |
| 09 | Entretiens & rémunération | Grille N1-N8, augmentation 2025 = 2.5% générale, primes, variable |
| 10 | Départ de l'entreprise | Démission (1-3 mois préavis), rupture co, licenciement, solde tout compte |
| 11 | Handicap & RQTH | Aménagements, télétravail 4j/sem, 2j absence/an, référent Marc Lefèvre |

### Complexité volontaire (niveau "moyen")
Les documents contiennent des **cas ambigus intentionnels** pour tester le RAG :
- Règles différentes cadre vs non-cadre (RTT, télétravail, carence maladie, train 1ère classe...)
- Règles qui varient selon l'ancienneté (maintien de salaire, congés supplémentaires)
- Informations croisées entre documents (titres restaurant dans frais ET onboarding)
- Chaque doc pointe vers des formulaires spécifiques sur "MonEspace" → base pour le tool use

### Trous volontaires (pour tester le "je ne sais pas")
Certains sujets sont intentionnellement absents : droit de grève, règlement intérieur, congé sabbatique, expatriation, droit syndical. L'assistant devra reconnaître qu'il n'a pas l'info et rediriger vers la DRH.

---

## 4. Architecture technique (en cours 🔧)

### Stack choisie

| Composant | Choix | Justification |
|---|---|---|
| **LLM** | Configurable (OpenAI, Anthropic, Mistral, Groq) | Flexibilité, peut comparer les providers |
| **Embedding** | sentence-transformers (all-MiniLM-L6-v2) | Gratuit, local, pas de coût API |
| **Vector store** | ChromaDB | Simple, local, persistant, bon pour un prototype |
| **Interface** | Streamlit | Demandé dans les critères, rapide à prototyper |
| **Chunking** | Hybride section + taille | Par article/section pour NovaTech, par question pour Gouv, fallback par taille avec overlap |

### Pipeline RAG

```
Question utilisateur
    → Embedding (sentence-transformers)
    → Recherche dans ChromaDB (top 5 chunks)
    → Contexte injecté dans le prompt
    → LLM génère une réponse structurée
    → Réponse avec : source citée + formulaire + checklist
```

### Structure du projet

```
hr-assistant/
├── data/
│   ├── gouv/              ← 10 PDF service-public.fr
│   ├── novatech/          ← 11 PDF internes NovaTech
│   ├── chroma_db/         ← Vector store (généré par ingest.py)
│   └── ingest.py          ← Pipeline d'ingestion (extraction, chunking, indexation)
├── src/
│   ├── config.py          ← Configuration centralisée (LLM, embedding, RAG params)
│   ├── rag.py             ← Pipeline retrieval + génération (à faire)
│   ├── prompts.py         ← System prompt, persona, few-shot (à faire)
│   ├── tools.py           ← Function calling : formulaire, checklist, routage (à faire)
│   └── __init__.py
├── eval/
│   ├── test_cases.json    ← Cas de test avec réponses attendues (à faire)
│   └── evaluate.py        ← Évaluation : hallucination, injection, précision (à faire)
├── app.py                 ← Interface Streamlit (à faire)
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md              ← Documentation complète (à faire)
```

### Ce qui est fait (étape 1 ✅)
- **`src/config.py`** : configuration centralisée avec support multi-LLM
- **`data/ingest.py`** : pipeline d'ingestion complet
  - Extraction texte PDF via pdfplumber
  - Nettoyage du bruit (en-têtes, pieds de page)
  - Chunking intelligent : par section/article pour NovaTech, par question pour Gouv, avec fallback par taille (800 tokens) + overlap (200 tokens)
  - Indexation dans ChromaDB avec sentence-transformers
  - Métadonnées riches : source (gouv/novatech), nom du document, index du chunk
- **`requirements.txt`**, **`.env.example`**, **`.gitignore`**
- **11 PDF NovaTech** générés avec mise en page corporate
- **Script de scraping** pour les 10 PDF service-public.fr

### Ce qui reste à faire
1. **`src/prompts.py`** — System prompt avec persona RH, few-shot examples, format de sortie JSON
2. **`src/rag.py`** — Pipeline retrieval (query ChromaDB) + génération (appel LLM avec contexte)
3. **`src/tools.py`** — Function calling : redirection formulaire, génération checklist, routage service
4. **`app.py`** — Interface Streamlit avec chat, historique, affichage des sources
5. **`eval/`** — Cas de test (questions avec réponses attendues), évaluation hallucination, tests prompt injection
6. **`README.md`** — Documentation architecture, choix techniques, résultats d'évaluation

---

## 5. Points de discussion / Feedback souhaité

1. **Corpus** : est-ce que 21 PDF (10 gouv + 11 NovaTech) c'est suffisant ? Trop ? Faut-il ajouter/retirer des thèmes ?

2. **Chunking** : la stratégie hybride (section pour NovaTech, question pour Gouv, fallback taille) est-elle pertinente ? Faut-il tester d'autres approches ?

3. **LLM configurable** : est-ce un plus pour le rapport (comparaison de providers) ou une complexité inutile ?

4. **Tool use** : les 3 outils prévus (formulaire, checklist, routage) sont-ils suffisants pour les critères "Agents & Tool Use" ?

5. **Évaluation** : quels types de tests seraient les plus intéressants à montrer dans le rapport ?

6. **Scope** : est-ce qu'on est trop ambitieux ou pas assez ? Y a-t-il un risque de ne pas finir à temps ?