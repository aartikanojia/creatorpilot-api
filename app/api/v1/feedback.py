from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class FeedbackRequest(BaseModel):
    message_id: str
    feedback: str  # "positive" or "negative"

@router.post("/", status_code=200)
async def submit_feedback(request: FeedbackRequest):
    """
    Submit user feedback for a specific message.
    Currently logs the feedback. In production, this would save to a database.
    """
    if request.feedback not in ["positive", "negative"]:
        raise HTTPException(status_code=400, detail="Invalid feedback type. Must be 'positive' or 'negative'.")

    # TODO: Save to database
    # For now, we log it to console/cloud logs
    logger.info(f"Feedback received - Message: {request.message_id}, Type: {request.feedback}")
    
    return {"success": True, "message": "Feedback received"}
