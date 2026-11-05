from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from config import DEMO_MODE, SCHOOL_NAME, SCHOOL_TAGLINE
from database import get_session
from models.fee import AcademicYear
from routers.auth import get_current_user

router = APIRouter(prefix="/school", tags=["School"])


@router.get("/public")
def get_public_school_details():
    """Shown on the sign-in page, so it needs no login and holds nothing private."""
    return {"name": SCHOOL_NAME, "demo_mode": DEMO_MODE}


@router.get("/info")
def get_school_info(session: Session = Depends(get_session), _user=Depends(get_current_user)):
    """The school's name and current session, so no page has to hardcode them."""
    current_year = session.exec(select(AcademicYear).where(AcademicYear.is_current == True)).first()  # noqa: E712
    return {
        "name": SCHOOL_NAME,
        "tagline": SCHOOL_TAGLINE,
        "academic_session": current_year.label if current_year else None,
        "demo_mode": DEMO_MODE,
    }
