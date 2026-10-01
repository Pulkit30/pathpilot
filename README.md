# PathPilot

PathPilot recommends careers and builds personalized learning roadmaps. You describe yourself in plain
English ("I know Python and like math, I want to work in AI"), and a **custom ML model built from scratch
with NumPy** suggests the best-fit careers. It then generates a step-by-step roadmap that skips the skills
you already have.

**Stack:** React · FastAPI · Python/NumPy (from-scratch ML) · MongoDB Atlas · Vercel

## Project structure

```
path_pilot/
├── data/        Knowledge base: careers, skill graph, resources, synonyms   ← Phase 1 ✅
├── ml/          From-scratch NLP + recommendation model                     ← Phase 2 ✅
├── backend/     FastAPI app                                                 ← Phase 3 ✅
├── frontend/    React app                                                   ← Phase 4 ✅
└── mcp/         MCP server                                                  ← Phase 8
```

## Build phases

| # | Phase | Status |
|---|---|---|
| 1 | Data & skill graph | ✅ Done |
| 2 | ML core (NLP, TF-IDF, softmax, roadmap builder) | ✅ Done |
| 3 | FastAPI backend + MongoDB | ✅ Done |
| 4 | React frontend | ✅ Done |
| 5 | Progress tracking & feedback loop | ✅ Done |
| 6 | Deploy to Vercel | ⏳ |
| 7 | RAG "AI Mentor" chat | ⏳ |
| 8 | MCP server | ⏳ |

## Data (Phase 1)

| File | Contents |
|---|---|
| `data/careers.json` | 15 tech careers: description, interest keywords, demand, salary range, and a roadmap split into beginner / intermediate / advanced stages, plus optional skills |
| `data/skills.json` | 135 skills forming a prerequisite graph (DAG): category, difficulty (1–5), estimated hours, description, prerequisites |
| `data/resources.json` | 270+ free learning resources (2–3 per skill) |
| `data/synonyms.json` | Variants users type (`js`, `k8s`, `sklearn`, `artificial intelligence`, …) mapped to canonical skill ids and interests |
| `data/validate.py` | Integrity checker |

Each skill is stored **once** and shared across careers. Python, for example, appears in eight roadmaps.
Knowing a skill therefore shortens every roadmap that contains it.

### Validate the data

```bash
python3 data/validate.py                # structure, references, cycles, stage ordering
python3 data/validate.py --check-links  # also checks every resource URL is live
```

The validator checks for:
- unique snake_case ids and the required fields on every skill and career
- prerequisite references that exist, with **no cycles** (A needs B needs A)
- **career completeness**: every prerequisite of a career's skill is also in that career, in the same or an earlier stage
- at least one resource per skill, with valid URLs and no duplicates
- synonyms that point at real skills or interests

> Salary ranges (`salary_inr_lpa`, in ₹ lakhs per annum, entry → mid level) are rough indicative figures for
> the Indian market. They are not authoritative data.

## ML engine (Phase 2)

Everything in `ml/` is written from scratch. The only dependency is **NumPy**, with no scikit-learn,
TensorFlow or NLP libraries.

```
"I know Python and pandas, I like math, I want to work in AI"
        │
   nlp.py        tokenize · stopwords · stemming · synonym & phrase matching · known-vs-goal intent · negation
        │        → known: [python, pandas]  interests: [math, ai]
   tfidf.py      features → TF-IDF vector (600 features)
        │
        ├── softmax.py      classifier trained with mini-batch gradient descent + momentum
        └── similarity.py   cosine similarity with each career's profile vector
        │
   recommender.py   blend = α·P_classifier + (1-α)·softmax(T·cosine)   (α, T tuned on validation set)
        │           → ML Engineer 87.6%, Data Scientist 10.7%, … with reasons
   roadmap.py       skill gap (incl. implied prerequisites) + topological sort (Kahn's algorithm)
                    → ordered steps with hours, stages and free resources
```

