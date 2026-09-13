from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from functools import lru_cache
import uuid
import time
from sqlmodel import Session
from database import get_session
from routers.auth import get_current_user
from services.school_assistant_service import SchoolAssistantService

router = APIRouter(prefix="/chatbot", tags=["AI School Assistant"])

# In-memory conversational session store:
# session_id -> list of {"role": "user" | "assistant", "content": str, "timestamp": float}
chat_memory: Dict[str, List[Dict[str, Any]]] = {}


@lru_cache
def get_rag_service():
    from services.rag_service import rag_service
    return rag_service


class ChatAskRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    history: Optional[List[Dict[str, Any]]] = None
    use_memory: Optional[bool] = True


class ChatAskResponse(BaseModel):
    answer: str
    sources: List[str]
    grounded: bool
    mode: Optional[str] = None
    tools_used: Optional[List[str]] = None
    structured_data: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    history_length: Optional[int] = 0
    memory_active: Optional[bool] = True


@router.post("/ask", response_model=ChatAskResponse)
def ask_school_assistant(
    req: ChatAskRequest,
    session: Session = Depends(get_session),
    _user=Depends(get_current_user),
):
    question = (req.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    use_memory = req.use_memory if req.use_memory is not None else True
    session_id = req.session_id or str(uuid.uuid4())

    # Build conversation history for memory
    conversation_history: List[Dict[str, Any]] = []

    if use_memory:
        # Retrieve server-side session memory if available
        if session_id in chat_memory:
            conversation_history = list(chat_memory[session_id])

        # If client passed additional history, merge and deduplicate
        if req.history:
            for item in req.history:
                if item.get("role") in ("user", "assistant") and item.get("content"):
                    if not any(
                        h.get("role") == item.get("role") and h.get("content") == item.get("content")
                        for h in conversation_history
                    ):
                        conversation_history.append({
                            "role": item["role"],
                            "content": str(item["content"]),
                            "timestamp": time.time(),
                        })

    # Execute SchoolAssistantService with full conversational memory
    result = SchoolAssistantService(session).answer(question, history=conversation_history)

    # Save current turn into session memory
    if use_memory:
        if session_id not in chat_memory:
            chat_memory[session_id] = []

        chat_memory[session_id].append({
            "role": "user",
            "content": question,
            "timestamp": time.time(),
        })
        chat_memory[session_id].append({
            "role": "assistant",
            "content": result.get("answer", ""),
            "timestamp": time.time(),
        })
        # Keep maximum last 40 messages per session to prevent unbounded memory growth
        if len(chat_memory[session_id]) > 40:
            chat_memory[session_id] = chat_memory[session_id][-40:]

    history_len = len(chat_memory.get(session_id, [])) if use_memory else 0

    return {
        "answer": result.get("answer", ""),
        "sources": result.get("sources", []),
        "grounded": result.get("grounded", False),
        "mode": result.get("mode"),
        "tools_used": result.get("tools_used"),
        "structured_data": result.get("structured_data"),
        "session_id": session_id,
        "history_length": history_len,
        "memory_active": use_memory,
    }


@router.get("/history/{session_id}")
def get_chat_history(session_id: str, _user=Depends(get_current_user)):
    """Retrieve saved chat messages for a specific session ID."""
    messages = chat_memory.get(session_id, [])
    return {
        "session_id": session_id,
        "count": len(messages),
        "messages": messages,
    }


@router.delete("/history/{session_id}")
def clear_chat_history(session_id: str, _user=Depends(get_current_user)):
    """Clear memory for a given session ID."""
    if session_id in chat_memory:
        del chat_memory[session_id]
    return {
        "session_id": session_id,
        "message": "Chat memory successfully cleared",
    }


@router.get("/topics")
def get_bot_topics(_user=Depends(get_current_user)):
    return {
        "school": "Al-Noor Academy",
        "description": (
            "I can answer questions about school policies (fees, exams, admissions, rules) "
            "and look up live student records, fee status, results, and collection data."
        ),
        "topics": get_rag_service().get_known_topics(),
    }
