"""Tool-using LLM agent with a deterministic no-key demo fallback."""

import json
import re
from typing import Any

try:
    from openai import OpenAI
except ImportError:  # The offline demo does not need the OpenAI SDK.
    OpenAI = None  # type: ignore[assignment,misc]

from sqlalchemy.orm import Session

from app.config import OPENAI_API_KEY, OPENAI_MODEL
from app.models import CandidateProfile
from app.repository import (
    DEMO_USER_ID, get_or_create_profile, list_saved_jobs,
    search_jobs as find_jobs, save_job, update_profile,
)

TOOLS = [
    {
        "type": "function", "function": {
            "name": "search_jobs",
            "description": "Search the curated demo job index and rank jobs for the user's stored preferences.",
            "parameters": {
                "type": "object", "properties": {
                    "query": {"type": "string", "description": "Keywords or role description to search for."},
                    "location": {"type": "string", "description": "Optional location filter, such as Bengaluru."},
                    "work_mode": {"type": "string", "enum": ["Remote", "Hybrid", "On-site"], "description": "Optional work-mode filter."},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 8},
                }, "required": [], "additionalProperties": False,
            },
        }
    },
    {
        "type": "function", "function": {
            "name": "update_preferences",
            "description": "Update the candidate profile after the user explicitly shares new preferences or skills.",
            "parameters": {
                "type": "object", "properties": {
                    "skills": {"type": "array", "items": {"type": "string"}},
                    "target_roles": {"type": "array", "items": {"type": "string"}},
                    "preferred_locations": {"type": "array", "items": {"type": "string"}},
                    "work_modes": {"type": "array", "items": {"type": "string", "enum": ["Remote", "Hybrid", "On-site"]}},
                    "min_salary": {"type": ["integer", "null"], "minimum": 0},
                    "dealbreakers": {"type": "array", "items": {"type": "string"}},
                    "notes": {"type": "string"},
                }, "required": [], "additionalProperties": False,
            },
        }
    },
    {
        "type": "function", "function": {
            "name": "save_job",
            "description": "Save a job to the candidate's saved list.",
            "parameters": {"type": "object", "properties": {"job_id": {"type": "integer"}}, "required": ["job_id"], "additionalProperties": False},
        }
    },
    {
        "type": "function", "function": {
            "name": "list_saved_jobs",
            "description": "List jobs already saved by the candidate.",
            "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        }
    },
]

SYSTEM_PROMPT = """You are CareerPilot, a transparent AI career assistant for students and early-career candidates.
Use tools for job searches, saved-job actions, and profile updates. Do not claim a job is currently open at a real company: the app uses a small synthetic demo dataset, not live vacancies. Clearly distinguish a heuristic match score from a probability. Explain missing skills constructively and never invent candidate experience, qualifications, or job facts. Ask a concise follow-up when a critical requirement is unclear. When you update preferences, summarize exactly what changed. Prefer concise, practical advice."""


def _execute_tool(name: str, args: dict[str, Any], db: Session, user_id: str) -> dict:
    """Allow-list function that maps LLM requests to known backend actions."""
    if name == "search_jobs":
        items = find_jobs(
            db, user_id=user_id, query=args.get("query", ""), location=args.get("location", ""),
            work_mode=args.get("work_mode", ""), limit=args.get("limit", 5),
        )
        return {"count": len(items), "jobs": items}
    if name == "update_preferences":
        if not args:
            return {"ok": False, "message": "No preference changes were provided."}
        updated = update_profile(db, user_id, args)
        return {"ok": True, "updated_fields": list(args.keys()), "profile": profile_to_dict(updated)}
    if name == "save_job":
        job_id = int(args["job_id"])
        ok = save_job(db, user_id, job_id)
        return {"ok": ok, "message": "Job saved." if ok else "Job ID was not found in the demo dataset."}
    if name == "list_saved_jobs":
        items = list_saved_jobs(db, user_id)
        return {"count": len(items), "jobs": items}
    return {"ok": False, "message": "This tool is not available."}


def profile_to_dict(profile: CandidateProfile) -> dict:
    return {
        "name": profile.name, "headline": profile.headline, "skills": profile.skills or [],
        "target_roles": profile.target_roles or [], "preferred_locations": profile.preferred_locations or [],
        "work_modes": profile.work_modes or [], "min_salary": profile.min_salary,
        "experience_level": profile.experience_level, "dealbreakers": profile.dealbreakers or [], "notes": profile.notes or "",
    }


def run_openai_agent(db: Session, user_id: str, message: str, previous_messages: list[dict]) -> tuple[str, list[str]]:
    """Run at most four tool rounds to avoid accidental infinite tool loops."""
    if OpenAI is None:
        raise RuntimeError("OpenAI SDK is not installed. Run pip install -r requirements.txt.")
    client = OpenAI(api_key=OPENAI_API_KEY)
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(previous_messages[-10:])
    messages.append({"role": "user", "content": message})
    called: list[str] = []

    for _ in range(5):
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.2,
        )
        assistant_message = response.choices[0].message
        if not assistant_message.tool_calls:
            return (assistant_message.content or "I couldn't form a response. Try rephrasing your request."), called

        messages.append(assistant_message.model_dump(exclude_none=True))
        for call in assistant_message.tool_calls:
            called.append(call.function.name)
            try:
                arguments = json.loads(call.function.arguments or "{}")
                result = _execute_tool(call.function.name, arguments, db, user_id)
            except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
                result = {"ok": False, "message": f"Tool arguments were invalid: {exc}"}
            messages.append({
                "role": "tool", "tool_call_id": call.id,
                "content": json.dumps(result, ensure_ascii=False),
            })
    return "I completed the available actions, but reached the tool-call limit. Please check your saved jobs or preferences.", called


