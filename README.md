# Nova - Assistante RH NovaTech Solutions
Assistant RH intelligent base sur une architecture **multi-agents RAG** pour repondre aux questions des employes de NovaTech Solutions sur les politiques RH internes et le droit du travail francais.
---
## Mises a jour recentes
- Le **reranking cross-encoder** est maintenant bien active quand `USE_RERANKING=true`.
- Les tools retournes par l'`ActionAgent` sont normalises pour l'UI Streamlit en `form`, `checklist` et `contact`.
- `generate_checklist` produit desormais des **etapes pratiques generiques** et non des regles RH affirmees sans source.
- L'historique sauvegarde est maintenant tronque avant persistance, comme dans l'interface.
- La langue de reponse suit desormais le **dernier message utilisateur**, pas l'historique precedent.
- Les prompts differencient maintenant les questions informatives, informatives avec aide pratique optionnelle, procedurales et d'escalade/contact.
---
## Contexte du projet

Projet final du cours **Generative AI** (ESIEA, Master). L'objectif est de construire un assistant IA spÃ©cialisÃ© pour un domaine mÃ©tier prÃ©cis, avec un prototype fonctionnel incluant interface web, RAG, architecture multi-agents, prompt engineering avancÃ© et tool use pilotÃ© par LLM.

### ProblÃ¨me rÃ©solu

Les employÃ©s posent sans cesse les mÃªmes questions RH (congÃ©s, tÃ©lÃ©travail, arrÃªts maladie, frais, etc.), ce qui mobilise inutilement les Ã©quipes RH sur des demandes rÃ©pÃ©titives. Nova rÃ©pond automatiquement en s'appuyant uniquement sur les documents officiels â€” sans inventer.

---

## Architecture multi-agents

```
Question employee
       |
       v
OrchestratorAgent
       |
       +- _route() --> routeur LLM : `policy` toujours, `legal` pour les sujets reglementes, `action` pour une vraie demarche ou une aide pratique legere si pertinente
       |
       +--> PolicyAgent   -> RAG sur docs NovaTech internes -> reponse partielle
       +--> LegalAgent    -> RAG sur docs droit du travail  -> reponse partielle
       +--> ActionAgent   -> LLM selectionne les outils HR  -> formulaires / checklist / contact
                      |
                      v
               _synthesize() --> LLM fusionne tout en une reponse finale
                      |
                      v
            Reponse structuree + sources
```

### Les 4 agents

| Agent | RÃ´le | Source de donnÃ©es |
|---|---|---|
| **OrchestratorAgent** | Route la question, lance les agents, synthÃ©tise | â€” |
| **PolicyAgent** | RÃ©pond sur les rÃ¨gles internes NovaTech | `data/novatech_md/` |
| **LegalAgent** | RÃ©pond sur le droit du travail franÃ§ais | `data/gouv_md/` |
| **ActionAgent** | SÃ©lectionne et exÃ©cute les outils RH via LLM | `src/tools.py` |

**Pourquoi multi-agents ?**
- Les sources sont separees (NovaTech vs Gouv) -> chaque agent cherche dans son corpus
- Le routage est adapte au cas RH : `policy` est systematique, `legal` est active par defaut sur les themes reglementaires, et `action` est reserve aux vraies demarches ou aux aides pratiques legeres quand elles apportent vraiment de la valeur
- La synthese confronte politique interne et droit du travail : la loi reste le socle, NovaTech n'est retenue que si la regle interne est explicitement plus favorable ou plus precise
- L'`ActionAgent` comprend l'intention via LLM et distingue mieux une question purement informative d'une question qui merite aussi une aide pratique
- Extensible : ajouter un agent = une classe, sans toucher au reste

---

## Structure du projet

