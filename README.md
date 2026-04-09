# Nova — Assistante RH NovaTech Solutions

Assistant RH intelligent basé sur une architecture **multi-agents RAG** pour répondre aux questions des employés de NovaTech Solutions sur les politiques RH internes et le droit du travail français.

---

## Mises à jour récentes

- Le **reranking cross-encoder** est maintenant bien activé quand `USE_RERANKING=true`.
- Les tools retournés par l'`ActionAgent` sont normalisés pour l'UI Streamlit en `form`, `checklist` et `contact`.
- `generate_checklist` produit désormais des **étapes pratiques génériques** et non des règles RH affirmées sans source.

---

## Contexte du projet

Projet final du cours **Generative AI** (ESIEA, Master). L'objectif est de construire un assistant IA spécialisé pour un domaine métier précis, avec un prototype fonctionnel incluant interface web, RAG, architecture multi-agents, prompt engineering avancé et tool use piloté par LLM.

### Problème résolu

Les employés posent sans cesse les mêmes questions RH (congés, télétravail, arrêts maladie, frais, etc.), ce qui mobilise inutilement les équipes RH sur des demandes répétitives. Nova répond automatiquement en s'appuyant uniquement sur les documents officiels — sans inventer.

---

## Architecture multi-agents

```
Question employé
       │
       ▼
OrchestratorAgent
       │
       ├─ _route() ──► routeur LLM : `policy` toujours, `legal` pour les sujets réglementés, `action` si une démarche concrète est utile
       │
       ├──► PolicyAgent   →  RAG sur docs NovaTech internes  →  réponse partielle
       ├──► LegalAgent    →  RAG sur docs droit du travail   →  réponse partielle
       └──► ActionAgent   →  LLM sélectionne les outils HR  →  formulaires / checklist / contact
                │
                ▼
         _synthesize() ──► LLM fusionne tout en une réponse finale
                │
                ▼
       Réponse structurée + sources
```

### Les 4 agents

| Agent | Rôle | Source de données |
|---|---|---|
| **OrchestratorAgent** | Route la question, lance les agents, synthétise | — |
| **PolicyAgent** | Répond sur les règles internes NovaTech | `data/novatech_md/` |
| **LegalAgent** | Répond sur le droit du travail français | `data/gouv_md/` |
| **ActionAgent** | Sélectionne et exécute les outils RH via LLM | `src/tools.py` |

**Pourquoi multi-agents ?**
- Les sources sont séparées (NovaTech vs Gouv) → chaque agent cherche dans son corpus
- Le routage est adapté au cas RH : `policy` est systématique, `legal` est activé par défaut sur les thèmes réglementaires, et `action` n'est ajouté que lorsqu'une démarche concrète est utile
- La synthèse confronte politique interne et droit du travail : la loi reste le socle, NovaTech n'est retenue que si la règle interne est explicitement plus favorable ou plus précise
- L'`ActionAgent` comprend l'intention via LLM, plus de détection par mots-clés fragile
- Extensible : ajouter un agent = une classe, sans toucher au reste

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
│   ├── agents.py                 ← Architecture multi-agents (Orchestrator, Policy, Legal, Action)
│   ├── rag.py                    ← Retriever ChromaDB + reranker cross-encoder
│   ├── llm.py                    ← Appel Gemini avec retry/backoff
│   ├── tools.py                  ← Outils RH : formulaires, checklists, contacts
│   └── cache.py                  ← Persistance des conversations (JSON)
│
├── prompts/
│   ├── prompts_llm.py            ← Système prompt Nova, few-shot, RAG prompt builder
│   └── prompts_agents.py         ← Prompts routing, synthesis, action agent
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

## Guide fichier par fichier

### Racine du projet