def _apply_simple_demo_updates(db: Session, user_id: str, message: str) -> list[str]:
    """Handle a few obvious preference requests when no API key is configured."""
    text = message.lower()
    changes: dict[str, Any] = {}
    if "remote only" in text or "only remote" in text or "remote jobs only" in text:
        changes["work_modes"] = ["Remote"]
    elif "hybrid only" in text or "only hybrid" in text:
        changes["work_modes"] = ["Hybrid"]
    elif "on-site only" in text or "onsite only" in text:
        changes["work_modes"] = ["On-site"]
    elif "remote and hybrid" in text:
        changes["work_modes"] = ["Remote", "Hybrid"]

    known_locations = ["Bengaluru", "Gurugram", "Pune", "Hyderabad", "Remote"]
    if any(word in text for word in ("prefer", "location", "based in", "move to", "relocate", "set my location")):
        locations = [place for place in known_locations if place.lower() in text]
        if locations:
            changes["preferred_locations"] = locations

    skills_match = re.search(r"(?:my skills are|my skills:|skills include)\s*(.+)", message, re.IGNORECASE)
    if skills_match:
        parsed = [item.strip(" .") for item in re.split(r",| and ", skills_match.group(1)) if item.strip()]
        if parsed:
            changes["skills"] = parsed[:30]

    if changes:
        update_profile(db, user_id, changes)
    return list(changes.keys())


def run_demo_agent(db: Session, user_id: str, message: str) -> tuple[str, list[str]]:
    """Rule-based offline experience so the project runs without a paid API key."""
    text = message.strip()
    lowered = text.lower()
    called: list[str] = []
    changed = _apply_simple_demo_updates(db, user_id, text)
    if changed:
        profile = get_or_create_profile(db, user_id)
        return f"Preference memory updated: {', '.join(changed)}. I'll use those settings in future recommendations. You can review or change them in My Profile.", ["update_preferences"]

    save_match = re.search(r"\b(?:save|bookmark)\s+(?:job\s*)?#?(\d+)\b", lowered)
    if save_match:
        job_id = int(save_match.group(1))
        ok = save_job(db, user_id, job_id)
        called.append("save_job")
        return (f"Saved job #{job_id} to your list." if ok else f"I couldn't find job #{job_id}. Try a job ID shown on a card."), called

    if any(word in lowered for word in ("saved jobs", "show saved", "my saved", "bookmarked")):
        jobs = list_saved_jobs(db, user_id)
        called.append("list_saved_jobs")
        if not jobs:
            return "You have no saved jobs yet. Use the Save button on a job card or ask me to save a job by its ID.", called
        lines = [f"• **{job['title']}** at {job['company']} (job #{job['id']})" for job in jobs[:8]]
        return "Here are your saved jobs:\n" + "\n".join(lines), called

    query = ""
    if any(word in lowered for word in ("find", "search", "recommend", "show", "jobs", "internship", "role", "opportunities")):
        query = re.sub(r"\b(find|search|recommend|show me|show|jobs for|jobs|internship|opportunities|please|can you)\b", " ", text, flags=re.IGNORECASE).strip()
    location = ""
    for place in ["Bengaluru", "Gurugram", "Pune", "Hyderabad"]:
        if place.lower() in lowered:
            location = place
            break
    work_mode = "Remote" if "remote" in lowered else ("Hybrid" if "hybrid" in lowered else ("On-site" if "on-site" in lowered or "onsite" in lowered else ""))
    jobs = find_jobs(db, user_id=user_id, query=query, location=location, work_mode=work_mode, limit=5)
    called.append("search_jobs")
    if jobs:
        lines = []
        for job in jobs[:4]:
            reasons = ", ".join(job["match_reasons"][:2])
            lines.append(f"• **{job['title']}** at {job['company']} — {job['match_score']}% heuristic match (job #{job['id']}). {reasons}.")
        return "Here are a few matches from the sample job catalogue:\n\n" + "\n".join(lines) + "\n\nThese are synthetic demo listings, not verified live vacancies. Ask me to save a job by its ID, or say 'remote only' to update your remembered preferences.", called
    return "I’m running in demo mode because no OpenAI API key is configured. I can search the sample job catalogue, show saved jobs, and remember simple preferences like 'remote only' or 'my skills are Python, FastAPI'. Try: 'Find AI internships in Bengaluru'.", called


def handle_chat(db: Session, user_id: str, message: str, previous_messages: list[dict]) -> tuple[str, str, list[str]]:
    """Choose the real LLM agent when configured, otherwise use the offline demo."""
    if OPENAI_API_KEY:
        try:
            reply, tool_calls = run_openai_agent(db, user_id, message, previous_messages)
            return reply, "openai", tool_calls
        except Exception:
            # Keep the app usable even if the API is temporarily unavailable.
            reply, tool_calls = run_demo_agent(db, user_id, message)
            return "The LLM service could not be reached, so I used demo mode for this reply.\n\n" + reply, "demo-fallback", tool_calls
    reply, tool_calls = run_demo_agent(db, user_id, message)
    return reply, "demo", tool_calls