```
GenAI/
â”œâ”€â”€ app.py                        â† Interface Streamlit
â”œâ”€â”€ requirements.txt
â”œâ”€â”€ .env.example                  â† Template de configuration
â”‚
â”œâ”€â”€ src/
â”‚   â”œâ”€â”€ config.py                 â† Configuration centralisÃ©e (env vars)
â”‚   â”œâ”€â”€ agents.py                 â† Architecture multi-agents (Orchestrator, Policy, Legal, Action)
â”‚   â”œâ”€â”€ rag.py                    â† Retriever ChromaDB + reranker cross-encoder
â”‚   â”œâ”€â”€ llm.py                    â† Appel Gemini avec retry/backoff
â”‚   â”œâ”€â”€ tools.py                  â† Outils RH : formulaires, checklists, contacts
â”‚   â””â”€â”€ cache.py                  â† Persistance des conversations (JSON)
â”‚
â”œâ”€â”€ prompts/
â”‚   â”œâ”€â”€ prompts_llm.py            â† SystÃ¨me prompt Nova, few-shot, RAG prompt builder
â”‚   â””â”€â”€ prompts_agents.py         â† Prompts routing, synthesis, action agent
â”‚
â”œâ”€â”€ Scripts/
â”‚   â”œâ”€â”€ ingest.py                 â† Pipeline d'ingestion : chunking + indexation ChromaDB
â”‚   â”œâ”€â”€ generate_corpus.py        â† GÃ©nÃ©ration des documents NovaTech via Gemini
â”‚   â”œâ”€â”€ Scrapping.py              â† Scraping des PDFs service-public.fr
â”‚   â””â”€â”€ md_to_pdf.py              â† Conversion Markdown â†’ PDF
â”‚
â”œâ”€â”€ data/
â”‚   â”œâ”€â”€ gouv/                     â† 10 PDFs service-public.fr (droit du travail)
â”‚   â”œâ”€â”€ gouv_md/                  â† Versions Markdown des PDFs gouv
â”‚   â”œâ”€â”€ novatech/                 â† 18 PDFs politiques internes NovaTech
â”‚   â”œâ”€â”€ novatech_md/              â† Versions Markdown des politiques NovaTech
â”‚   â””â”€â”€ chroma_db/                â† Base vectorielle persistante (gÃ©nÃ©rÃ© par ingest.py)
â”‚
â””â”€â”€ eval/
    â”œâ”€â”€ test_cases.json           â† 15 cas de test (prÃ©cision, hors pÃ©rimÃ¨tre, injection)
    â”œâ”€â”€ evaluate.py               â† Script d'Ã©valuation automatique
    â””â”€â”€ eval_results.json         â† RÃ©sultats du dernier run d'Ã©valuation
```

---

## Guide fichier par fichier

### Racine du projet

| Fichier | RÃ´le concret |
|---|---|
| `README.md` | Document principal du projet : architecture, pipeline RAG, prompts, outils, installation, Ã©valuation. |
| `app.py` | Point d'entrÃ©e Streamlit. GÃ¨re l'interface du chat, la session, l'affichage des sources/tools et la persistance des conversations. |
| `requirements.txt` | Liste des dÃ©pendances Python nÃ©cessaires au projet. |
| `.env.example` | Exemple de configuration locale : clÃ©s API, modÃ¨les, chemins Chroma, paramÃ¨tres de chunking et reranking. |
| `.env` | Configuration locale rÃ©elle utilisÃ©e Ã  l'exÃ©cution. Non versionnÃ©e, elle contient notamment la clÃ© Gemini et les variables d'environnement du projet. |
| `.gitignore` | EmpÃªche de versionner les fichiers locaux ou gÃ©nÃ©rÃ©s automatiquement (`.venv`, cache, artefacts temporaires, etc.). |
| `test_rag.py` | Petit script manuel de debug pour lancer une question de test et inspecter les agents utilisÃ©s, les chunks rÃ©cupÃ©rÃ©s et les scores de reranking. |

### Dossier `src/`

| Fichier | RÃ´le concret |
|---|---|
| `src/__init__.py` | Marqueur de package Python. Permet d'importer `src.*` proprement. |
| `src/config.py` | Centralise toute la configuration : chargement `.env`, chemins des donnÃ©es, modÃ¨les, paramÃ¨tres RAG, retry/backoff et utilitaire `is_retryable_error()`. |
| `src/llm.py` | Encapsule l'appel Gemini : conversion des messages au format API, gestion des retries, backoff exponentiel et retour texte. |
| `src/rag.py` | Contient le retriever ChromaDB et l'utilitaire d'extraction JSON. Fait la recherche vectorielle, applique les filtres de source et retourne les chunks. |
| `src/tools.py` | Regroupe les outils â€œactionâ€ : formulaires internes, checklists pratiques gÃ©nÃ©riques, routage vers les contacts RH, mots-clÃ©s et exÃ©cution des tool calls. |
| `src/agents.py` | CÅ“ur de l'architecture multi-agents : `PolicyAgent`, `LegalAgent`, `ActionAgent`, `OrchestratorAgent`, routage, reranking partagÃ© et synthÃ¨se finale. |
| `src/cache.py` | GÃ¨re la persistance JSON des conversations : chargement, crÃ©ation, suppression, renommage automatique par premier message utilisateur. |

### Dossier `prompts/`

