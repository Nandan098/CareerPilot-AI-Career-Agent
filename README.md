# CareerPilot — AI Career Agent

CareerPilot is a portfolio project for an AI/software engineering internship. It demonstrates a conversational career assistant, persistent candidate preferences, job search, explainable job ranking, saved jobs, a Python API, and an optional LLM tool-calling agent.

> **Important demo note:** The included job listings and companies are synthetic examples. The application does not crawl the web or verify real vacancies. Match percentages are a transparent heuristic score, not a probability of getting hired.

## What you can do

- Browse a catalogue of sample internship and entry-level jobs.
- Search by role, skill, location, and work mode.
- See a match score, the reasons behind it, and required skills missing from your profile.
- If an OpenAI key is configured, cache text embeddings for jobs and use cosine similarity as an extra semantic-ranking signal; without a key, use the offline keyword and profile-matching baseline.
- Edit your candidate profile: skills, target roles, location, work mode, minimum salary, and deal-breakers.
- Save and remove jobs from a persistent shortlist.
- Chat with CareerPilot. With an OpenAI API key it uses tool calling to search jobs, update preferences, and manage saved jobs. Without a key, demo mode still supports searching, listing saved jobs, and a few straightforward preference updates.
- Run basic tests for the matching logic.

## Architecture

```text
React + Vite frontend (localhost:5173)
             | REST / JSON
             v
FastAPI backend (localhost:8000)
   |                |                   |
   v                v                   v
SQLAlchemy      Match scorer        Agent tools
   |                ^                   |
   v                |                   v
SQLite + cached    Optional         OpenAI chat API
profile/job data   embeddings       (or offline demo)
                    |
                    v
              cosine similarity
```

### Folder layout

```text
CareerPilot/
├── README.md
├── docker-compose.yml
├── backend/
│   ├── app/
│   │   ├── agent.py          # OpenAI tool calling + no-key fallback
│   │   ├── embeddings.py     # Optional embeddings + cosine similarity
│   │   ├── config.py         # Environment settings
│   │   ├── database.py       # SQLAlchemy engine and sessions
│   │   ├── main.py           # FastAPI routes
│   │   ├── matching.py       # Transparent match scoring
│   │   ├── models.py         # Database tables
│   │   ├── repository.py     # Job/profile/saved-job database helpers
│   │   ├── schemas.py        # Pydantic request/response validation
│   │   └── seed.py           # Synthetic starter jobs
│   ├── tests/test_matching.py
│   ├── tests/test_embeddings.py
│   ├── .env.example
│   ├── Dockerfile
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── App.jsx           # Pages and shared UI state
    │   ├── main.jsx          # React entry point
    │   └── styles.css        # Responsive styling
    ├── index.html
    ├── package.json
    ├── vite.config.js
    ├── Dockerfile
    └── nginx.conf
```

## Option A — Run locally (recommended while learning)

### Requirements

- Python 3.11 or newer
- Node.js 20.19+ (or 22.12+) and npm
- Git, if you want to push it to GitHub

### 1. Start the backend

Open a terminal in the project folder, then run:

```bash
cd backend
python -m venv .venv
```

Activate the environment:

**Windows PowerShell**

```powershell
.venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
source .venv/bin/activate
```

Install the Python packages:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create your local environment file:

**Windows PowerShell**

```powershell
Copy-Item .env.example .env
```

**macOS / Linux**

```bash
cp .env.example .env
```

The default `.env` uses SQLite and needs no separate database installation. Leave `OPENAI_API_KEY` blank for demo mode. Start the API:

```bash
uvicorn app.main:app --reload --port 8000
```

On startup, CareerPilot creates the tables and inserts the sample jobs if the local job table is empty.

Check the API:

- Health: http://localhost:8000/api/health
- Swagger / interactive API docs: http://localhost:8000/docs
- Jobs: http://localhost:8000/api/jobs
- Current profile: http://localhost:8000/api/profile

Keep this terminal open.

### 2. Start the frontend

Open a second terminal from the project folder:

```bash
cd frontend
npm install
```

Optionally create the frontend `.env` from `.env.example`. The default URL already points to the local API. Start the UI:

```bash
npm run dev
```

Open http://localhost:5173.

### 3. Try these demo prompts

In **AI career agent**, try:

- `Find AI internships in Bengaluru`
- `Show my saved jobs`
- `Save job 1`
- `I prefer remote only`
- `My skills are Python, FastAPI, SQL, and embeddings`

The offline fallback deliberately understands only a small set of simple patterns; natural-language tool selection is enabled when an OpenAI key is set.

## Option B — Enable the OpenAI agent

