"""Optional OpenAI embedding helpers used to upgrade search to hybrid retrieval.

The default app stays fully usable without an API key. When embeddings are enabled,
job vectors are cached in the database and cosine similarity contributes to ranking.
For this small SQLite starter, similarity is calculated in Python; pgvector can be
introduced later for large collections and database-side nearest-neighbor queries.
"""

import math
from typing import Any

try:
    from openai import OpenAI
except ImportError:  # Search falls back to lexical matching without the SDK.
    OpenAI = None  # type: ignore[assignment,misc]

from sqlalchemy.orm import Session

from app.config import OPENAI_API_KEY, OPENAI_EMBEDDING_MODEL
from app.models import CandidateProfile, Job


def embeddings_enabled() -> bool:
    return bool(OPENAI_API_KEY and OpenAI is not None)


def job_embedding_text(job: Job) -> str:
    """Create a consistent document containing useful job-searchable fields."""
    return "\n".join([
        f"Job title: {job.title}",
        f"Company: {job.company}",
        f"Location: {job.location}",
        f"Work mode: {job.work_mode}",
        f"Experience: {job.experience}",
        f"Description: {job.description}",
        f"Required skills: {', '.join(job.required_skills or [])}",
        f"Nice-to-have skills: {', '.join(job.nice_to_have or [])}",
    ])


def profile_query_text(profile: CandidateProfile, query: str = "") -> str:
    """Combine the current request with stored preferences for personalized search."""
    parts = [
        f"User's job-search request: {query}" if query.strip() else "Find jobs aligned with the candidate profile.",
        f"Target roles: {', '.join(profile.target_roles or [])}",
        f"Skills and experience: {', '.join(profile.skills or [])}",
        f"Preferred locations: {', '.join(profile.preferred_locations or [])}",
        f"Preferred work modes: {', '.join(profile.work_modes or [])}",
        f"Additional context: {profile.notes or ''}",
    ]
    return "\n".join(parts)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed text in one API batch and return vectors in original input order."""
    if not embeddings_enabled() or not texts:
        return []
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.embeddings.create(model=OPENAI_EMBEDDING_MODEL, input=texts)
    ordered = sorted(response.data, key=lambda item: item.index)
    return [list(item.embedding) for item in ordered]


def ensure_job_embeddings(db: Session, jobs: list[Job]) -> bool:
    """Cache missing job vectors once. False means callers should use lexical search."""
    if not embeddings_enabled():
        return False
    missing = [job for job in jobs if not job.embedding]
    if not missing:
        return True
    try:
        vectors = embed_texts([job_embedding_text(job) for job in missing])
        if len(vectors) != len(missing):
            return False
        for job, vector in zip(missing, vectors):
            job.embedding = vector
        db.commit()
        return True
    except Exception:
        # Never make basic job search unavailable because an optional embedding call failed.
        db.rollback()
        return False


def cosine_similarity(left: list[float], right: list[float]) -> float:
    """Cosine similarity with a guard for empty vectors and zero-magnitude vectors."""
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def score_jobs_by_embedding(profile: CandidateProfile, jobs: list[Job], query: str = "") -> dict[int, float] | None:
    """Return cosine similarities by job ID, or None when semantic search is unavailable."""
    if not embeddings_enabled() or not jobs or any(not job.embedding for job in jobs):
        return None
    try:
        query_vector = embed_texts([profile_query_text(profile, query)])[0]
        return {job.id: cosine_similarity(query_vector, list(job.embedding)) for job in jobs}
    except Exception:
        return None
