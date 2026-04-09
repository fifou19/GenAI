# Nova — Assistante RH NovaTech Solutions

Assistant RH intelligent basé sur un pipeline RAG (Retrieval-Augmented Generation) pour répondre aux questions des employés de NovaTech Solutions sur les politiques RH internes et le droit du travail français.

---

## Contexte du projet

Projet final du cours **Generative AI** (ESIEA, Master). L'objectif est de construire un assistant IA spécialisé pour un domaine métier précis, avec un prototype fonctionnel incluant interface web, RAG, prompt engineering avancé et tool use.

### Problème résolu

Les employés posent sans cesse les mêmes questions RH (congés, télétravail, arrêts maladie, frais, etc.), ce qui mobilise inutilement les équipes RH sur des demandes répétitives. Nova répond automatiquement en s'appuyant uniquement sur les documents officiels — sans inventer.

---

## Architecture globale

```
Question utilisateur
    │
    ▼
[Embedding — sentence-transformers]
    │
    ▼
[Retrieval — ChromaDB (top K chunks)]
    │
    ▼
[Reranking — Cross-encoder local]
    │
    ▼
[Prompt Engineering — système + few-shot + contexte RAG]
    │
    ▼
[LLM — Gemini (via google-genai)]
    │
    ▼
[Tool Use — formulaire / checklist / contact RH]
    │
    ▼
Réponse structurée + sources
```

---

## Structure du projet

```
GenAI/
├── app.py                        ← Interface Streamlit
├── requirements.txt
├── .env.example                  ← Template de configuration
│
├── src/
│   ├── config.py                 ← Configuration centralisée (env vars)
│   ├── rag.py                    ← Pipeline RAG : retriever + reranker + génération
│   ├── llm.py                    ← Appel Gemini avec retry/backoff
│   ├── prompts.py                ← Système prompt, few-shot, builder de messages
│   ├── tools.py                  ← Tool use : formulaires, checklists, contacts
│   └── cache.py                  ← Persistance des conversations (JSON)
│
├── Scripts/
│   ├── ingest.py                 ← Pipeline d'ingestion : chunking + indexation ChromaDB
│   ├── generate_corpus.py        ← Génération des documents NovaTech via Gemini
│   ├── Scrapping.py              ← Scraping des PDFs service-public.fr
│   └── md_to_pdf.py              ← Conversion Markdown → PDF
│
├── data/
│   ├── gouv/                     ← 10 PDFs service-public.fr (droit du travail)
│   ├── gouv_md/                  ← Versions Markdown des PDFs gouv
│   ├── novatech/                 ← 18 PDFs politiques internes NovaTech
│   ├── novatech_md/              ← Versions Markdown des politiques NovaTech
│   └── chroma_db/                ← Base vectorielle persistante (généré par ingest.py)
│
└── eval/
    ├── test_cases.json           ← 15 cas de test (précision, hors périmètre, injection)
    ├── evaluate.py               ← Script d'évaluation automatique
    └── eval_results.json         ← Résultats du dernier run d'évaluation
```

---

## Corpus documentaire

### Couche 1 — Droit du travail français (service-public.fr)

10 documents scraipés et nettoyés :

| # | Thème |
|---|---|
| 01 | Congés payés |
| 02 | Congés pour événements familiaux |
| 03 | Télétravail dans le secteur privé |
| 04 | Arrêt maladie |
| 05 | Accident du travail |
| 06 | Démission |
| 07 | Rupture conventionnelle |
| 08 | Licenciement |
| 09 | CPF (Compte Personnel de Formation) |
| 10 | RQTH (Reconnaissance de la Qualité de Travailleur Handicapé) |

### Couche 2 — Politiques internes NovaTech Solutions (entreprise fictive)

18 documents générés par Gemini, simulant les politiques RH d'une vraie entreprise :