1. Get an API key from your OpenAI developer account.
2. Put it in `backend/.env` as `OPENAI_API_KEY=your_key_here`.
3. Optionally set `OPENAI_MODEL` to a model available to your account.
4. Restart the backend.

The agent exposes an allow-list of backend tools: `search_jobs`, `update_preferences`, `save_job`, and `list_saved_jobs`. Each tool runs in Python and accesses the application database; the model cannot execute arbitrary shell commands or SQL. With the same key, the search service can cache `text-embedding-3-small` vectors for the sample jobs and include cosine similarity in the ranking. For portability, this starter stores vectors as JSON and calculates similarity in Python; a larger deployment should use PostgreSQL + pgvector for database-side nearest-neighbor retrieval.

**Do not commit `.env` files or share API keys.** API use may incur charges according to your provider's pricing and account settings.

## Option C — Run with Docker Compose

Install Docker Desktop / Docker Engine, then from the project root run:

```bash
docker compose up --build
```

Open http://localhost:5173 for the UI and http://localhost:8000/docs for the API docs. The SQLite database is persisted in `backend/data/careerpilot.db`.

To enable the LLM in Docker, set `OPENAI_API_KEY` and optionally `OPENAI_EMBEDDING_MODEL` in your shell or create a root `.env` file with these values before running Compose. Never add the key to source control.

To stop the containers:

```bash
docker compose down
```

For a file-by-file explanation, see [`docs/PROJECT_WALKTHROUGH.md`](docs/PROJECT_WALKTHROUGH.md).

## Run the tests

From the project root:

```bash
cd backend
python -m pip install -r requirements.txt
pytest -q
```

The current test suite checks the matching score, required-skill gaps, and score bounds.

## Useful API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/jobs?q=AI&location=Bengaluru` | Search and rank sample jobs |
| GET | `/api/jobs/{job_id}` | Job details and match explanation |
| GET | `/api/profile` | Read the demo candidate profile |
| PUT | `/api/profile` | Update the candidate preferences |
| GET | `/api/saved-jobs` | List saved roles |
| POST | `/api/jobs/{job_id}/save` | Save a role |
| DELETE | `/api/jobs/{job_id}/save` | Remove a saved role |
| GET | `/api/chat/history` | Read saved conversation messages |
| POST | `/api/chat` | Send a message to CareerPilot |
| DELETE | `/api/chat/history` | Clear conversation messages |
| GET | `/api/stats` | Dashboard metrics |

## How match scoring works

The baseline scorer is deliberately simple and inspectable. It combines:

- Required-skill overlap
- Target-role relevance
- Preferred-location fit
- Work-mode fit
- Internship / entry-level fit
- A small salary fit bonus when salary is available
- Search-keyword overlap
- Optional cosine similarity from OpenAI text embeddings when a key is configured

The score is capped at 99 and should be treated as a ranking heuristic, not a calibrated likelihood. Deal-breaker phrases are filtered from job text before results are returned. Improve the scorer only after you create a labelled evaluation set and measure how it performs.

## Good next steps for a serious portfolio version

1. Add a labelled set of candidate/job relevance judgments and report Recall@10, Precision@5, and NDCG@10.
2. Compare keyword-only ranking with embedding-enhanced ranking on a labelled dataset; add PostgreSQL + pgvector for database-side vector retrieval at larger scale.
3. Add database migrations, rate limiting, structured logs, API authentication, and deployment secrets management before handling real user data.
4. Add verified job ingestion with source URLs, deduplication, and expiry checks before presenting jobs as real vacancies.
5. Add dedicated tests for tool argument validation and end-to-end user flows.

## Troubleshooting

**The UI says API disconnected**

Make sure the backend terminal is running and http://localhost:8000/api/health opens. If you changed the API port, update `VITE_API_URL` in `frontend/.env` and restart Vite.

**Port 8000 or 5173 is already in use**

Stop the other process or change the port in the relevant run command and frontend configuration.

**The assistant says demo mode**

This is expected without `OPENAI_API_KEY`. Search, saved jobs, and simple preference commands work in demo mode; a configured key enables the real LLM tool-calling path.

**I changed the seed job list but don't see the changes**

Seeding runs only when the job table is empty. For a disposable local demo, stop the backend and delete `backend/careerpilot.db`, then start it again. This resets local profiles, saved jobs, and chat history too. Do not delete a database with data you need.

## Responsible use

Use synthetic data for demos. Do not paste private CVs, phone numbers, or other sensitive information into this starter. Before production use, add authentication and per-user authorization, privacy and retention controls, observability, stronger evaluation, and verified job data sources.
