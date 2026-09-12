from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from services.rag_service import rag_service

router = APIRouter(prefix="/chatbot", tags=["Policy Chatbot (RAG)"])

class ChatAskRequest(BaseModel):
    question: str

class ChatAskResponse(BaseModel):
    answer: str
    sources: List[str]
    grounded: bool

@router.post("/ask", response_model=ChatAskResponse)
def ask_policy_bot(req: ChatAskRequest):
    if not req.question or not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    result = rag_service.answer_query(req.question.strip())
    return result

@router.get("/topics")
def get_bot_topics():
    return {
        "school": "Al-Noor Academy",
        "description": "I can answer questions regarding official school policies, examinations, fee structures, admissions, and academic calendars.",
        "topics": rag_service.get_known_topics()
    }
