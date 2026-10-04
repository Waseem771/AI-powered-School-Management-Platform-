from crewai import Task

def create_admissions_tasks(counselor, evaluator, advisor, student_profile_text):
    task1 = Task(
        description=f"Review the following student profile: {student_profile_text}. Verify if they meet basic admission requirements (age, previous grades).",
        expected_output="A checklist report stating if basic requirements are met or what is missing.",
        agent=counselor
    )
    
    task2 = Task(
        description="Analyze the counselor's initial review and the student's academic grades. Identify core strengths and any subjects needing improvement.",
        expected_output="A detailed academic evaluation paragraph summarizing strengths, weaknesses, and eligibility.",
        agent=evaluator
    )
    
    task3 = Task(
        description="Based on the academic evaluation, recommend a specific academic track (e.g., Science, Arts) and any necessary support programs.",
        expected_output="A final, formatted admission recommendation plan for the student.",
        agent=advisor
    )
    
    return [task1, task2, task3]