| Fichier | Rôle concret |
|---|---|
| `README.md` | Document principal du projet : architecture, pipeline RAG, prompts, outils, installation, évaluation. |
| `app.py` | Point d'entrée Streamlit. Gère l'interface du chat, la session, l'affichage des sources/tools et la persistance des conversations. |
| `requirements.txt` | Liste des dépendances Python nécessaires au projet. |
| `.env.example` | Exemple de configuration locale : clés API, modèles, chemins Chroma, paramètres de chunking et reranking. |
| `.env` | Configuration locale réelle utilisée à l'exécution. Non versionnée, elle contient notamment la clé Gemini et les variables d'environnement du projet. |
| `.gitignore` | Empêche de versionner les fichiers locaux ou générés automatiquement (`.venv`, cache, artefacts temporaires, etc.). |
| `test_rag.py` | Petit script manuel de debug pour lancer une question de test et inspecter les agents utilisés, les chunks récupérés et les scores de reranking. |

### Dossier `src/`

| Fichier | Rôle concret |
|---|---|
| `src/__init__.py` | Marqueur de package Python. Permet d'importer `src.*` proprement. |
| `src/config.py` | Centralise toute la configuration : chargement `.env`, chemins des données, modèles, paramètres RAG, retry/backoff et utilitaire `is_retryable_error()`. |
| `src/llm.py` | Encapsule l'appel Gemini : conversion des messages au format API, gestion des retries, backoff exponentiel et retour texte. |
| `src/rag.py` | Contient le retriever ChromaDB et l'utilitaire d'extraction JSON. Fait la recherche vectorielle, applique les filtres de source et retourne les chunks. |
| `src/tools.py` | Regroupe les outils “action” : formulaires internes, checklists pratiques génériques, routage vers les contacts RH, mots-clés et exécution des tool calls. |
| `src/agents.py` | Cœur de l'architecture multi-agents : `PolicyAgent`, `LegalAgent`, `ActionAgent`, `OrchestratorAgent`, routage, reranking partagé et synthèse finale. |
| `src/cache.py` | Gère la persistance JSON des conversations : chargement, création, suppression, renommage automatique par premier message utilisateur. |

### Dossier `prompts/`

| Fichier | Rôle concret |
|---|---|
| `prompts/__init__.py` | Marqueur de package Python pour les prompts. |
| `prompts/prompts_llm.py` | Prompt système principal “Nova”, few-shot examples, construction du prompt RAG et assemblage final des messages envoyés aux agents RAG. |
| `prompts/prompts_agents.py` | Prompts spécialisés pour le routage (`router`), la synthèse (`synthesis`) et la sélection d'outils (`action`). |
| `prompts/prompt_generate_corpus.py` | Définit les prompts de génération du corpus NovaTech et la liste des 18 thèmes métier utilisés par `Scripts/generate_corpus.py`. |
| `prompts/rag_prompt_template.py` | Version utilitaire/factorisée du builder de prompt RAG ; proche de `prompts_llm.py`, utile pour isoler la logique de templating. |

### Dossier `Scripts/`

| Fichier | Rôle concret |
|---|---|
| `Scripts/__init__.py` | Marqueur de package Python pour les scripts. |
| `Scripts/Scrapping.py` | Scrape les pages service-public.fr, nettoie le bruit, suit certains liens, puis exporte les contenus en Markdown structuré et en PDF. |
| `Scripts/generate_corpus.py` | Génère les politiques internes NovaTech avec Gemini, thème par thème et article par article, en s'appuyant si besoin sur un contexte légal gouv. |
| `Scripts/ingest.py` | Transforme les fichiers Markdown en chunks, nettoie les textes, calcule les métadonnées et indexe l'ensemble dans ChromaDB. |
| `Scripts/md_to_pdf.py` | Convertisseur simple Markdown → PDF utilisé surtout après la génération des documents NovaTech. |

### Dossier `eval/`

| Fichier | Rôle concret |
|---|---|
| `eval/__init__.py` | Marqueur de package Python pour les scripts d'évaluation. |
| `eval/evaluate.py` | Lance les cas de test, exécute l'orchestrateur, vérifie la réponse, les sources, les refus et la résistance aux injections. |
| `eval/test_cases.json` | Jeu de cas de test utilisé par `evaluate.py` : questions, catégories, mots-clés attendus, source attendue, flags injection/hors périmètre. |
| `eval/eval_results.json` | Dernier rapport d'évaluation généré automatiquement : résumé global, résultats par catégorie et détail de chaque cas. |