| File | Purpose |
|---|---|
| `kb.py` | Loads the knowledge base from `data/` |
| `nlp.py` | Parses free text into tokens, known/goal/negated skills, interests, career mentions |
| `generate_data.py` | Creates 2,400 synthetic labelled profiles (`data/training_profiles.json`) |
| `tfidf.py` | TF-IDF vectorizer |
| `softmax.py` | Softmax classifier: forward pass, cross-entropy, gradients, gradient descent |
| `similarity.py` | Cosine similarity and career profile documents |
| `recommender.py` | Hybrid scoring, explanations, confidence |
| `roadmap.py` | Personalised, prerequisite-ordered roadmap |
| `train.py` / `evaluate.py` / `predict.py` | Train, measure, and query from the terminal |
| `artifacts/` | Trained model (~96 KB), committed so deployment needs no training |

### Commands

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m ml.generate_data                 # (re)create synthetic training data
.venv/bin/python -m ml.train                         # train + save to ml/artifacts/
.venv/bin/python -m ml.evaluate                      # accuracy report
.venv/bin/python -m ml.predict "I love video games and know C#"
.venv/bin/python -m unittest discover -s ml/tests -t .   # 21 unit tests, incl. a gradient check
```

### Results

| Dataset | Classifier only | Similarity only | **Hybrid** |
|---|---|---|---|
| Synthetic test split (360, held out) top-1 / top-3 | 94.2% / 99.7% | 93.9% / 99.4% | **94.7% / 100%** |
| Hand-written realistic queries (45, never trained on) top-1 / top-3 | 95.6% / 97.8% | 97.8% / 100% | **97.8% / 97.8%** |

The hand-written set is small (3 queries per career), so treat it as a sanity check rather than a
precise benchmark. Training data is synthetic. Once real users give 👍/👎 feedback (Phase 5), that
data will be added and the model retrained.

## Backend API (Phase 3)

FastAPI app in `backend/app/`. It loads the trained model once at startup and serves it over HTTP.
MongoDB stores **users, saved roadmaps and feedback**. Careers, skills and resources are read from `data/*.json`, so they
always match the trained model.

```
backend/app/
├── main.py      app setup: CORS, routers, loads the model at startup
├── config.py    settings from environment variables / .env
├── deps.py      shared pieces: the model, the user store, the logged-in user
├── schemas.py   request/response shapes (validation + /docs)
├── security.py  bcrypt password hashing + JWT login tokens
├── db.py        storage for users, saved roadmaps, feedback: MongoDB (real) or in-memory (tests)
└── routes/
    ├── recommend.py   POST /api/recommend, POST /api/roadmap
    ├── catalog.py     GET  /api/careers, /api/careers/{id}, /api/skills
    ├── auth.py        POST /api/auth/register, /api/auth/login · GET /api/auth/me
    ├── progress.py    /api/roadmaps: save, list, mark steps done, delete (login required)
    └── feedback.py    POST /api/feedback
```

| Method | Endpoint | What it does |
|---|---|---|
| GET | `/api/health` | Server and model status |
| POST | `/api/recommend` | `{query, known_skills?, top_k?, min_match?}` → top careers with match %, reasons, what the NLP understood |
| POST | `/api/roadmap` | `{career_id, known_skills, hours_per_week}` → ordered learning plan |
| GET | `/api/careers` | All 15 careers (summary) |
| GET | `/api/careers/{id}` | One career with its staged skills |
| GET | `/api/skills` | All 135 skills (for the skill-chip picker) |
| POST | `/api/auth/register` | Create an account → JWT token |
| POST | `/api/auth/login` | Log in → JWT token |
| GET | `/api/auth/me` | Current user (needs `Authorization: Bearer <token>`) |
| GET | `/api/roadmaps` | 🔒 My saved roadmaps with progress |
| POST | `/api/roadmaps` | 🔒 Save a roadmap (or update its known skills / weekly hours) |
| GET | `/api/roadmaps/{career_id}` | 🔒 One saved roadmap with its plan and completed skills |
| PUT | `/api/roadmaps/{career_id}/skills/{skill_id}` | 🔒 `{done: true/false}`: mark a step done or not |
| DELETE | `/api/roadmaps/{career_id}` | 🔒 Remove a saved roadmap |
| POST | `/api/feedback` | 👍/👎 on a recommendation (`rating` 1 or -1); works logged in or not |

Without `MONGODB_URI`/`JWT_SECRET`, the recommendation and catalog endpoints still work and the
account endpoints return 503.

### Run it

```bash
.venv/bin/pip install -r requirements-dev.txt
cp .env.example .env                     # then set JWT_SECRET (and MONGODB_URI if not local)
.venv/bin/uvicorn backend.app.main:app --reload
```

Open **http://localhost:8000/api/docs** to try every endpoint in the browser.

```bash
.venv/bin/python -m pytest -q            # all tests (ML + API)
```

## Frontend (Phase 4)

React app in `frontend/`, built with Vite, styled with Tailwind CSS, with React Router for pages and
React Flow for the roadmap graph. In development, Vite forwards `/api/*` to FastAPI on port 8000,
so the browser talks to one origin, the same as production on Vercel.

| Page | URL | What it shows |
|---|---|---|
| Ask | `/` | Free-text question box with example prompts |
| Results | `/results?q=…` | Top careers with match %, reasons, demand and salary; **editable skill chips** ("What I understood") that re-run the model |
| Roadmap | `/roadmap/:careerId?known=…&hours=…` | Stats, study-hours selector, skipped skills, **graph view** (React Flow) or list view; click a skill for details and free resources |
| Careers | `/careers` | All 15 careers, filterable by category |
| Career | `/careers/:careerId` | Staged skills; pick skills you know, then build your roadmap |
| Log in / Sign up | `/login`, `/register` | Accounts (JWT stored in the browser) |
| My roadmaps | `/my-roadmaps` | 🔒 Saved roadmaps with progress bars; continue or remove |

```
frontend/src/
├── api.js          every backend call lives here
├── auth.jsx        login state shared by all pages
├── hooks.js        useAsync (loading/error/data), useSkills
├── constants.js    stage colours, demand colours, salary format
├── components/     Navbar, CareerCard, SkillPicker, RoadmapGraph, SkillDrawer, ui
└── pages/          Home, Results, Roadmap, Careers, CareerDetail, AuthPage, NotFound
```

### Run the whole app

```bash
# terminal 1: backend
.venv/bin/uvicorn backend.app.main:app --reload
# terminal 2: frontend
cd frontend && npm install && npm run dev
```

Open **http://localhost:5173**.

## Progress & feedback loop (Phase 5)

- **Save a roadmap** from the roadmap page (login required). Then tick steps as done in the list view
  or in the skill panel. Progress, hours left and weeks left update instantly, and everything is listed
  under **My roadmaps**.
- **👍/👎** under each recommended career is stored in MongoDB (`feedback` collection) together with
  the model version that made the recommendation.

### Retraining with feedback

```
👍 in the app ─► MongoDB feedback ─► ml/retrain.py ─► data/feedback_profiles.json + new model ─► commit ─► deploy
```

```bash
.venv/bin/python -m ml.retrain --dry-run   # see what would change, save nothing
.venv/bin/python -m ml.retrain             # retrain and save only if the quality gate passes
```

- A 👍 turns (question, career) into a new training example, weighted 3× a synthetic one. A 👎 is
  kept for analysis but isn't a label, because it says which career is wrong, not which is right.
- Duplicates are removed, each user contributes at most 20 examples, and questions identical to the
  hand-written test set are skipped so the test stays honest.
- Feedback examples go into the **training split only**, so test scores stay comparable.
- **Quality gate:** the new model is saved only if hand-written top-1 doesn't drop and synthetic
  top-1 drops by at most 1 point (`--force` overrides).
- `python -m ml.train` always includes `data/feedback_profiles.json` if it exists, so retraining from
  scratch keeps what users taught it.
