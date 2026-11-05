import time
import uuid
from functools import lru_cache
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session

from config import SCHOOL_NAME
from database import get_session
from models.user import User
from routers.auth import get_current_user
from services.school_assistant_service import SchoolAssistantService, groq_status

router = APIRouter(prefix="/chatbot", tags=["AI School Assistant"])

MAX_QUESTION_LENGTH = 1000
MAX_HISTORY_ITEMS = 40
MAX_HISTORY_ITEM_LENGTH = 4000
MAX_MESSAGES_PER_SESSION = 40
MAX_STORED_SESSIONS = 200
SESSION_ID_PATTERN = r"^[A-Za-z0-9_-]{1,64}$"

# In-memory conversations, stored per user so one person's session id never opens another's:
# (username, session_id) -> list of {"role": "user" | "assistant", "content": str, "timestamp": float}
chat_memory: Dict[tuple, List[Dict[str, Any]]] = {}


@lru_cache
def get_rag_service():
    from services.rag_service import rag_service
    return rag_service


class ChatHistoryItem(BaseModel):
    role: str = Field(max_length=20)
    content: str = Field(max_length=MAX_HISTORY_ITEM_LENGTH)


class ChatAskRequest(BaseModel):
    question: str = Field(max_length=MAX_QUESTION_LENGTH)
    session_id: Optional[str] = Field(default=None, pattern=SESSION_ID_PATTERN)
    history: Optional[List[ChatHistoryItem]] = Field(default=None, max_length=MAX_HISTORY_ITEMS)
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


def _memory_key(user: User, session_id: str) -> tuple:
    return (user.username, session_id)


def _conversation_so_far(key: tuple, sent_by_page: Optional[List[ChatHistoryItem]]) -> List[Dict[str, Any]]:
    """Server memory. The page's copy is used only when the server has none, as after a restart.

    Never both: added after the server's messages, the page's would read as the latest ones.
    """
    if chat_memory.get(key):
        return list(chat_memory[key])
    return [
        {"role": item.role, "content": item.content}
        for item in sent_by_page or []
        if item.role in ("user", "assistant") and item.content
    ]


def _remember_turn(key: tuple, question: str, answer: str) -> None:
    if key not in chat_memory and len(chat_memory) >= MAX_STORED_SESSIONS:
        del chat_memory[next(iter(chat_memory))]
    now = time.time()
    turn = [
        {"role": "user", "content": question, "timestamp": now},
        {"role": "assistant", "content": answer, "timestamp": now},
    ]
    chat_memory[key] = (chat_memory.get(key, []) + turn)[-MAX_MESSAGES_PER_SESSION:]


@router.post("/ask", response_model=ChatAskResponse)
def ask_school_assistant(
    req: ChatAskRequest,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    question = (req.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    use_memory = req.use_memory if req.use_memory is not None else True
    session_id = req.session_id or str(uuid.uuid4())
    key = _memory_key(user, session_id)

    conversation = _conversation_so_far(key, req.history) if use_memory else []
    result = SchoolAssistantService(session).answer(question, history=conversation)

    if use_memory:
        _remember_turn(key, question, result.get("answer", ""))

    return {
        "answer": result.get("answer", ""),
        "sources": result.get("sources", []),
        "grounded": result.get("grounded", False),
        "mode": result.get("mode"),
        "tools_used": result.get("tools_used"),
        "structured_data": result.get("structured_data"),
        "session_id": session_id,
        "history_length": len(chat_memory.get(key, [])) if use_memory else 0,
        "memory_active": use_memory,
    }


@router.get("/history/{session_id}")
def get_chat_history(session_id: str, user: User = Depends(get_current_user)):
    """Saved messages for one of this user's own sessions."""
    messages = chat_memory.get(_memory_key(user, session_id), [])
    return {
        "session_id": session_id,
        "count": len(messages),
        "messages": messages,
    }


@router.delete("/history/{session_id}")
def clear_chat_history(session_id: str, user: User = Depends(get_current_user)):
    """Clear one of this user's own sessions."""
    chat_memory.pop(_memory_key(user, session_id), None)
    return {
        "session_id": session_id,
        "message": "Chat memory successfully cleared",
    }


@router.get("/topics")
def get_bot_topics(_user=Depends(get_current_user)):
    return {
        "school": SCHOOL_NAME,
        "description": (
            "I can answer questions about school policies (fees, exams, admissions, rules) "
            "and look up live student records, fee status, results, and collection data."
        ),
        "topics": get_rag_service().get_known_topics(),
    }


@router.get("/status")
def get_bot_status(_user=Depends(get_current_user)):
    """What is really running, so the page never claims an AI service that is not there."""
    return {
        "school": SCHOOL_NAME,
        "language_model": groq_status(),
        "policy_search": get_rag_service().status(),
    }