### Cache et base vectorielle

| Fichier / famille | Rôle concret |
|---|---|
| `cache/chat_cache/conversations.json` | Historique persistant des conversations Streamlit. Chaque entrée stocke id, titre, messages et `chat_history` tronqué. |
| `data/__init__.py` | Marqueur de package Python pour le dossier de données. |
| `data/chroma_db/chroma.sqlite3` | Métadonnées principales de la base vectorielle Chroma persistée localement. |
| `data/chroma_db/<uuid>/header.bin` | Métadonnées bas niveau d'un index HNSW stocké par Chroma. |
| `data/chroma_db/<uuid>/data_level0.bin` | Données vectorielles/indexées pour le niveau de base de l'index HNSW. |
| `data/chroma_db/<uuid>/length.bin` | Informations de taille/longueur associées à l'index binaire. |
| `data/chroma_db/<uuid>/link_lists.bin` | Liens de voisinage utilisés par l'index HNSW pour la recherche de plus proches voisins. |

### Corpus `data/gouv/` et `data/gouv_md/`

Chaque thème gouv existe en général en **deux formats** :
- `data/gouv/*.pdf` pour la consultation humaine
- `data/gouv_md/*.md` pour l'ingestion RAG structurée

| Fichiers | Thème |
|---|---|
| `data/gouv/gouv_01_conges_payes.pdf` + `data/gouv_md/gouv_01_conges_payes.md` | Congés payés |
| `data/gouv/gouv_02_conges_evenements_familiaux.pdf` + `data/gouv_md/gouv_02_conges_evenements_familiaux.md` | Congés pour événements familiaux |
| `data/gouv/gouv_03_teletravail.pdf` + `data/gouv_md/gouv_03_teletravail.md` | Télétravail dans le secteur privé |
| `data/gouv/gouv_04_arret_maladie.pdf` + `data/gouv_md/gouv_04_arret_maladie.md` | Arrêt maladie |
| `data/gouv/gouv_05_accident_travail.pdf` + `data/gouv_md/gouv_05_accident_travail.md` | Accident du travail |
| `data/gouv/gouv_06_demission.pdf` + `data/gouv_md/gouv_06_demission.md` | Démission |
| `data/gouv/gouv_07_rupture_conventionnelle.pdf` + `data/gouv_md/gouv_07_rupture_conventionnelle.md` | Rupture conventionnelle |
| `data/gouv/gouv_08_licenciement.pdf` + `data/gouv_md/gouv_08_licenciement.md` | Licenciement |
| `data/gouv/gouv_09_cpf.pdf` + `data/gouv_md/gouv_09_cpf.md` | CPF |
| `data/gouv/gouv_10_rqth.pdf` + `data/gouv_md/gouv_10_rqth.md` | RQTH / handicap |

### Corpus `data/novatech/` et `data/novatech_md/`

Les documents internes NovaTech sont générés en Markdown dans `data/novatech_md/`. Une partie d'entre eux existe aussi en PDF dans `data/novatech/` pour la démonstration ou la consultation humaine.