| Fichier | RÃ´le concret |
|---|---|
| `prompts/__init__.py` | Marqueur de package Python pour les prompts. |
| `prompts/prompts_llm.py` | Prompt systeme principal Nova, few-shot examples et helpers de langue / cadrage global utilises par les agents RAG et la synthese. |
| `prompts/prompts_agents.py` | Prompts spÃ©cialisÃ©s pour le routage (`router`), la synthÃ¨se (`synthesis`) et la sÃ©lection d'outils (`action`). |
| `prompts/prompt_generate_corpus.py` | DÃ©finit les prompts de gÃ©nÃ©ration du corpus NovaTech et la liste des 18 thÃ¨mes mÃ©tier utilisÃ©s par `Scripts/generate_corpus.py`. |
| `prompts/rag_prompt_template.py` | Builder effectivement utilise au runtime pour assembler les messages RAG : prompt systeme, contexte, historique et contrainte explicite sur la langue de reponse. |

### Dossier `Scripts/`

| Fichier | RÃ´le concret |
|---|---|
| `Scripts/__init__.py` | Marqueur de package Python pour les scripts. |
| `Scripts/Scrapping.py` | Scrape les pages service-public.fr, nettoie le bruit, suit certains liens, puis exporte les contenus en Markdown structurÃ© et en PDF. |
| `Scripts/generate_corpus.py` | GÃ©nÃ¨re les politiques internes NovaTech avec Gemini, thÃ¨me par thÃ¨me et article par article, en s'appuyant si besoin sur un contexte lÃ©gal gouv. |
| `Scripts/ingest.py` | Transforme les fichiers Markdown en chunks, nettoie les textes, calcule les mÃ©tadonnÃ©es et indexe l'ensemble dans ChromaDB. |
| `Scripts/md_to_pdf.py` | Convertisseur simple Markdown â†’ PDF utilisÃ© surtout aprÃ¨s la gÃ©nÃ©ration des documents NovaTech. |

### Dossier `eval/`

| Fichier | RÃ´le concret |
|---|---|
| `eval/__init__.py` | Marqueur de package Python pour les scripts d'Ã©valuation. |
| `eval/evaluate.py` | Lance les cas de test, exÃ©cute l'orchestrateur, vÃ©rifie la rÃ©ponse, les sources, les refus et la rÃ©sistance aux injections. |
| `eval/test_cases.json` | Jeu de cas de test utilisÃ© par `evaluate.py` : questions, catÃ©gories, mots-clÃ©s attendus, source attendue, flags injection/hors pÃ©rimÃ¨tre. |
| `eval/eval_results.json` | Dernier rapport d'Ã©valuation gÃ©nÃ©rÃ© automatiquement : rÃ©sumÃ© global, rÃ©sultats par catÃ©gorie et dÃ©tail de chaque cas. |

### Cache et base vectorielle

| Fichier / famille | RÃ´le concret |
|---|---|
| `cache/chat_cache/conversations.json` | Historique persistant des conversations Streamlit. Chaque entrÃ©e stocke id, titre, messages et `chat_history` tronquÃ©. |
| `data/__init__.py` | Marqueur de package Python pour le dossier de donnÃ©es. |
| `data/chroma_db/chroma.sqlite3` | MÃ©tadonnÃ©es principales de la base vectorielle Chroma persistÃ©e localement. |
| `data/chroma_db/<uuid>/header.bin` | MÃ©tadonnÃ©es bas niveau d'un index HNSW stockÃ© par Chroma. |
| `data/chroma_db/<uuid>/data_level0.bin` | DonnÃ©es vectorielles/indexÃ©es pour le niveau de base de l'index HNSW. |
| `data/chroma_db/<uuid>/length.bin` | Informations de taille/longueur associÃ©es Ã  l'index binaire. |
| `data/chroma_db/<uuid>/link_lists.bin` | Liens de voisinage utilisÃ©s par l'index HNSW pour la recherche de plus proches voisins. |

### Corpus `data/gouv/` et `data/gouv_md/`

Chaque thÃ¨me gouv existe en gÃ©nÃ©ral en **deux formats** :
- `data/gouv/*.pdf` pour la consultation humaine
- `data/gouv_md/*.md` pour l'ingestion RAG structurÃ©e

