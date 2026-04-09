# Nova - Assistante RH pour NovaTech Solutions

Nova est une assistante RH specialisee construite pour le projet de Generative AI de l'ESIEA.

Elle repond aux questions des employes en combinant :

- les politiques RH internes de NovaTech
- des documents de droit du travail francais
- une architecture multi-agents
- un pipeline RAG avec ChromaDB
- un reranking optionnel par cross-encoder
- des outils RH pratiques : formulaires, checklist, contacts

L'application est exposee via une interface Streamlit.

---

## Objectif Du Projet

Les employes posent souvent les memes questions RH :

- teletravail
- conges
- arret maladie
- frais
- onboarding
- formation
- demission
- RQTH / handicap

L'objectif n'est pas de faire un chatbot generique, mais un assistant capable de :

- retrouver les bons passages documentaires
- separer politique interne et base legale
- produire une reponse finale propre
- proposer une aide pratique quand elle est utile

---

## Mises A Jour Importantes

La version actuelle du projet inclut ces corrections et ameliorations :

- le reranking est maintenant vraiment actif quand `USE_RERANKING=true`
- les tools renvoyes par `ActionAgent` sont normalises pour l'UI en `form`, `checklist` et `contact`
- `generate_checklist` produit maintenant des etapes pratiques generiques au lieu d'affirmer des regles RH non sourcees
- l'historique sauvegarde est tronque avant persistance, comme dans l'interface
- la langue de reponse suit maintenant le dernier message utilisateur
- les prompts distinguent plusieurs types de questions au lieu d'une logique binaire trop simple

---

## Architecture

```text
Question employe
    |
    v
OrchestratorAgent
    |
    +--> _route()
    |      Choisit quels agents lancer
    |
    +--> PolicyAgent
    |      RAG sur les documents internes NovaTech
    |
    +--> LegalAgent
    |      RAG sur les documents de droit du travail
    |
    +--> ActionAgent
    |      Selection de tools via LLM
    |      form / checklist / contact
    |
    +--> _synthesize()
           Fusionne les sorties en une reponse finale
```

### Pourquoi Une Architecture Multi-Agents ?

Chaque agent a un role clair :

- `PolicyAgent` repond depuis les documents internes
- `LegalAgent` repond depuis les documents legaux
- `ActionAgent` gere l'aide operationnelle
- `OrchestratorAgent` choisit les agents utiles et synthese le tout

Cette separation rend le systeme plus facile a :

- expliquer
- debugguer
- evaluer
- faire evoluer

---

## Logique De Routage

L'orchestrateur ne lance pas automatiquement exactement les memes agents a chaque question.

Strategie actuelle :

- `policy` est toujours inclus
- `legal` est ajoute pour les sujets RH reglementes ou les questions de droits
- `action` est ajoute quand l'utilisateur doit faire une vraie demarche, ou quand une petite aide pratique est pertinente

### Types De Questions

Les prompts distinguent 4 types de questions :

1. `informational`
   L'utilisateur demande une regle, un nombre de jours, une eligibilite ou une explication.

2. `informational_with_practical_follow_up`
   L'utilisateur veut surtout une reponse, mais une petite checklist optionnelle peut etre utile ensuite.

3. `procedural`
   L'utilisateur veut faire quelque chose concretement : declarer, demander, soumettre, lancer une procedure, remplir un formulaire.

4. `escalation`
   L'utilisateur veut savoir qui contacter ou comment faire remonter un cas.

### Exemples

- `How many telework days do I have as a manager?`
  En general : `policy + legal`, avec eventuellement une checklist legere en fin de reponse.

- `How do I declare my telework days?`
  En general : `policy + legal + action`.

- `Who should I contact for an unusual sick leave case?`
  En general : `policy + legal + action`.

- `What happens during onboarding at NovaTech?`
  En general : `policy`, parfois `action` si une checklist est utile.

---

## Pipeline RAG

### 1. Ingestion

Le projet utilise des documents Markdown comme source de verite pour le retrieval.

Le script d'ingestion :

- lit les fichiers Markdown
- decoupe les documents en chunks
- nettoie le bruit
- ajoute des metadonnees
- indexe le tout dans ChromaDB

Script principal :

- `Scripts/ingest.py`

### 2. Retrieval

Le retriever :

- encode la question utilisateur
- interroge ChromaDB
- filtre par source quand c'est necessaire (`novatech` ou `gouv`)
- applique un seuil de distance
- retourne les meilleurs chunks

Code principal :

- `src/rag.py`

### 3. Reranking

Le systeme peut appliquer une deuxieme passe apres le retrieval.

Fonctionnement :

- ChromaDB recupere d'abord un ensemble plus large de chunks proches
- un cross-encoder local relit la question et chaque chunk ensemble
- les chunks sont reordonnes par score de pertinence
- seuls les meilleurs sont conserves pour le LLM

Pourquoi c'est utile :

- moins de chunks "presque pertinents" mais mauvais
- meilleure precision sur des sujets RH proches
- meilleur contexte pour la reponse finale