| Fichiers | Thème |
|---|---|
| `data/novatech_md/01_conges_payes.md` + `data/novatech/01_conges_payes.pdf` | Politique interne sur les congés payés |
| `data/novatech_md/02_conges_evenements_familiaux.md` + `data/novatech/02_conges_evenements_familiaux.pdf` | Congés événements familiaux |
| `data/novatech_md/03_teletravail.md` + `data/novatech/03_teletravail.pdf` | Politique télétravail |
| `data/novatech_md/04_arret_maladie.md` + `data/novatech/04_arret_maladie.pdf` | Politique arrêt maladie |
| `data/novatech_md/05_accident_travail.md` | Politique accident du travail |
| `data/novatech_md/06_demission.md` + `data/novatech/06_demission.pdf` | Politique démission |
| `data/novatech_md/07_rupture_conventionnelle.md` + `data/novatech/07_rupture_conventionnelle.pdf` | Rupture conventionnelle |
| `data/novatech_md/08_licenciement.md` + `data/novatech/08_licenciement.pdf` | Politique licenciement |
| `data/novatech_md/09_cpf.md` | CPF côté NovaTech |
| `data/novatech_md/10_rqth_handicap.md` | RQTH, handicap et aménagements |
| `data/novatech_md/11_rtt.md` + `data/novatech/11_rtt.pdf` | RTT |
| `data/novatech_md/12_frais_deplacements.md` + `data/novatech/12_frais_deplacements.pdf` | Frais et déplacements professionnels |
| `data/novatech_md/13_onboarding.md` + `data/novatech/13_onboarding.pdf` | Onboarding et intégration |
| `data/novatech_md/14_mutuelle_avantages.md` | Mutuelle et avantages sociaux |
| `data/novatech_md/15_formation_carriere.md` + `data/novatech/15_formation_carriere.pdf` | Formation continue et évolution de carrière |
| `data/novatech_md/16_entretiens_remuneration.md` + `data/novatech/16_entretiens_remuneration.pdf` | Entretiens, objectifs et rémunération |
| `data/novatech_md/17_faq_rh.md` + `data/novatech/17_faq_rh.pdf` | FAQ RH |
| `data/novatech_md/18_depart_entreprise.md` + `data/novatech/18_depart_entreprise.pdf` | Départ de l'entreprise / offboarding |

---

## Corpus documentaire

### Couche 1 — Droit du travail français (service-public.fr)

10 documents scrappés et nettoyés :

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
  - `chunk_by_size` : l'overlap repart depuis la dernière frontière de phrase
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
- Filtre par source (`gouv` ou `novatech`) utilisé par `PolicyAgent` et `LegalAgent`

### 3. Reranking (`src/rag.py` + `src/agents.py`)

Le reranking ajoute une **deuxième passe de sélection** après la recherche vectorielle classique.

- **Étape 1 : retrieval large**
  - ChromaDB récupère d'abord `top_k * 2` chunks proches de la question grâce aux embeddings.
  - Cette étape est rapide, mais elle peut ramener des chunks globalement proches sans être les plus précis pour la question exacte.

- **Étape 2 : reranking fin**
  - Un **cross-encoder local** (`cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`) réévalue chaque paire `(question, chunk)`.
  - Contrairement à l'embedding search, il lit la question et le chunk **ensemble**, ce qui donne un score de pertinence plus précis.
  - Les chunks sont ensuite retriés par `rerank_score`, puis on garde les `top_k` meilleurs.

- **Pourquoi c'est utile**
  - Réduit les faux positifs sémantiques : un chunk vaguement proche peut être rétrogradé.
  - Aide à mieux distinguer des cas RH proches mais différents (cadre/non-cadre, télétravail/RTT, arrêt maladie/accident du travail, etc.).
  - Améliore la qualité du contexte envoyé au LLM, donc la précision de la réponse finale.

- **Implémentation dans ce projet**
  - Le modèle est chargé une seule fois en lazy init dans l'orchestrateur.
  - Il est partagé par `PolicyAgent` et `LegalAgent`.
  - Il s'exécute réellement quand `use_reranking=True` / `USE_RERANKING=true`.
  - Il est local, sans appel API supplémentaire, et optimisé pour le français / multilingue.

---

## Prompt Engineering (`prompts/`)

### Système prompt — Nova (`prompts/prompts_llm.py`)

- **Persona** : Nova, assistante RH NovaTech Solutions, chaleureuse et professionnelle
- **Langue de réponse** : est déduite à partir du message courant de l'employé puis réinjectée explicitement dans les prompts RAG et de synthèse
- **Périmètre strict** : refuse les questions hors RH, redirige vers le bon contact
- **Réconciliation des sources** : le droit du travail français est traité comme socle ; une règle NovaTech n'est mise en avant que si elle est explicitement plus favorable ou plus précise dans le contexte disponible
- **Sécurité factuelle** : ne cite jamais un chiffre, délai ou droit absent du contexte
- **Anti-hallucination** : reconnaît explicitement quand l'information est absente
- **Anti-injection** : ignore les tentatives de changement de rôle, ne révèle jamais ses instructions
- **Adaptation profil** : applique la règle cadre ou non-cadre selon le profil donné, présente les deux cas si inconnu

