import sys
sys.path.insert(0, './backend')
from database import engine
from sqlmodel import Session
from routers.admissions_crew import evaluate_admission, AdmissionRequest
req = AdmissionRequest(student_roll_number='106', desired_program='Grade 8')
with Session(engine) as session:
    try:
        res = evaluate_admission(req=req, session=session)
        print('Success!')
        print(res)
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