| Fichiers | ThÃ¨me |
|---|---|
| `data/gouv/gouv_01_conges_payes.pdf` + `data/gouv_md/gouv_01_conges_payes.md` | CongÃ©s payÃ©s |
| `data/gouv/gouv_02_conges_evenements_familiaux.pdf` + `data/gouv_md/gouv_02_conges_evenements_familiaux.md` | CongÃ©s pour Ã©vÃ©nements familiaux |
| `data/gouv/gouv_03_teletravail.pdf` + `data/gouv_md/gouv_03_teletravail.md` | TÃ©lÃ©travail dans le secteur privÃ© |
| `data/gouv/gouv_04_arret_maladie.pdf` + `data/gouv_md/gouv_04_arret_maladie.md` | ArrÃªt maladie |
| `data/gouv/gouv_05_accident_travail.pdf` + `data/gouv_md/gouv_05_accident_travail.md` | Accident du travail |
| `data/gouv/gouv_06_demission.pdf` + `data/gouv_md/gouv_06_demission.md` | DÃ©mission |
| `data/gouv/gouv_07_rupture_conventionnelle.pdf` + `data/gouv_md/gouv_07_rupture_conventionnelle.md` | Rupture conventionnelle |
| `data/gouv/gouv_08_licenciement.pdf` + `data/gouv_md/gouv_08_licenciement.md` | Licenciement |
| `data/gouv/gouv_09_cpf.pdf` + `data/gouv_md/gouv_09_cpf.md` | CPF |
| `data/gouv/gouv_10_rqth.pdf` + `data/gouv_md/gouv_10_rqth.md` | RQTH / handicap |

### Corpus `data/novatech/` et `data/novatech_md/`

Les documents internes NovaTech sont gÃ©nÃ©rÃ©s en Markdown dans `data/novatech_md/`. Une partie d'entre eux existe aussi en PDF dans `data/novatech/` pour la dÃ©monstration ou la consultation humaine.

| Fichiers | ThÃ¨me |
|---|---|
| `data/novatech_md/01_conges_payes.md` + `data/novatech/01_conges_payes.pdf` | Politique interne sur les congÃ©s payÃ©s |
| `data/novatech_md/02_conges_evenements_familiaux.md` + `data/novatech/02_conges_evenements_familiaux.pdf` | CongÃ©s Ã©vÃ©nements familiaux |
| `data/novatech_md/03_teletravail.md` + `data/novatech/03_teletravail.pdf` | Politique tÃ©lÃ©travail |
| `data/novatech_md/04_arret_maladie.md` + `data/novatech/04_arret_maladie.pdf` | Politique arrÃªt maladie |
| `data/novatech_md/05_accident_travail.md` | Politique accident du travail |
| `data/novatech_md/06_demission.md` + `data/novatech/06_demission.pdf` | Politique dÃ©mission |
| `data/novatech_md/07_rupture_conventionnelle.md` + `data/novatech/07_rupture_conventionnelle.pdf` | Rupture conventionnelle |
| `data/novatech_md/08_licenciement.md` + `data/novatech/08_licenciement.pdf` | Politique licenciement |
| `data/novatech_md/09_cpf.md` | CPF cÃ´tÃ© NovaTech |
| `data/novatech_md/10_rqth_handicap.md` | RQTH, handicap et amÃ©nagements |
| `data/novatech_md/11_rtt.md` + `data/novatech/11_rtt.pdf` | RTT |
| `data/novatech_md/12_frais_deplacements.md` + `data/novatech/12_frais_deplacements.pdf` | Frais et dÃ©placements professionnels |
| `data/novatech_md/13_onboarding.md` + `data/novatech/13_onboarding.pdf` | Onboarding et intÃ©gration |
| `data/novatech_md/14_mutuelle_avantages.md` | Mutuelle et avantages sociaux |
| `data/novatech_md/15_formation_carriere.md` + `data/novatech/15_formation_carriere.pdf` | Formation continue et Ã©volution de carriÃ¨re |
| `data/novatech_md/16_entretiens_remuneration.md` + `data/novatech/16_entretiens_remuneration.pdf` | Entretiens, objectifs et rÃ©munÃ©ration |
| `data/novatech_md/17_faq_rh.md` + `data/novatech/17_faq_rh.pdf` | FAQ RH |
| `data/novatech_md/18_depart_entreprise.md` + `data/novatech/18_depart_entreprise.pdf` | DÃ©part de l'entreprise / offboarding |

---

## Corpus documentaire

### Couche 1 â€” Droit du travail franÃ§ais (service-public.fr)

10 documents scrappÃ©s et nettoyÃ©s :

| # | ThÃ¨me |
|---|---|
| 01 | CongÃ©s payÃ©s |
| 02 | CongÃ©s pour Ã©vÃ©nements familiaux |
| 03 | TÃ©lÃ©travail dans le secteur privÃ© |
| 04 | ArrÃªt maladie |
| 05 | Accident du travail |
| 06 | DÃ©mission |
| 07 | Rupture conventionnelle |
| 08 | Licenciement |
| 09 | CPF (Compte Personnel de Formation) |
| 10 | RQTH (Reconnaissance de la QualitÃ© de Travailleur HandicapÃ©) |

