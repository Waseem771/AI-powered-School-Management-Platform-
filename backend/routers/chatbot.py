from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from functools import lru_cache
from sqlmodel import Session
from database import get_session
from routers.auth import get_current_user
from services.school_assistant_service import SchoolAssistantService

router = APIRouter(prefix="/chatbot", tags=["Policy Chatbot (RAG)"])

@lru_cache
def get_rag_service():
    from services.rag_service import rag_service
    return rag_service

class ChatAskRequest(BaseModel):
    question: str

class ChatAskResponse(BaseModel):
    answer: str
    sources: List[str]
    grounded: bool

@router.post("/ask", response_model=ChatAskResponse)
def ask_policy_bot(
    req: ChatAskRequest,
    session: Session = Depends(get_session),
    _user = Depends(get_current_user),
):
    if not req.question or not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    return SchoolAssistantService(session).answer(req.question.strip())

@router.get("/topics")
def get_bot_topics(_user = Depends(get_current_user)):
    return {
        "school": "Al-Noor Academy",
        "description": "I can answer questions regarding official school policies, examinations, fee structures, admissions, and academic calendars.",
        "topics": get_rag_service().get_known_topics()
    }