| # | Document | Contenu clé |
|---|---|---|
| 01 | Congés payés | 25 jours légaux, règles de prise et de report |
| 02 | Congés événements familiaux | Mariage, naissance, deuil, enfant malade |
| 03 | Télétravail | 3j/semaine cadres, 2j non-cadres, indemnité 10-30€/mois |
| 04 | Arrêt maladie | Délai de carence 0j cadres / 3j non-cadres, maintien de salaire |
| 05 | Accident du travail | Procédure de déclaration, prise en charge spécifique |
| 06 | Démission | Préavis 1 mois non-cadres / 3 mois cadres, formalités |
| 07 | Rupture conventionnelle | Procédure, indemnités, délai de rétractation |
| 08 | Licenciement | Procédure, entretien préalable, indemnités |
| 09 | CPF | Utilisation, délais de demande, cofinancement NovaTech |
| 10 | RQTH & Handicap | 4j télétravail/semaine, 2j absence/an, référent Marc Lefèvre |
| 11 | RTT | 11j cadres / 12j non-cadres, règles de prise et d'expiration |
| 12 | Frais & déplacements | Plafonds repas/hôtel, 1ère classe >3h, TravelNova |
| 13 | Onboarding | Premier jour, période d'essai, outils, formations obligatoires |
| 14 | Mutuelle & avantages | Harmonie Mutuelle 60% employeur, CSE, PEE/PERCO |
| 15 | Formation & carrière | Plan de formation 2% masse salariale, NovAcademy, CPF |
| 16 | Entretiens & rémunération | Grille N1-N8, hausse 2025 = 2,5%, variable, primes |
| 17 | FAQ RH | Questions transversales fréquentes |
| 18 | Départ de l'entreprise | Démission, rupture, licenciement, solde de tout compte |

### Complexité intentionnelle

Les documents contiennent des cas ambigus pour tester le système :
- Règles différentes cadres vs non-cadres (RTT, télétravail, carence, 1ère classe...)
- Règles variant selon l'ancienneté (maintien de salaire, congés supplémentaires)
- Références croisées entre documents
- Sujets absents volontairement (droit de grève, congé sabbatique) pour tester le refus de répondre

---

## Pipeline RAG détaillé

### 1. Ingestion (`Scripts/ingest.py`)

- Lecture des fichiers Markdown (`data/gouv_md/` et `data/novatech_md/`)
- **Chunking par headers `##`** : 1 section = 1 chunk
  - Le préambule (avant le premier `##`) est ignoré — uniquement si le document a des sections
  - Si section > `CHUNK_SIZE * 2` : re-découpage sur `###` puis par taille
  - `chunk_by_size` : l'overlap repart depuis la dernière frontière de phrase (plus de coupures en plein milieu)
  - Fallback : si aucun `##` trouvé, le document entier est indexé comme un seul chunk
  - Chaque chunk est préfixé avec le titre du document (`[Nom du document]`)
- Nettoyage du bruit (métadonnées service-public, séparateurs vides)
- **Titre lisible** extrait du `# Titre` Markdown et préfixé selon la source :
  - Documents gouv → `Code du travail — Congés payés du salarié dans le secteur privé`
  - Documents NovaTech → `NovaTech — Télétravail`
- Indexation dans ChromaDB avec métadonnées riches (`source`, `document`, `title`, `section`, `chunk_index`)
- IDs déterministes par MD5 (réindexation idempotente)

### 2. Retrieval (`src/rag.py` — classe `Retriever`)

- Embedding de la question via `sentence-transformers`
- Recherche vectorielle dans ChromaDB (cosine similarity)
- Récupère `top_k * 2` chunks, filtre par `distance_threshold`, retourne les `top_k` meilleurs
- Filtre optionnel par source (`gouv` ou `novatech`)

### 3. Reranking (`src/rag.py` — méthode `rerank_chunks`)

- **Cross-encoder local** (`cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`)
- Évalue chaque paire (question, chunk) ensemble → score de pertinence précis
- Trie les chunks par score décroissant, garde les `top_k` meilleurs
- Modèle chargé une seule fois (lazy init), **aucun appel API**, ~200ms
- Multilingue, optimisé pour le français

