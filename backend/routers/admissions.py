from fastapi import APIRouter
from pydantic import BaseModel
from services.crew_service import run_admissions_evaluation

# Create the router for the AI Admissions
router = APIRouter(prefix="/api/admissions", tags=["Admissions AI"])

# Define what data the Frontend will send us
class StudentProfile(BaseModel):
    name: str
    age: int
    previous_grades: str
    interests: str
    notes: str = ""

@router.post("/evaluate")
async def evaluate_student(profile: StudentProfile):
    """
    Receives student data from the React frontend, formats it, 
    and sends it to the CrewAI multi-agent system.
    """
    # 1. Format the incoming data into a clear text block for the AI
    profile_text = (
        f"Student Name: {profile.name}\n"
        f"Age: {profile.age}\n"
        f"Previous Grades: {profile.previous_grades}\n"
        f"Interests & Extracurriculars: {profile.interests}\n"
        f"Additional Notes: {profile.notes}"
    )
    
    # 2. Wake up the CrewAI Agents and get the report!
    result = run_admissions_evaluation(profile_text)
    
    # 3. Send the final markdown report back to the Frontend
    return {
        "status": "success", 
        "evaluation_report": result
    }