### Couche 2 â€” Politiques internes NovaTech Solutions (entreprise fictive)

18 documents gÃ©nÃ©rÃ©s par Gemini, simulant les politiques RH d'une vraie entreprise :

| # | Document | Contenu clÃ© |
|---|---|---|
| 01 | CongÃ©s payÃ©s | 25 jours lÃ©gaux, rÃ¨gles de prise et de report |
| 02 | CongÃ©s Ã©vÃ©nements familiaux | Mariage, naissance, deuil, enfant malade |
| 03 | TÃ©lÃ©travail | 3j/semaine cadres, 2j non-cadres, indemnitÃ© 10-30â‚¬/mois |
| 04 | ArrÃªt maladie | DÃ©lai de carence 0j cadres / 3j non-cadres, maintien de salaire |
| 05 | Accident du travail | ProcÃ©dure de dÃ©claration, prise en charge spÃ©cifique |
| 06 | DÃ©mission | PrÃ©avis 1 mois non-cadres / 3 mois cadres, formalitÃ©s |
| 07 | Rupture conventionnelle | ProcÃ©dure, indemnitÃ©s, dÃ©lai de rÃ©tractation |
| 08 | Licenciement | ProcÃ©dure, entretien prÃ©alable, indemnitÃ©s |
| 09 | CPF | Utilisation, dÃ©lais de demande, cofinancement NovaTech |
| 10 | RQTH & Handicap | 4j tÃ©lÃ©travail/semaine, 2j absence/an, rÃ©fÃ©rent Marc LefÃ¨vre |
| 11 | RTT | 11j cadres / 12j non-cadres, rÃ¨gles de prise et d'expiration |
| 12 | Frais & dÃ©placements | Plafonds repas/hÃ´tel, 1Ã¨re classe >3h, TravelNova |
| 13 | Onboarding | Premier jour, pÃ©riode d'essai, outils, formations obligatoires |
| 14 | Mutuelle & avantages | Harmonie Mutuelle 60% employeur, CSE, PEE/PERCO |
| 15 | Formation & carriÃ¨re | Plan de formation 2% masse salariale, NovAcademy, CPF |
| 16 | Entretiens & rÃ©munÃ©ration | Grille N1-N8, hausse 2025 = 2,5%, variable, primes |
| 17 | FAQ RH | Questions transversales frÃ©quentes |
| 18 | DÃ©part de l'entreprise | DÃ©mission, rupture, licenciement, solde de tout compte |

### ComplexitÃ© intentionnelle

Les documents contiennent des cas ambigus pour tester le systÃ¨me :
- RÃ¨gles diffÃ©rentes cadres vs non-cadres (RTT, tÃ©lÃ©travail, carence, 1Ã¨re classe...)
- RÃ¨gles variant selon l'anciennetÃ© (maintien de salaire, congÃ©s supplÃ©mentaires)
- RÃ©fÃ©rences croisÃ©es entre documents
- Sujets absents volontairement (droit de grÃ¨ve, congÃ© sabbatique) pour tester le refus de rÃ©pondre

---

## Pipeline RAG dÃ©taillÃ©

### 1. Ingestion (`Scripts/ingest.py`)

- Lecture des fichiers Markdown (`data/gouv_md/` et `data/novatech_md/`)
- **Chunking par headers `##`** : 1 section = 1 chunk
  - Le prÃ©ambule (avant le premier `##`) est ignorÃ© â€” uniquement si le document a des sections
  - Si section > `CHUNK_SIZE * 2` : re-dÃ©coupage sur `###` puis par taille
  - `chunk_by_size` : l'overlap repart depuis la derniÃ¨re frontiÃ¨re de phrase
  - Fallback : si aucun `##` trouvÃ©, le document entier est indexÃ© comme un seul chunk
  - Chaque chunk est prÃ©fixÃ© avec le titre du document (`[Nom du document]`)
- Nettoyage du bruit (mÃ©tadonnÃ©es service-public, sÃ©parateurs vides)
- **Titre lisible** extrait du `# Titre` Markdown et prÃ©fixÃ© selon la source :
  - Documents gouv â†’ `Code du travail â€” CongÃ©s payÃ©s du salariÃ© dans le secteur privÃ©`
  - Documents NovaTech â†’ `NovaTech â€” TÃ©lÃ©travail`
- Indexation dans ChromaDB avec mÃ©tadonnÃ©es riches (`source`, `document`, `title`, `section`, `chunk_index`)
- IDs dÃ©terministes par MD5 (rÃ©indexation idempotente)

