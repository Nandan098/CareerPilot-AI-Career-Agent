"""Request and response schemas. Pydantic validates data at the API boundary."""

from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    company: str
    location: str
    work_mode: str
    job_type: str
    experience: str
    salary: str
    description: str
    required_skills: list[str]
    nice_to_have: list[str]
    responsibilities: list[str]
    source_url: str
    match_score: int = 0
    semantic_similarity: float | None = None
    match_reasons: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)


class ProfileIn(BaseModel):
    name: str = Field(default="Alex Morgan", min_length=1, max_length=120)
    headline: str = Field(default="Computer Science student", max_length=180)
    skills: list[str] = Field(default_factory=list, max_length=80)
    target_roles: list[str] = Field(default_factory=list, max_length=20)
    preferred_locations: list[str] = Field(default_factory=list, max_length=20)
    work_modes: list[str] = Field(default_factory=lambda: ["Remote", "Hybrid"], max_length=5)
    min_salary: int | None = Field(default=None, ge=0, le=100000000)
    experience_level: str = Field(default="Internship / Entry-level", max_length=80)
    dealbreakers: list[str] = Field(default_factory=list, max_length=30)
    notes: str = Field(default="", max_length=2000)


class ProfileOut(ProfileIn):
    updated_at: datetime | None = None


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    user_id: str = Field(default="demo-user", min_length=1, max_length=80)


class ChatOut(BaseModel):
    reply: str
    mode: str
    tool_calls: list[str] = Field(default_factory=list)


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    created_at: datetime


class StatsOut(BaseModel):
    total_jobs: int
    matching_jobs: int
    saved_jobs: int
    skills_count: int
