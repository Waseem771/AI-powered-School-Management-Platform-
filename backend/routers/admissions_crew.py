from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from database import get_session
from models.student import Student
from school_crew.crew import run_admissions_crew

router = APIRouter(prefix="/api/admissions-crew", tags=["Admissions CrewAI"])

class AdmissionRequest(BaseModel):
    student_roll_number: str
    desired_program: str

@router.post("/evaluate")
def evaluate_admission(req: AdmissionRequest, session: Session = Depends(get_session)):
    # 1. Fetch from Database
    student = session.exec(select(Student).where(Student.roll_number == req.student_roll_number)).first()
    
    if not student:
        raise HTTPException(status_code=404, detail=f"Student with roll number {req.student_roll_number} not found in Database.")
        
    # 2. Format profile for CrewAI
    student_profile = f"Name: {student.name}\nRoll Number: {student.roll_number}\nGrade: {student.grade}\nSection: {student.section}\nGuardian: {student.guardian_name}\nPhone: {student.phone}"
    
    # 3. Call CrewAI
    final_recommendation = run_admissions_crew(student_profile, req.desired_program)
    
    return {
        "status": "success", 
        "recommendation": final_recommendation,
        "student_name": student.name
    }