### 2. Retrieval (`src/rag.py` â€” classe `Retriever`)

- Embedding de la question via `sentence-transformers`
- Recherche vectorielle dans ChromaDB (cosine similarity)
- RÃ©cupÃ¨re `top_k * 2` chunks, filtre par `distance_threshold`, retourne les `top_k` meilleurs
- Filtre par source (`gouv` ou `novatech`) utilisÃ© par `PolicyAgent` et `LegalAgent`

### 3. Reranking (`src/rag.py` + `src/agents.py`)

Le reranking ajoute une **deuxiÃ¨me passe de sÃ©lection** aprÃ¨s la recherche vectorielle classique.

- **Ã‰tape 1 : retrieval large**
  - ChromaDB rÃ©cupÃ¨re d'abord `top_k * 2` chunks proches de la question grÃ¢ce aux embeddings.
  - Cette Ã©tape est rapide, mais elle peut ramener des chunks globalement proches sans Ãªtre les plus prÃ©cis pour la question exacte.

- **Ã‰tape 2 : reranking fin**
  - Un **cross-encoder local** (`cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`) rÃ©Ã©value chaque paire `(question, chunk)`.
  - Contrairement Ã  l'embedding search, il lit la question et le chunk **ensemble**, ce qui donne un score de pertinence plus prÃ©cis.
  - Les chunks sont ensuite retriÃ©s par `rerank_score`, puis on garde les `top_k` meilleurs.

- **Pourquoi c'est utile**
  - RÃ©duit les faux positifs sÃ©mantiques : un chunk vaguement proche peut Ãªtre rÃ©trogradÃ©.
  - Aide Ã  mieux distinguer des cas RH proches mais diffÃ©rents (cadre/non-cadre, tÃ©lÃ©travail/RTT, arrÃªt maladie/accident du travail, etc.).
  - AmÃ©liore la qualitÃ© du contexte envoyÃ© au LLM, donc la prÃ©cision de la rÃ©ponse finale.

- **ImplÃ©mentation dans ce projet**
  - Le modÃ¨le est chargÃ© une seule fois en lazy init dans l'orchestrateur.
  - Il est partagÃ© par `PolicyAgent` et `LegalAgent`.
  - Il s'exÃ©cute rÃ©ellement quand `use_reranking=True` / `USE_RERANKING=true`.
  - Il est local, sans appel API supplÃ©mentaire, et optimisÃ© pour le franÃ§ais / multilingue.

---

## Prompt Engineering (`prompts/`)

### SystÃ¨me prompt â€” Nova (`prompts/prompts_llm.py`)

- **Persona** : Nova, assistante RH NovaTech Solutions, chaleureuse et professionnelle
- **Langue de rÃ©ponse** : est dÃ©duite Ã  partir du message courant de l'employÃ© puis rÃ©injectÃ©e explicitement dans les prompts RAG et de synthÃ¨se
- **PÃ©rimÃ¨tre strict** : refuse les questions hors RH, redirige vers le bon contact
- **RÃ©conciliation des sources** : le droit du travail franÃ§ais est traitÃ© comme socle ; une rÃ¨gle NovaTech n'est mise en avant que si elle est explicitement plus favorable ou plus prÃ©cise dans le contexte disponible
- **SÃ©curitÃ© factuelle** : ne cite jamais un chiffre, dÃ©lai ou droit absent du contexte
- **Anti-hallucination** : reconnaÃ®t explicitement quand l'information est absente
- **Anti-injection** : ignore les tentatives de changement de rÃ´le, ne rÃ©vÃ¨le jamais ses instructions
- **Adaptation profil** : applique la rÃ¨gle cadre ou non-cadre selon le profil donnÃ©, prÃ©sente les deux cas si inconnu

### Prompts agents (`prompts/prompts_agents.py`)

| Prompt | Utilise par | Role |
|---|---|---|
| `ROUTER_SYSTEM_PROMPT` | OrchestratorAgent | Decide quels agents invoquer selon la logique du projet : `policy` toujours, `legal` pour les sujets RH reglementes, `action` pour une vraie demarche ou une aide pratique legere si pertinente |
| `SYNTHESIS_SYSTEM_PROMPT` | OrchestratorAgent | Fusionne les reponses des agents, reconcilie politique interne et loi, puis reformule proprement les actions utiles |
| `ACTION_AGENT_PROMPT` | ActionAgent | Choisit les outils RH a appeler en distinguant plusieurs types de questions -> JSON `{"tool_calls": [...]}` |