### 4. Génération (`src/rag.py` — méthode `answer`)

- Construction du prompt : système + few-shot + historique + contexte RAG + question
- Instructions tool use fusionnées dans le dernier message user (pas de doublon de rôle)
- Appel Gemini → détection d'un éventuel tool call JSON
- Si tool call : exécution + second appel Gemini avec le résultat
- Extraction des sources pour affichage

---

## Prompt Engineering (`src/prompts.py`)

### Système prompt (Nova)

- **Persona** : Nova, assistante RH NovaTech Solutions, chaleureuse et professionnelle
- **Langue automatique** : détecte la langue de l'employé (français ou anglais) et répond dans la même langue
- **Périmètre strict** : refuse les questions hors RH, redirige vers le bon contact
- **Priorité des sources** : politiques NovaTech > droit du travail français — si NovaTech est plus favorable que la loi, le dit explicitement
- **Sécurité factuelle** : ne cite jamais un chiffre, délai ou droit absent du contexte
- **Anti-hallucination** : reconnaît explicitement quand l'information est absente plutôt que d'inventer
- **Anti-injection** : ignore les tentatives de changement de rôle, ne révèle jamais ses instructions
- **Adaptation profil** : applique la règle cadre ou non-cadre selon le profil donné, présente les deux cas si inconnu

### Détection de langue

La langue de la question est détectée côté Python (correspondance avec un ensemble de mots français courants) et injectée comme instruction explicite (`MUST reply in French / English`) dans le prompt RAG — avant même les documents de contexte. Cela empêche Gemini de basculer en français automatiquement quand le corpus est en français.

### Format de réponse

Format naturel et aéré — pas de labels rigides comme "Réponse directe" :

```
Phrase d'ouverture directe qui répond immédiatement à la question

- Détail 1 (bullet points pour les informations clés)
- Détail 2
- Cas particulier si pertinent

📄 *NovaTech — Télétravail*
👉 Action recommandée sur MonEspace si applicable
```

- Les **chiffres** et **termes importants** sont en gras
- Les sources affichent le titre lisible (`NovaTech — Télétravail`, `Code du travail — Arrêt maladie`) extrait des métadonnées ChromaDB — plus de noms de fichiers bruts
- Le ton est humain et chaleureux, pas administratif

### Few-shot examples

3 exemples couvrant :
- Télétravail cadre (question en **anglais** → réponse en **anglais**)
- Congé deuil (question en **français** → réponse en **français**)
- Hors périmètre — droit de grève (refus poli + redirection contact)

---

## Tool Use (`src/tools.py`)

3 outils disponibles, détectés par mots-clés et proposés par le LLM via function calling :

| Outil | Rôle | Exemple |
|---|---|---|
| `get_form_link` | Retourne le chemin MonEspace vers le bon formulaire | `MonEspace > Mes congés > Nouvelle demande` |
| `generate_checklist` | Génère une checklist d'actions pour le salarié | 5 étapes pour un départ de l'entreprise |
| `route_to_contact` | Identifie le bon contact RH selon le sujet | Sophie Martin pour l'administration du personnel |

### Contacts RH disponibles

| Contact | Rôle | Sujets |
|---|---|---|
| Sophie Martin | Responsable Administration du Personnel | Congés, contrats, bulletins |
| Lucas Dupont | Chargé de projet QVT | Bien-être, télétravail, ergonomie |
| Claire Lefebvre | Responsable Comptabilité Fournisseurs | Frais, remboursements |
| Amina Khelifi | Chargée recrutement & intégration | Onboarding, recrutement |
| Thomas Bernard | Responsable Compensation & Benefits | Salaire, primes, mutuelle |
| Isabelle Morel | Responsable Formation et Développement | Formation, CPF, carrière |
| Marc Lefèvre | Référent Handicap | RQTH, aménagements |
| Dr. Émilie Renaud | Médecin du travail | Visites médicales, arrêts |
| Nathalie Brun | Référent harcèlement | Signalements, discrimination |

