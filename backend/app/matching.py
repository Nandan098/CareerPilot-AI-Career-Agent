"""Transparent baseline matching algorithm; easy to inspect and tune."""

import re
from typing import Any


def clean(value: str) -> str:
    """Normalize text for forgiving comparisons."""
    return re.sub(r"[^a-z0-9+#. ]+", " ", value.lower()).strip()


def tokens(value: str) -> set[str]:
    """Return normalized words; lightly normalize simple plurals (APIs -> API)."""
    words = {part for part in clean(value).split() if len(part) > 1}
    return {word[:-1] if word.endswith("s") and len(word) > 3 else word for word in words}


def skill_is_present(required_skill: str, candidate_skills: list[str]) -> bool:
    """Match whole skill tokens so Java does not accidentally match JavaScript."""
    required_tokens = tokens(required_skill)
    if not required_tokens:
        return False
    return any(required_tokens.issubset(tokens(candidate_skill)) for candidate_skill in candidate_skills)


def calculate_match(job: Any, profile: Any, query: str = "", semantic_score: float | None = None) -> dict:
    """Return a heuristic match score and human-readable score reasons.

    The score is a product heuristic, not a statistically calibrated probability.
    """
    score = 0
    reasons: list[str] = []
    candidate_skills = list(profile.skills or [])
    required_skills = [clean(skill) for skill in (job.required_skills or [])]
    matching_skills = [skill for skill in required_skills if skill_is_present(skill, candidate_skills)]
    missing_skills = [skill for skill in (job.required_skills or []) if clean(skill) not in matching_skills]

    if required_skills:
        skill_points = round(45 * len(matching_skills) / len(required_skills))
        score += skill_points
        if matching_skills:
            reasons.append(f"{len(matching_skills)} of {len(required_skills)} required skills match")

    role_text = " ".join(profile.target_roles or [])
    generic_role_words = {"intern", "internship", "engineer", "engineering", "software", "entry", "level", "junior", "role"}
    role_overlap = (tokens(role_text) & tokens(job.title)) - generic_role_words
    if role_overlap:
        score += min(20, 10 + 5 * len(role_overlap))
        reasons.append("Role aligns with your target positions")

    preferred_locations = [clean(location) for location in (profile.preferred_locations or [])]
    job_location = clean(job.location)
    if any(location in job_location or location in job_location.replace(", india", "") for location in preferred_locations):
        score += 15
        reasons.append("Matches your preferred location")
    elif "remote" in job_location and any(clean(mode) == "remote" for mode in (profile.work_modes or [])):
        score += 12
        reasons.append("Remote work matches your preferences")

    if profile.work_modes and any(clean(mode) == clean(job.work_mode) for mode in profile.work_modes):
        score += 10
        reasons.append(f"Work mode matches: {job.work_mode}")

    experience = clean(profile.experience_level or "")
    if "intern" in experience and "intern" in clean(job.job_type):
        score += 10
        reasons.append("Suitable for internship experience")
    elif any(word in experience for word in ("entry", "junior", "graduate")) and any(word in clean(job.experience) for word in ("0", "1", "entry")):
        score += 7
        reasons.append("Experience level looks suitable")

    min_salary = getattr(profile, "min_salary", None)
    if min_salary:
        salary_digits = re.findall(r"\d[\d,]*", job.salary or "")
        if salary_digits:
            # Job salary range is displayed as monthly INR in this sample dataset.
            lowest = int(salary_digits[0].replace(",", ""))
            if lowest >= min_salary:
                score += 5
                reasons.append("Listed salary meets your minimum")

    if query.strip():
        query_terms = tokens(query)
        document_terms = tokens(f"{job.title} {job.company} {job.location} {job.description} {' '.join(job.required_skills or [])}")
        overlap = query_terms & document_terms
        if overlap:
            score += min(10, len(overlap) * 3)
            reasons.append("Matches your search keywords")

    if semantic_score is not None:
        # Convert cosine similarity to a modest 0–15 bonus rather than presenting it as a probability.
        semantic_points = round(max(0.0, min(1.0, (semantic_score - 0.15) / 0.65)) * 15)
        score += semantic_points
        if semantic_score >= 0.40:
            reasons.append("Semantically related to your profile and search")

    # Simple deal-breaker filters are also applied in the search service. Keep score bounded.
    return {
        "match_score": min(99, max(0, score)),
        "match_reasons": reasons[:4] or ["Potentially relevant; review the requirements"],
        "missing_skills": missing_skills[:6],
    }