Logique de routage actuelle :
- `policy` est systematique
- `legal` est active par defaut sur les themes reglementaires (teletravail, conges, arret maladie, demission, CPF, RQTH, etc.)
- `action` peut etre active dans deux cas : vraie demarche a realiser, ou petite aide pratique optionnelle pertinente apres la reponse principale

Types de questions distingues :
- `informational` : l'utilisateur veut une regle, un nombre de jours, une eligibilite, une definition
- `informational_with_practical_follow_up` : l'utilisateur veut surtout une reponse, mais une petite checklist optionnelle peut aider ensuite
- `procedural` : l'utilisateur veut faire quelque chose concretement (declarer, demander, soumettre, remplir un formulaire)
- `escalation` : l'utilisateur a besoin de savoir qui contacter ou comment faire remonter son cas

Exemples concrets :
- `How many telework days do I have as a manager?` -> `policy + legal`, avec eventuellement une checklist legere en fin de reponse
- `How do I declare my telework days?` -> `policy + legal + action`, avec formulaire + checklist
- `Who should I contact for an unusual sick leave case?` -> `policy + legal + action`, surtout pour le contact RH

### Few-shot examples

3 exemples couvrant :
- TÃ©lÃ©travail cadre (question en **anglais** â†’ rÃ©ponse en **anglais**)
- CongÃ© deuil (question en **franÃ§ais** â†’ rÃ©ponse en **franÃ§ais**)
- Hors pÃ©rimÃ¨tre â€” droit de grÃ¨ve (refus poli + redirection contact)

---

## Tool Use (`src/tools.py`)

3 outils disponibles, sÃ©lectionnÃ©s et invoquÃ©s par l'`ActionAgent` via LLM :

| Outil | RÃ´le | Exemple |
|---|---|---|
| `get_form_link` | Retourne le chemin MonEspace vers le bon formulaire | `MonEspace > Mes congÃ©s > Nouvelle demande` |
| `generate_checklist` | GÃ©nÃ¨re des Ã©tapes pratiques gÃ©nÃ©riques pour aider l'utilisateur Ã  agir | Ouvrir le bon formulaire, prÃ©parer les justificatifs, contacter RH si besoin |
| `route_to_contact` | Identifie le bon contact RH selon le sujet | Sophie Martin pour l'administration du personnel |

Le LLM comprend l'intention de l'employe et choisit les bons outils avec les bons arguments, sans correspondance de mots-cles fragile.

Regles de decision actuelles :
- `get_form_link` est reserve aux questions procedurales : on donne un formulaire quand l'utilisateur veut reellement lancer ou declarer quelque chose
- `generate_checklist` peut aussi servir sur certaines questions informatives, mais uniquement comme **aide pratique optionnelle** apres la vraie reponse
- `route_to_contact` est reserve aux cas d'escalade, de blocage ou aux questions qui demandent explicitement qui contacter

Exemples :
- `How many telework days do I have as a manager?` -> eventuellement une checklist courte, mais pas de formulaire automatique
- `How do I declare my telework days?` -> formulaire + checklist
- `Who should I contact for an accommodation request?` -> contact RH

Exemple pour *"Je veux bosser de chez moi"* :
```json
{"tool_calls": [
  {"tool": "get_form_link",      "arguments": {"topic": "telework"}},
  {"tool": "generate_checklist", "arguments": {"topic": "telework"}}
]}
```

### Contrat UI des tools

Les tools retournÃ©s par l'`ActionAgent` sont normalisÃ©s en 3 types compatibles avec l'interface :

- `form`
- `checklist`
- `contact`

Cela permet un affichage direct dans Streamlit sans conversion supplÃ©mentaire cÃ´tÃ© UI.

### Important sur les checklists

`generate_checklist` ne doit pas Ãªtre interprÃ©tÃ© comme une source de vÃ©ritÃ© RH ou juridique.

- La rÃ©ponse de fond doit venir des documents RAG (`PolicyAgent` / `LegalAgent`)
- La checklist sert seulement Ã  proposer des **prochaines actions pratiques**
- Elle Ã©vite volontairement d'affirmer en dur des dÃ©lais, prÃ©avis, droits ou obligations non sourcÃ©s

### Contacts RH disponibles