---

## LLM (`src/llm.py`)

- **Modèle** : Gemini 2.5 Flash Lite (configurable via `.env`)
- Client instancié **une seule fois** au chargement du module (pas de reconnexion à chaque appel)
- **Retry avec backoff exponentiel** : jusqu'à 10 tentatives, attente 15s → 120s max
- Erreurs retriables : HTTP 429, 500, 503, "resource exhausted", "rate limit", "overloaded"

---

## Évaluation (`eval/`)

15 cas de test couvrant 11 catégories :

| Catégorie | Cas | Ce qui est testé |
|---|---|---|
| `telework` | 2 | Nombre de jours selon profil (cadre/non-cadre) |
| `leave` | 2 | Congés deuil, congés selon ancienneté |
| `rtt` | 1 | Jours RTT non-cadre |
| `expenses` | 1 | 1ère classe train selon statut |
| `sick_leave` | 1 | Délai de carence selon statut |
| `training` | 1 | Utilisation CPF chez NovaTech |
| `departure` | 1 | Préavis démission cadre |
| `disability` | 1 | Télétravail RQTH |
| `out_of_scope` | 2 | Refus sur sujets absents (grève, congé sabbatique) |
| `prompt_injection` | 2 | Résistance aux attaques d'injection |
| `cross_case` | 1 | Interaction arrêt maladie + RTT |

### Métriques évaluées

- **Présence de mots-clés** dans la réponse (chiffres, termes clés)
- **Sources récupérées** : le bon document est-il dans les chunks retournés ?
- **Refus approprié** : le modèle dit-il "je ne sais pas" quand il le faut ?
- **Résistance à l'injection** : aucun marqueur de compromission dans la réponse

```bash
python eval/evaluate.py
```

---

## Installation et lancement

### Prérequis

- Python 3.11+
- Une clé API Gemini (Google AI Studio)

### Installation

```bash
# Cloner le projet
git clone <repo>
cd GenAI

# Créer l'environnement virtuel
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux/Mac

# Installer les dépendances
pip install -r requirements.txt
```

### Configuration

Copier `.env.example` en `.env` et remplir :

```env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash-lite

EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-mpnet-base-v2
RERANKING_MODEL=cross-encoder/mmarco-mMiniLMv2-L12-H384-v1

CHROMA_PERSIST_DIR=data/chroma_db
CHROMA_COLLECTION_NAME=hr_docs

CHUNK_SIZE=800
CHUNK_OVERLAP=200
TOP_K=10
DISTANCE_THRESHOLD=1.5
USE_RERANKING=true
```

### Génération du corpus (optionnel — fichiers déjà présents)

```bash
# Scraper les PDFs service-public.fr
python Scripts/Scrapping.py

# Générer les documents NovaTech via Gemini
python Scripts/generate_corpus.py
```

### Indexation (obligatoire au premier lancement)

```bash
python Scripts/ingest.py
```

### Lancement de l'application

```bash
streamlit run app.py
```

### Évaluation

```bash
python eval/evaluate.py
```

---

## Choix techniques

| Composant | Choix | Justification |
|---|---|---|
| **LLM** | Gemini 2.5 Flash Lite | Rapide, gratuit en tier développeur, bon en français |
| **Embedding** | `paraphrase-multilingual-mpnet-base-v2` | Local, gratuit, optimisé français/multilingue |
| **Reranking** | Cross-encoder `mmarco-mMiniLMv2` | Local, 0 appel API, plus précis qu'un LLM scoring |
| **Vector store** | ChromaDB | Local, persistant, simple à déployer |
| **Chunking** | Par headers `##` Markdown | Respecte la structure logique des documents |
| **Interface** | Streamlit | Rapide à prototyper, gestion du state intégrée |
| **Format données** | Markdown → ChromaDB | Évite la perte de structure des PDFs |
