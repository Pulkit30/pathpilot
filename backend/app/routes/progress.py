"""Saved roadmaps and progress tracking (login required)."""

import math

from fastapi import APIRouter, Depends, HTTPException, Response, status

from backend.app.deps import get_current_user, get_kb, get_store
from backend.app.schemas import SavedRoadmapDetail, SavedRoadmapSummary, SaveRoadmapRequest, SkillDoneRequest
from ml.roadmap import build_roadmap

router = APIRouter(prefix="/roadmaps", tags=["my roadmaps"])


def _check_ids(kb, career_id, skill_ids=()):
    if career_id not in kb.careers:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown career '{career_id}'")
    unknown = [s for s in skill_ids if s not in kb.skills]
    if unknown:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Unknown skill ids: {', '.join(unknown)}")


def _with_progress(saved, kb, include_roadmap=False):
    """Combine a saved roadmap with its freshly built plan and progress numbers."""
    roadmap = build_roadmap(saved["career_id"], saved["known_skills"], saved["hours_per_week"], kb=kb)
    step_ids = [s["skill_id"] for s in roadmap["steps"]]
    done = [s for s in step_ids if s in saved["completed_skills"]]
    hours_left = sum(s["est_hours"] for s in roadmap["steps"] if s["skill_id"] not in done)
    required = len(kb.required_skills(saved["career_id"]))
    result = {
        "career_id": saved["career_id"],
        "career_name": roadmap["career_name"],
        "known_skills": saved["known_skills"],
        "hours_per_week": saved["hours_per_week"],
        "steps_total": len(step_ids),
        "steps_done": len(done),
        "progress": round((len(roadmap["already_known"]) + len(done)) / required, 3) if required else 1.0,
        "hours_left": hours_left,
        "weeks_left": math.ceil(hours_left / saved["hours_per_week"]),
        "updated_at": saved["updated_at"],
    }
    if include_roadmap:
        result["completed_skills"] = done
        result["roadmap"] = roadmap
    return result


@router.get("", response_model=list[SavedRoadmapSummary])
async def list_saved(user=Depends(get_current_user), store=Depends(get_store), kb=Depends(get_kb)):
    """All roadmaps the user has saved, most recently updated first."""
    return [_with_progress(r, kb) for r in await store.list_roadmaps(user["id"]) if r["career_id"] in kb.careers]


@router.post("", response_model=SavedRoadmapDetail)
async def save(body: SaveRoadmapRequest, user=Depends(get_current_user), store=Depends(get_store),
               kb=Depends(get_kb)):
    """Save a roadmap, or update the known skills / weekly hours of one already saved.
    Skills already marked as done are kept."""
    _check_ids(kb, body.career_id, body.known_skills)
    saved = await store.save_roadmap(user["id"], body.career_id, body.known_skills, body.hours_per_week)
    return _with_progress(saved, kb, include_roadmap=True)


@router.get("/{career_id}", response_model=SavedRoadmapDetail)
async def get_saved(career_id: str, user=Depends(get_current_user), store=Depends(get_store),
                    kb=Depends(get_kb)):
    saved = await store.get_roadmap(user["id"], career_id)
    if saved is None or career_id not in kb.careers:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "You haven't saved this roadmap")
    return _with_progress(saved, kb, include_roadmap=True)


@router.put("/{career_id}/skills/{skill_id}", response_model=SavedRoadmapDetail)
async def mark_skill(career_id: str, skill_id: str, body: SkillDoneRequest, user=Depends(get_current_user),
                     store=Depends(get_store), kb=Depends(get_kb)):
    """Mark one roadmap step as done (or not done)."""
    saved = await store.get_roadmap(user["id"], career_id)
    if saved is None or career_id not in kb.careers:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "You haven't saved this roadmap")
    steps = build_roadmap(career_id, saved["known_skills"], saved["hours_per_week"], kb=kb)["steps"]
    if skill_id not in {s["skill_id"] for s in steps}:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"'{skill_id}' is not a step in this roadmap")
    saved = await store.set_skill_done(user["id"], career_id, skill_id, body.done)
    return _with_progress(saved, kb, include_roadmap=True)


@router.delete("/{career_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(career_id: str, user=Depends(get_current_user), store=Depends(get_store)):
    if not await store.delete_roadmap(user["id"], career_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "You haven't saved this roadmap")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