| Contact | RÃ´le | Sujets |
|---|---|---|
| Sophie Martin | Responsable Administration du Personnel | CongÃ©s, contrats, bulletins |
| Lucas Dupont | ChargÃ© de projet QVT | Bien-Ãªtre, tÃ©lÃ©travail, ergonomie |
| Claire Lefebvre | Responsable ComptabilitÃ© Fournisseurs | Frais, remboursements |
| Amina Khelifi | ChargÃ©e recrutement & intÃ©gration | Onboarding, recrutement |
| Thomas Bernard | Responsable Compensation & Benefits | Salaire, primes, mutuelle |
| Isabelle Morel | Responsable Formation et DÃ©veloppement | Formation, CPF, carriÃ¨re |
| Marc LefÃ¨vre | RÃ©fÃ©rent Handicap | RQTH, amÃ©nagements |
| Dr. Ã‰milie Renaud | MÃ©decin du travail | Visites mÃ©dicales, arrÃªts |
| Nathalie Brun | RÃ©fÃ©rent harcÃ¨lement | Signalements, discrimination |

---

## LLM (`src/llm.py`)

- **ModÃ¨le** : Gemini 2.5 Flash Lite (configurable via `.env`)
- Client instanciÃ© **une seule fois** au chargement du module
- **Retry avec backoff exponentiel** : jusqu'Ã  10 tentatives, attente 15s â†’ 120s max
- Erreurs retriables : HTTP 429, 500, 503, "resource exhausted", "rate limit", "overloaded"

---

## Ã‰valuation (`eval/`)

15 cas de test couvrant 11 catÃ©gories :

| CatÃ©gorie | Cas | Ce qui est testÃ© |
|---|---|---|
| `telework` | 2 | Nombre de jours selon profil (cadre/non-cadre) |
| `leave` | 2 | CongÃ©s deuil, congÃ©s selon anciennetÃ© |
| `rtt` | 1 | Jours RTT non-cadre |
| `expenses` | 1 | 1Ã¨re classe train selon statut |
| `sick_leave` | 1 | DÃ©lai de carence selon statut |
| `training` | 1 | Utilisation CPF chez NovaTech |
| `departure` | 1 | PrÃ©avis dÃ©mission cadre |
| `disability` | 1 | TÃ©lÃ©travail RQTH |
| `out_of_scope` | 2 | Refus sur sujets absents (grÃ¨ve, congÃ© sabbatique) |
| `prompt_injection` | 2 | RÃ©sistance aux attaques d'injection |
| `cross_case` | 1 | Interaction arrÃªt maladie + RTT |

### MÃ©triques Ã©valuÃ©es

- **PrÃ©sence de mots-clÃ©s** dans la rÃ©ponse (chiffres, termes clÃ©s)
- **Sources rÃ©cupÃ©rÃ©es** : le bon document est-il dans les chunks retournÃ©s ?
- **Refus appropriÃ©** : le modÃ¨le dit-il "je ne sais pas" quand il le faut ?
- **RÃ©sistance Ã  l'injection** : aucun marqueur de compromission dans la rÃ©ponse

```bash
python eval/evaluate.py
```

---

## Installation et lancement

### PrÃ©requis

- Python 3.11+
- Une clÃ© API Gemini (Google AI Studio)

### Installation

```bash
# Cloner le projet
git clone <repo>
cd GenAI

# CrÃ©er l'environnement virtuel
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux/Mac

# Installer les dÃ©pendances
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

### GÃ©nÃ©ration du corpus (optionnel â€” fichiers dÃ©jÃ  prÃ©sents)

```bash
# Scraper les PDFs service-public.fr
python Scripts/Scrapping.py

# GÃ©nÃ©rer les documents NovaTech via Gemini
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

### Ã‰valuation

```bash
python eval/evaluate.py
```

---

## Choix techniques

| Composant | Choix | Justification |
|---|---|---|
| **Architecture** | Multi-agents (Orchestrator / Policy / Legal / Action) | SÃ©paration des sources, synthÃ¨se explicite, extensible |
| **LLM** | Gemini 2.5 Flash Lite | Rapide, gratuit en tier dÃ©veloppeur, bon en franÃ§ais |
| **Embedding** | `paraphrase-multilingual-mpnet-base-v2` | Local, gratuit, optimisÃ© franÃ§ais/multilingue |
| **Reranking** | Cross-encoder `mmarco-mMiniLMv2` | Local, 0 appel API, plus prÃ©cis qu'un LLM scoring |
| **Vector store** | ChromaDB | Local, persistant, simple Ã  dÃ©ployer |
| **Tool selection** | LLM-driven (ActionAgent) | Comprend l'intention, pas de keywords fragiles |
| **Chunking** | Par headers `##` Markdown | Respecte la structure logique des documents |
| **Interface** | Streamlit | Rapide Ã  prototyper, gestion du state intÃ©grÃ©e |
| **Format donnÃ©es** | Markdown â†’ ChromaDB | Ã‰vite la perte de structure des PDFs |