Implementation :

- cross-encoder charge une seule fois dans `src/agents.py`
- retrieval dans `src/rag.py`
- controle par `USE_RERANKING`

---

## Prompting

Le projet utilise plusieurs couches de prompts, chacune avec un role precis.

### `prompts/prompts_llm.py`

Ce fichier contient :

- le `SYSTEM_PROMPT` principal
- les few-shot examples
- la logique de langue comme `infer_answer_language()`

Son role est de definir le comportement general de Nova :

- rester dans le scope RH
- repondre uniquement depuis le contexte recupere
- limiter les hallucinations
- ne pas inventer de chiffres, de delais, de contacts ou de formulaires
- suivre la langue de l'utilisateur

### `prompts/rag_prompt_template.py`

Ce fichier construit les messages effectivement envoyes aux agents RAG.

Il :

- injecte les chunks recuperes
- ajoute les few-shot examples
- impose explicitement la langue de la question courante
- assemble le message final envoye a Gemini

### `prompts/prompts_agents.py`

Ce fichier contient :

- `ROUTER_SYSTEM_PROMPT`
- `ACTION_AGENT_PROMPT`
- `SYNTHESIS_SYSTEM_PROMPT`

Leurs roles :

- choisir quels agents lancer
- choisir quels tools appeler
- fusionner policy, legal et action dans une seule reponse

### Pourquoi Plusieurs Prompts ?

Le projet n'utilise pas un seul prompt pour tout faire.

C'est volontaire :

- le prompt RAG sert a repondre depuis les documents
- le prompt routeur sert a choisir les agents
- le prompt action sert a choisir les outils
- le prompt de synthese sert a fusionner les sorties

Repondre depuis des chunks et fusionner plusieurs sorties d'agents sont deux taches differentes.

---

## Tool Use

La couche de tools se trouve dans `src/tools.py`.

Outils disponibles :

- `get_form_link(topic)`
- `generate_checklist(topic)`
- `route_to_contact(topic)`

### Comportement Actuel Des Tools

- `get_form_link` est reserve aux questions procedurales
- `generate_checklist` peut aussi etre utilise pour certaines questions informatives, mais seulement comme aide pratique optionnelle
- `route_to_contact` est reserve aux demandes de contact, aux blocages ou aux cas d'escalade

### Point Important Sur Les Checklists

`generate_checklist` n'est pas une source de verite legale ou RH.

La checklist sert seulement a :

- proposer des prochaines etapes pratiques
- guider l'utilisateur dans une demarche
- donner un complement operationnel a la reponse principale

La reponse de fond doit toujours venir de :

- `PolicyAgent`
- `LegalAgent`

### Contrat UI

Les tools sont normalises pour l'interface Streamlit en :

- `form`
- `checklist`
- `contact`

Cela evite un mismatch entre ce que renvoie l'agent et ce que sait afficher l'interface.

---

## Gestion De La Langue

L'application gere les questions en anglais et en francais.

Regle actuelle :

- la langue de la reponse doit suivre le dernier message utilisateur

Cette regle est renforcee :

- dans le builder de prompt RAG
- dans la synthese finale

Cela corrige le bug initial ou une question en anglais pouvait encore produire une reponse en francais a cause de l'historique precedent.

---

## Reconciliation Des Sources

Le projet ne suppose plus `NovaTech > loi`.

Logique actuelle :

- le droit du travail francais est le socle legal
- la politique NovaTech est une regle interne
- si NovaTech est explicitement plus favorable, la synthese peut le dire
- si la loi et la politique semblent en conflit, la reponse doit le signaler au lieu d'inventer une hierarchie

Cette logique est plus juste et plus defendable pour un assistant RH.

---

## Guide Fichier Par Fichier

### Racine

| Fichier | Role |
|---|---|
| `app.py` | Interface Streamlit du chat. Gere l'affichage, les messages, les tools, les sources et les conversations. |
| `requirements.txt` | Liste des dependances Python. |
| `.env.example` | Exemple de configuration locale. |
| `test_rag.py` | Petit point d'entree de debug pour tester une question hors UI. |
| `README.md` | Documentation du projet. |

### `src/`

| Fichier | Role |
|---|---|
| `src/config.py` | Charge les variables d'environnement et centralise les parametres du projet. |
| `src/llm.py` | Encapsule les appels Gemini avec retry et backoff. |
| `src/rag.py` | Contient le retriever ChromaDB et l'utilitaire d'extraction JSON. |
| `src/agents.py` | Coeur de l'architecture multi-agents : routing, agents RAG, action agent, reranking, synthese. |
| `src/tools.py` | Formulaires, checklist, routage vers les contacts, matching par topic et execution des tool calls. |
| `src/cache.py` | Persistance des conversations pour l'application Streamlit. |
| `src/__init__.py` | Marqueur de package Python. |

### `prompts/`

