"""Database helpers shared by the API and the agent tools."""

from sqlalchemy import select, func
from sqlalchemy.orm import Session, joinedload

from app.embeddings import ensure_job_embeddings, score_jobs_by_embedding
from app.matching import calculate_match, clean, tokens
from app.models import CandidateProfile, ConversationMessage, Job, SavedJob
from app.schemas import ProfileIn
from app.seed import JOBS

DEMO_USER_ID = "demo-user"


def seed_database(db: Session) -> None:
    """Insert demo jobs and the first sample profile on an empty database."""
    if db.scalar(select(func.count()).select_from(Job)) == 0:
        db.add_all(Job(**job_data) for job_data in JOBS)
    if db.get(CandidateProfile, DEMO_USER_ID) is None:
        db.add(CandidateProfile(
            user_id=DEMO_USER_ID,
            name="Alex Morgan",
            headline="CS student building AI-powered products",
            skills=["Python", "FastAPI", "SQL", "REST APIs", "LLMs", "React"],
            target_roles=["AI Engineer Intern", "Software Engineer Intern", "Backend Engineer Intern"],
            preferred_locations=["Bengaluru", "Gurugram"],
            work_modes=["Remote", "Hybrid"],
            min_salary=30000,
            experience_level="Internship / Entry-level",
            dealbreakers=[],
            notes="Interested in early-stage product teams and practical AI engineering.",
        ))
    db.commit()


def get_or_create_profile(db: Session, user_id: str = DEMO_USER_ID) -> CandidateProfile:
    profile = db.get(CandidateProfile, user_id)
    if profile is None:
        profile = CandidateProfile(user_id=user_id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def update_profile(db: Session, user_id: str, values: dict) -> CandidateProfile:
    profile = get_or_create_profile(db, user_id)
    allowed = set(ProfileIn.model_fields.keys())
    for key, value in values.items():
        if key in allowed:
            setattr(profile, key, value)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def _job_matches_query(job: Job, query: str) -> bool:
    query_tokens = tokens(query)
    if not query_tokens:
        return True
    text_tokens = tokens(
        f"{job.title} {job.company} {job.location} {job.work_mode} {job.job_type} "
        f"{job.description} {' '.join(job.required_skills or [])} {' '.join(job.nice_to_have or [])}"
    )
    # Require at least one meaningful term. Ranking decides ordering among matches.
    return bool(query_tokens & text_tokens)


def _passes_dealbreakers(job: Job, profile: CandidateProfile) -> bool:
    all_text = clean(f"{job.title} {job.company} {job.location} {job.work_mode} {job.job_type} {job.description}")
    for item in profile.dealbreakers or []:
        phrase = clean(item)
        if phrase and phrase in all_text:
            return False
    return True


def job_to_dict(job: Job, profile: CandidateProfile, query: str = "", semantic_score: float | None = None) -> dict:
    data = {
        "id": job.id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "work_mode": job.work_mode,
        "job_type": job.job_type,
        "experience": job.experience,
        "salary": job.salary,
        "description": job.description,
        "required_skills": job.required_skills or [],
        "nice_to_have": job.nice_to_have or [],
        "responsibilities": job.responsibilities or [],
        "source_url": job.source_url,
    }
    data.update(calculate_match(job, profile, query, semantic_score=semantic_score))
    if semantic_score is not None:
        data["semantic_similarity"] = round(float(semantic_score), 4)
    return data


def search_jobs(
    db: Session,
    user_id: str = DEMO_USER_ID,
    query: str = "",
    location: str = "",
    work_mode: str = "",
    limit: int = 50,
) -> list[dict]:
    profile = get_or_create_profile(db, user_id)
    jobs = list(db.scalars(select(Job).where(Job.is_active.is_(True))).all())
    semantic_scores = None
    if ensure_job_embeddings(db, jobs):
        semantic_scores = score_jobs_by_embedding(profile, jobs, query)
    result = []
    for job in jobs:
        # When embeddings are available, semantic ranking can find matches without exact keywords.
        if semantic_scores is None and not _job_matches_query(job, query):
            continue
        if location and clean(location) not in clean(job.location):
            continue
        if work_mode and clean(work_mode) != clean(job.work_mode):
            continue
        if not _passes_dealbreakers(job, profile):
            continue
        result.append(job_to_dict(job, profile, query, semantic_scores.get(job.id) if semantic_scores is not None else None))
    result.sort(key=lambda item: (item["match_score"], item.get("semantic_similarity", 0.0), item["title"]), reverse=True)
    return result[:max(1, min(limit, 100))]


def get_job(db: Session, job_id: int, user_id: str = DEMO_USER_ID) -> dict | None:
    job = db.get(Job, job_id)
    if not job:
        return None
    profile = get_or_create_profile(db, user_id)
    return job_to_dict(job, profile)


def save_job(db: Session, user_id: str, job_id: int) -> bool:
    if db.get(Job, job_id) is None:
        return False
    get_or_create_profile(db, user_id)
    existing = db.scalar(select(SavedJob).where(SavedJob.user_id == user_id, SavedJob.job_id == job_id))
    if existing is None:
        db.add(SavedJob(user_id=user_id, job_id=job_id))
        db.commit()
    return True


def remove_saved_job(db: Session, user_id: str, job_id: int) -> bool:
    saved = db.scalar(select(SavedJob).where(SavedJob.user_id == user_id, SavedJob.job_id == job_id))
    if saved is None:
        return False
    db.delete(saved)
    db.commit()
    return True


def list_saved_jobs(db: Session, user_id: str = DEMO_USER_ID) -> list[dict]:
    profile = get_or_create_profile(db, user_id)
    rows = db.scalars(
        select(SavedJob).options(joinedload(SavedJob.job))
        .where(SavedJob.user_id == user_id).order_by(SavedJob.created_at.desc())
    ).all()
    return [job_to_dict(row.job, profile) for row in rows if row.job is not None]


def chat_history(db: Session, user_id: str, limit: int = 60) -> list[ConversationMessage]:
    rows = db.scalars(
        select(ConversationMessage).where(ConversationMessage.user_id == user_id)
        .order_by(ConversationMessage.created_at.desc()).limit(limit)
    ).all()
    return list(reversed(rows))
