"""The two core endpoints: career recommendations and personalised roadmaps."""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.deps import get_kb, get_recommender
from backend.app.schemas import RecommendRequest, RecommendResponse, RoadmapRequest, RoadmapResponse
from ml.roadmap import build_roadmap

router = APIRouter(tags=["recommendations"])


@router.post("/recommend", response_model=RecommendResponse)
def recommend(body: RecommendRequest, rec=Depends(get_recommender), kb=Depends(get_kb)):
    """Top careers for a free-text description of the user's skills, interests and goals."""
    if body.known_skills is not None:
        unknown = [s for s in body.known_skills if s not in kb.skills]
        if unknown:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Unknown skill ids: {', '.join(unknown)}")

    result = rec.recommend(body.query, top_k=body.top_k, known_skills=body.known_skills)
    recs = result["recommendations"]
    # Hide near-zero matches so a clear case shows one confident answer, not random fillers.
    result["recommendations"] = recs[:1] + [r for r in recs[1:] if r["match"] >= body.min_match]
    return result


@router.post("/roadmap", response_model=RoadmapResponse)
def roadmap(body: RoadmapRequest, kb=Depends(get_kb)):
    """Ordered learning plan for a career, skipping skills the user already knows."""
    if body.career_id not in kb.careers:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown career '{body.career_id}'")
    unknown = [s for s in body.known_skills if s not in kb.skills]
    if unknown:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Unknown skill ids: {', '.join(unknown)}")
    return build_roadmap(body.career_id, body.known_skills, body.hours_per_week, kb=kb)