| Fichier | Role |
|---|---|
| `prompts/prompts_llm.py` | Prompt systeme principal, few-shot examples, helper de langue. |
| `prompts/rag_prompt_template.py` | Builder runtime des messages RAG envoyes a Gemini. |
| `prompts/prompts_agents.py` | Prompts du routeur, de l'action agent et de la synthese. |
| `prompts/prompt_generate_corpus.py` | Prompts utilises pour generer le corpus NovaTech. |
| `prompts/__init__.py` | Marqueur de package Python. |

### `Scripts/`

| Fichier | Role |
|---|---|
| `Scripts/Scrapping.py` | Scraping et conversion de contenus RH / droit du travail. |
| `Scripts/generate_corpus.py` | Generation des documents internes NovaTech. |
| `Scripts/ingest.py` | Creation de la base vectorielle depuis le corpus Markdown. |
| `Scripts/md_to_pdf.py` | Conversion Markdown vers PDF. |
| `Scripts/__init__.py` | Marqueur de package Python. |

### `eval/`

| Fichier | Role |
|---|---|
| `eval/evaluate.py` | Lance l'evaluation automatique. |
| `eval/test_cases.json` | Definit les cas de test. |
| `eval/eval_results.json` | Stocke le dernier resultat d'evaluation. |
| `eval/__init__.py` | Marqueur de package Python. |

### Donnees Et Cache

| Chemin | Role |
|---|---|
| `data/gouv_md/` | Documents Markdown de droit du travail utilises par `LegalAgent`. |
| `data/novatech_md/` | Documents Markdown internes utilises par `PolicyAgent`. |
| `data/chroma_db/` | Base vectorielle ChromaDB persistante. |
| `cache/chat_cache/conversations.json` | Conversations sauvegardees de Streamlit. |

---

## Vue D'Ensemble Du Corpus

Le projet utilise deux couches documentaires.

### 1. Couche Publique / Legale

Documents RH / droit du travail couvrant notamment :

- conges payes
- conges pour evenements familiaux
- teletravail
- arret maladie
- accident du travail
- demission
- rupture conventionnelle
- licenciement
- CPF
- RQTH / handicap

### 2. Couche Interne NovaTech

Documents internes couvrant notamment :

- conges
- RTT
- teletravail
- arret maladie
- demission
- frais
- onboarding
- mutuelle / avantages
- formation et carriere
- entretiens et remuneration
- FAQ RH
- depart / offboarding

Cette structure permet de comparer :

- la regle interne
- le socle legal

quand le sujet le demande.

---

## Evaluation

La suite d'evaluation se trouve dans `eval/`.

Elle contient des cas pour :

- teletravail
- conges
- RTT
- frais
- arret maladie
- formation
- depart
- handicap
- hors perimetre
- prompt injection
- cas croises

L'objectif est de tester :

- la pertinence des reponses
- les sources recuperees
- le bon comportement de refus
- la resistance aux tentatives d'injection

Commande :

```bash
python eval/evaluate.py
```

---

## Installation

### Prerequis

- Python 3.11+
- une cle API Gemini

### 1. Creer un environnement virtuel

```bash
python -m venv .venv
```

### 2. L'activer

Sous PowerShell :

```bash
.venv\Scripts\Activate.ps1
```

### 3. Installer les dependances

```bash
pip install -r requirements.txt
```

### 4. Configurer le `.env`

Variables principales :

```env
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash-lite
EMBEDDING_MODEL=all-mpnet-base-v2
USE_RERANKING=true
RERANKING_MODEL=cross-encoder/mmarco-mMiniLMv2-L12-H384-v1
CHROMA_PERSIST_DIR=data/chroma_db
CHROMA_COLLECTION_NAME=hr_docs
CHUNK_SIZE=800
CHUNK_OVERLAP=200
TOP_K=10
DISTANCE_THRESHOLD=1.5
```

### 5. Construire La Base Vectorielle

```bash
python Scripts/ingest.py
```

### 6. Lancer L'Application

```bash
streamlit run app.py
```

---

## Choix Techniques

| Composant | Choix | Pourquoi |
|---|---|---|
| LLM | Gemini 2.5 Flash Lite | Rapide et pratique pour un prototype etudiant |
| Vector store | ChromaDB | Local et simple a persister |
| Embeddings | SentenceTransformers | Pipeline local pour les embeddings |
| Reranking | cross-encoder local | Ameliore la precision sans appel API supplementaire |
| UI | Streamlit | Rapide a prototyper et simple a demontrer |
| Architecture | multi-agents | Separation claire des sources et de la synthese |
| Tool selection | LLM + garde-fous code | Plus souple qu'une logique purement keywords |

---

## Etat Actuel Du Projet

Le projet dispose maintenant :

- d'une architecture multi-agents fonctionnelle
- d'un vrai routing entre policy, legal et action
- d'un reranking effectivement branche
- d'une meilleure separation des prompts
- de checklists plus sures
- d'une meilleure gestion de la langue
- d'un affichage UI coherent pour les tools
- d'une persistance d'historique alignee avec la session visible

En bref : le projet est maintenant beaucoup plus propre, plus defendable a l'oral, et plus coherent avec l'architecture que tu voulais presenter.
