# CareerPilot: Beginner-Friendly Code Walkthrough

This guide explains how the main files connect. Read it while keeping the project open in your editor.

## 1. Start with the frontend

### `frontend/src/main.jsx`

This is the browser entry point. It imports React, mounts the `<App />` component into the `root` element in `index.html`, and imports the global CSS.

### `frontend/src/App.jsx`

This file contains the main UI and page state.

- `API_BASE` tells the browser which backend URL to call.
- `api()` wraps `fetch()`, parses JSON, and throws a useful error for failed responses.
- `INITIAL_PROFILE` is a temporary value to render while the app loads. The persisted profile comes from `GET /api/profile`.
- `useState()` stores the current page, candidate profile, job list, saved jobs, chat transcript, search filters, loading state, and notification.
- `refreshCore()` loads profile, jobs, saved jobs, and dashboard statistics from the API.
- `toggleSave()` sends `POST` or `DELETE` based on whether a job is already saved.
- `submitProfile()` converts comma-separated text into arrays and sends `PUT /api/profile`.
- `sendChat()` appends a user message, calls `POST /api/chat`, displays the reply, and refreshes the UI in case the agent changed profile preferences or saved a job.
- `OverviewPage`, `DiscoverPage`, `AgentPage`, `SavedPage`, and `ProfilePage` are the five page-level components.
- `JobCard` renders a role card; `JobModal` explains the role, match reasons, and skill gaps.

### `frontend/src/styles.css`

The CSS defines the visual theme, sidebar, dashboard cards, job cards, chat UI, profile form, modal, responsive breakpoints, and mobile navigation. The app uses ordinary CSS so you can change colors and spacing without learning a design framework first.

## 2. Understand the backend request path

A frontend request usually follows this path:

```text
User click or form submit
        ↓
api() in frontend/src/App.jsx
        ↓ HTTP JSON request
Route in backend/app/main.py
        ↓
Pydantic schema validates input
        ↓
Repository helper reads / writes SQLAlchemy models
        ↓
SQLite persists the result
        ↓
JSON response returns to the UI
```

### `backend/app/main.py`

This is the FastAPI entry point. Each `@app.get`, `@app.post`, `@app.put`, or `@app.delete` decorator registers an API route. `Depends(get_db)` gives each route a database session and closes it after the request. The lifespan function creates tables and seeds example jobs when the server starts.

### `backend/app/schemas.py`

Pydantic models describe the shape of incoming and outgoing JSON. For example, `ProfileIn` checks the candidate profile fields before the API saves them. Invalid input should fail at the API boundary instead of silently entering the database.

### `backend/app/models.py`

These SQLAlchemy classes describe the database tables:

- `Job`: a sample job listing and its required skills.
- `CandidateProfile`: the single demo user's saved preferences.
- `SavedJob`: connects the candidate to jobs they saved.
- `ConversationMessage`: stores the chat history.

### `backend/app/database.py`

This file creates the database engine and `SessionLocal`. SQLite is used by default because it is easy to run locally; `DATABASE_URL` can be changed for another SQLAlchemy-supported database.

### `backend/app/seed.py`

Contains 12 synthetic sample listings. They are example data, not real vacancies. Add or edit dictionaries here to experiment with ranking. Seeding inserts the listings only when the job table is empty.

### `backend/app/repository.py`

This is the database-access layer. It contains reusable functions to:

- Create the initial profile and seed data.
- Read/update candidate preferences.
- Filter and rank jobs.
- Save and remove jobs.
- Retrieve chat history.

API routes and agent tools use the same helpers, so the UI and chat agent behave consistently.

### `backend/app/embeddings.py`

This is an optional enhancement. When an API key is configured, it turns job descriptions and skills into embedding vectors. It stores job vectors in the SQLite JSON column so the same jobs do not need to be embedded again on every request. It embeds the combined query/profile text and compares vectors with cosine similarity. If an API request fails, the app falls back to the ordinary keyword search. This starter calculates similarity in Python; PostgreSQL + pgvector is a sensible next step for larger collections.

### `backend/app/matching.py`

`calculate_match(job, profile, query)` calculates a heuristic ranking score. It adds points for skill overlap, target-role relevance, location, work mode, experience, salary, and search keywords. It returns three fields:

- `match_score`: a number from 0 to 99 used for ordering.
- `match_reasons`: short phrases explaining the score.
- `missing_skills`: required skills not found in the profile.
- `semantic_similarity`: optional cosine similarity when embeddings are enabled.

This is intentionally a heuristic scorer, not a trained ranking model. You can replace or extend it later, then compare its results on a labelled evaluation set.

### `backend/app/agent.py`

This file contains the assistant instructions, the tool schema, and the tool execution loop.

1. If `OPENAI_API_KEY` is configured, the OpenAI SDK receives the latest user message, a short conversation history, and the allowed tool definitions.
2. When the model requests a tool, the backend checks the requested function name and calls the corresponding Python function.
3. The tool result is appended to the model conversation so the model can explain what happened.
4. The loop has a maximum number of rounds to avoid an accidental endless cycle.
5. If no key is configured—or the external service is unavailable—the deterministic demo agent handles basic queries without an external API call.

Tools are explicitly allow-listed: `search_jobs`, `update_preferences`, `save_job`, and `list_saved_jobs`. Never run arbitrary code or raw SQL based directly on model-generated text.

### `backend/app/config.py`

Reads the database URL, OpenAI key, model name, and frontend origin from environment variables. The `.env` file is for local development; do not commit it.

## 3. Follow one user journey

Example: a user asks `Find AI internships in Bengaluru`.

1. The chat form in `AgentPage` submits the text.
2. `sendChat()` sends a JSON body to `/api/chat`.
3. `main.py` stores the user message and calls `handle_chat()`.
4. In OpenAI mode, the model can request `search_jobs`. In demo mode, a small rule-based handler makes the search directly.
5. The repository gets the user's profile and searches the sample jobs.
6. `calculate_match()` assigns a score and explanations to each result.
7. The assistant returns a summary to the UI.
8. The frontend refreshes the job list and profile data.

## 4. How to learn this code in order

1. Open `seed.py` and understand the job fields.
2. Read `models.py` and see how those fields become database columns.
3. Read `matching.py` and manually calculate why a sample job scores well.
4. Read `repository.py` to see database queries and saved-job operations.
5. Read `main.py` and trace the `/api/jobs` route.
6. Read `agent.py` to understand the difference between a tool schema and the Python function that actually executes it.
7. Open the React `JobCard` component, then trace how its Save button calls `toggleSave()` and `POST /api/jobs/{id}/save`.
8. Change one feature and run the tests before adding another feature.

## 5. Important limitations to be honest about in an interview

- The starter catalogue is synthetic and small; it does not contain live job postings.
- The default matcher is a transparent heuristic, not a trained ranking model. Optional semantic scoring uses an API-based embedding model; no-key mode remains lexical and rule based.
- Offline assistant mode supports a few explicit patterns; full natural-language tool selection requires a configured model API.
- The starter uses a single demo profile and does not include authentication. It is not ready for real users or sensitive CV data.
- The tests cover core matching behavior, not every API path or production-scale behavior.

These are valid next steps to discuss. It is better to explain the implemented scope clearly than to claim features that are not present.
