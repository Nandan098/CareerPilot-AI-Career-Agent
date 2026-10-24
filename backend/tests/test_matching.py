"""Small fast tests for the transparent matching algorithm."""

from types import SimpleNamespace

from app.matching import calculate_match


def test_matching_skills_increase_score_and_explain_match():
    job = SimpleNamespace(
        title="AI Engineering Intern", description="Build LLM-powered APIs.",
        required_skills=["Python", "LLMs", "SQL"], nice_to_have=["RAG"],
        location="Bengaluru, India", work_mode="Hybrid", job_type="Internship",
        experience="0–1 years", salary="₹50,000–₹80,000/month",
    )
    profile = SimpleNamespace(
        skills=["Python", "LLMs", "SQL"], target_roles=["AI Engineer Intern"],
        preferred_locations=["Bengaluru"], work_modes=["Hybrid"], min_salary=30000,
        experience_level="Internship / Entry-level",
    )
    result = calculate_match(job, profile)
    assert result["match_score"] > 50
    assert len(result["match_reasons"]) >= 3
    assert result["missing_skills"] == []


def test_missing_skills_are_reported():
    job = SimpleNamespace(
        title="Search Intern", description="Build retrieval systems.",
        required_skills=["Python", "Embeddings", "BM25"], nice_to_have=[],
        location="Remote, India", work_mode="Remote", job_type="Internship",
        experience="0–1 years", salary="₹50,000/month",
    )
    profile = SimpleNamespace(
        skills=["Python"], target_roles=["Search Intern"], preferred_locations=[],
        work_modes=["Remote"], min_salary=None, experience_level="Internship",
    )
    result = calculate_match(job, profile)
    assert "Embeddings" in result["missing_skills"]
    assert "BM25" in result["missing_skills"]


def test_score_is_bounded():
    job = SimpleNamespace(
        title="Python FastAPI Intern", description="Python FastAPI SQL LLMs.",
        required_skills=["Python", "FastAPI"], nice_to_have=[], location="Remote, India",
        work_mode="Remote", job_type="Internship", experience="0–1 years", salary="₹70,000/month",
    )
    profile = SimpleNamespace(
        skills=["Python", "FastAPI"], target_roles=["Python FastAPI Intern"], preferred_locations=["Remote"],
        work_modes=["Remote"], min_salary=10000, experience_level="Internship",
    )
    score = calculate_match(job, profile)["match_score"]
    assert 0 <= score <= 99


def test_java_does_not_match_javascript():
    job = SimpleNamespace(
        title="Frontend Intern", description="Build web interfaces.",
        required_skills=["JavaScript"], nice_to_have=[], location="Remote, India",
        work_mode="Remote", job_type="Internship", experience="0–1 years", salary="Not specified",
    )
    profile = SimpleNamespace(
        skills=["Java"], target_roles=["Frontend Intern"], preferred_locations=[],
        work_modes=["Remote"], min_salary=None, experience_level="Internship",
    )
    result = calculate_match(job, profile)
    assert result["missing_skills"] == ["JavaScript"]
