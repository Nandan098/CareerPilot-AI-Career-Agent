"""FastAPI entry point for CareerPilot."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.agent import handle_chat
from app.config import APP_NAME, FRONTEND_ORIGIN
from app.database import Base, SessionLocal, engine, get_db
from app.models import CandidateProfile, ConversationMessage, Job, SavedJob
from app.repository import (
    DEMO_USER_ID, chat_history, get_job, get_or_create_profile, list_saved_jobs,
    remove_saved_job, save_job, search_jobs, seed_database, update_profile,
)
from app.schemas import ChatIn, ChatMessageOut, ChatOut, JobOut, ProfileIn, ProfileOut, StatsOut


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create missing tables and seed a small local demo dataset on startup."""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_database(db)
    yield


app = FastAPI(
    title=APP_NAME,
    description="A portfolio-ready AI career agent with job recommendations, preference memory, and saved jobs.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN, "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": APP_NAME}


@app.get("/api/jobs")
def get_jobs(
    q: str = Query(default="", max_length=180),
    location: str = Query(default="", max_length=120),
    work_mode: str = Query(default="", max_length=30),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    jobs = search_jobs(db, user_id=DEMO_USER_ID, query=q, location=location, work_mode=work_mode, limit=limit)
    return {"items": jobs, "total": len(jobs)}


@app.get("/api/jobs/{job_id}", response_model=JobOut)
def get_job_detail(job_id: int, db: Session = Depends(get_db)) -> dict:
    job = get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/api/profile", response_model=ProfileOut)
def get_profile(db: Session = Depends(get_db)) -> dict:
    profile = get_or_create_profile(db, DEMO_USER_ID)
    return profile_to_api_dict(profile)


@app.put("/api/profile", response_model=ProfileOut)
def put_profile(payload: ProfileIn, db: Session = Depends(get_db)) -> dict:
    profile = update_profile(db, DEMO_USER_ID, payload.model_dump())
    return profile_to_api_dict(profile)


def profile_to_api_dict(profile: CandidateProfile) -> dict:
    return {
        "name": profile.name,
        "headline": profile.headline,
        "skills": profile.skills or [],
        "target_roles": profile.target_roles or [],
        "preferred_locations": profile.preferred_locations or [],
        "work_modes": profile.work_modes or [],
        "min_salary": profile.min_salary,
        "experience_level": profile.experience_level,
        "dealbreakers": profile.dealbreakers or [],
        "notes": profile.notes or "",
        "updated_at": profile.updated_at,
    }


@app.get("/api/saved-jobs")
def get_saved_jobs(db: Session = Depends(get_db)) -> dict:
    items = list_saved_jobs(db, DEMO_USER_ID)
    return {"items": items, "total": len(items)}


@app.post("/api/jobs/{job_id}/save")
def save_job_endpoint(job_id: int, db: Session = Depends(get_db)) -> dict:
    if not save_job(db, DEMO_USER_ID, job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    return {"ok": True, "job_id": job_id, "message": "Job saved"}


@app.delete("/api/jobs/{job_id}/save")
def remove_saved_job_endpoint(job_id: int, db: Session = Depends(get_db)) -> dict:
    removed = remove_saved_job(db, DEMO_USER_ID, job_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Saved job not found")
    return {"ok": True, "job_id": job_id, "message": "Job removed from saved list"}


@app.get("/api/chat/history", response_model=list[ChatMessageOut])
def get_chat_history(db: Session = Depends(get_db)) -> list[ConversationMessage]:
    return chat_history(db, DEMO_USER_ID)


@app.post("/api/chat", response_model=ChatOut)
def chat(payload: ChatIn, db: Session = Depends(get_db)) -> ChatOut:
    # Load prior context before storing this new user message.
    previous = chat_history(db, payload.user_id, limit=12)
    previous_for_llm = [{"role": row.role, "content": row.content} for row in previous if row.role in {"user", "assistant"}]

    db.add(ConversationMessage(user_id=payload.user_id, role="user", content=payload.message))
    db.commit()

    reply, mode, tool_calls = handle_chat(db, payload.user_id, payload.message, previous_for_llm)
    db.add(ConversationMessage(user_id=payload.user_id, role="assistant", content=reply))
    db.commit()
    return ChatOut(reply=reply, mode=mode, tool_calls=tool_calls)


@app.delete("/api/chat/history")
def clear_chat_history(db: Session = Depends(get_db)) -> dict:
    db.query(ConversationMessage).filter(ConversationMessage.user_id == DEMO_USER_ID).delete()
    db.commit()
    return {"ok": True, "message": "Conversation history cleared"}


@app.get("/api/stats", response_model=StatsOut)
def get_stats(db: Session = Depends(get_db)) -> StatsOut:
    all_jobs = search_jobs(db, DEMO_USER_ID, limit=100)
    saved_total = db.scalar(select(func.count()).select_from(SavedJob).where(SavedJob.user_id == DEMO_USER_ID)) or 0
    profile = get_or_create_profile(db, DEMO_USER_ID)
    return StatsOut(
        total_jobs=db.scalar(select(func.count()).select_from(Job).where(Job.is_active.is_(True))) or 0,
        matching_jobs=sum(1 for job in all_jobs if job["match_score"] >= 55),
        saved_jobs=int(saved_total),
        skills_count=len(profile.skills or []),
    )