### Prompts agents (`prompts/prompts_agents.py`)

| Prompt | Utilisé par | Rôle |
|---|---|---|
| `ROUTER_SYSTEM_PROMPT` | OrchestratorAgent | Décide quels agents invoquer selon la logique du projet : `policy` toujours, `legal` pour les sujets RH réglementés, `action` seulement si une démarche concrète est utile |
| `SYNTHESIS_SYSTEM_PROMPT` | OrchestratorAgent | Fusionne les réponses des agents en une réponse finale |
| `ACTION_AGENT_PROMPT` | ActionAgent | Choisit les outils RH à appeler → JSON `{"tool_calls": [...]}` |

Logique de routage actuelle :
- `policy` est systématique
- `legal` est activé par défaut sur les thèmes réglementaires (télétravail, congés, arrêt maladie, démission, CPF, RQTH, etc.)
- `action` n'est appelé que si la question implique une démarche concrète (formulaire, procédure, contact)

### Few-shot examples

3 exemples couvrant :
- Télétravail cadre (question en **anglais** → réponse en **anglais**)
- Congé deuil (question en **français** → réponse en **français**)
- Hors périmètre — droit de grève (refus poli + redirection contact)

---

## Tool Use (`src/tools.py`)

3 outils disponibles, sélectionnés et invoqués par l'`ActionAgent` via LLM :

| Outil | Rôle | Exemple |
|---|---|---|
| `get_form_link` | Retourne le chemin MonEspace vers le bon formulaire | `MonEspace > Mes congés > Nouvelle demande` |
| `generate_checklist` | Génère des étapes pratiques génériques pour aider l'utilisateur à agir | Ouvrir le bon formulaire, préparer les justificatifs, contacter RH si besoin |
| `route_to_contact` | Identifie le bon contact RH selon le sujet | Sophie Martin pour l'administration du personnel |

Le LLM comprend l'intention de l'employé et choisit les bons outils avec les bons arguments — sans correspondance de mots-clés fragile. Exemple pour *"Je veux bosser de chez moi"* :
```json
{"tool_calls": [
  {"tool": "get_form_link",      "arguments": {"topic": "telework"}},
  {"tool": "generate_checklist", "arguments": {"topic": "telework"}}
]}
```

### Contrat UI des tools

Les tools retournés par l'`ActionAgent` sont normalisés en 3 types compatibles avec l'interface :

- `form`
- `checklist`
- `contact`

Cela permet un affichage direct dans Streamlit sans conversion supplémentaire côté UI.

### Important sur les checklists

`generate_checklist` ne doit pas être interprété comme une source de vérité RH ou juridique.

- La réponse de fond doit venir des documents RAG (`PolicyAgent` / `LegalAgent`)
- La checklist sert seulement à proposer des **prochaines actions pratiques**
- Elle évite volontairement d'affirmer en dur des délais, préavis, droits ou obligations non sourcés

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
- Client instancié **une seule fois** au chargement du module
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
| **Architecture** | Multi-agents (Orchestrator / Policy / Legal / Action) | Séparation des sources, synthèse explicite, extensible |
| **LLM** | Gemini 2.5 Flash Lite | Rapide, gratuit en tier développeur, bon en français |
| **Embedding** | `paraphrase-multilingual-mpnet-base-v2` | Local, gratuit, optimisé français/multilingue |
| **Reranking** | Cross-encoder `mmarco-mMiniLMv2` | Local, 0 appel API, plus précis qu'un LLM scoring |
| **Vector store** | ChromaDB | Local, persistant, simple à déployer |
| **Tool selection** | LLM-driven (ActionAgent) | Comprend l'intention, pas de keywords fragiles |
| **Chunking** | Par headers `##` Markdown | Respecte la structure logique des documents |
| **Interface** | Streamlit | Rapide à prototyper, gestion du state intégrée |
| **Format données** | Markdown → ChromaDB | Évite la perte de structure des PDFs |
