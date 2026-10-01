"""Browse the knowledge base: careers and skills."""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.deps import get_kb
from backend.app.schemas import CareerDetail, CareerSummary, SkillSummary
from ml.kb import STAGES

router = APIRouter(tags=["catalog"])


def _summary(career, kb):
    skill_ids = kb.required_skills(career["id"])
    return {
        "id": career["id"],
        "name": career["name"],
        "category": career["category"],
        "description": career["description"],
        "demand": career["demand"],
        "salary_inr_lpa": career["salary_inr_lpa"],
        "skill_count": len(skill_ids),
        "total_hours": sum(kb.skills[s]["est_hours"] for s in skill_ids),
    }


@router.get("/careers", response_model=list[CareerSummary])
def list_careers(kb=Depends(get_kb)):
    return [_summary(c, kb) for c in kb.careers.values()]


@router.get("/careers/{career_id}", response_model=CareerDetail)
def get_career(career_id: str, kb=Depends(get_kb)):
    career = kb.careers.get(career_id)
    if career is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown career '{career_id}'")
    skill = lambda sid: kb.skills[sid]
    return {
        **_summary(career, kb),
        "interests": career["interests"],
        "stages": {stage: [{"id": s, "name": skill(s)["name"], "est_hours": skill(s)["est_hours"]}
                           for s in career["stages"][stage]] for stage in STAGES},
        "optional_skills": [{"skill_id": s, "name": skill(s)["name"]} for s in career.get("optional_skills", [])],
    }


@router.get("/skills", response_model=list[SkillSummary])
def list_skills(kb=Depends(get_kb)):
    """All skills, for the skill-chip picker."""
    return sorted(({"id": s["id"], "name": s["name"], "category": s["category"]} for s in kb.skills.values()),
                  key=lambda s: s["name"].lower())
