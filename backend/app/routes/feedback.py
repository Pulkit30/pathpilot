"""👍/👎 feedback on recommendations. Works logged in or not; ml/retrain.py learns from it."""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.deps import get_kb, get_optional_user, get_recommender, get_store
from backend.app.schemas import FeedbackRequest, FeedbackResponse

router = APIRouter(tags=["feedback"])


@router.post("/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def give_feedback(body: FeedbackRequest, user=Depends(get_optional_user), store=Depends(get_store),
                        kb=Depends(get_kb), rec=Depends(get_recommender)):
    if body.career_id not in kb.careers:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown career '{body.career_id}'")
    saved = await store.add_feedback({
        "user_id": user["id"] if user else None,
        "query": body.query.strip(),
        "career_id": body.career_id,
        "rating": body.rating,
        "rank": body.rank,
        "model_version": rec.trained_at,  # which model produced the recommendation
    })
    return {"id": saved["id"]}
