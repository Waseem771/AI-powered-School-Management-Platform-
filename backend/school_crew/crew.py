from crewai import Task, Crew, Process
from school_crew.agents.requirements_agent import create_requirements_agent
from school_crew.agents.eligibility_agent import create_eligibility_agent
from school_crew.agents.recommendation_agent import create_recommendation_agent

def run_admissions_crew(student_profile: str, desired_program: str):
    # 1. Instantiate Agents
    req_agent = create_requirements_agent()
    eligibility_agent = create_eligibility_agent()
    rec_agent = create_recommendation_agent()

    # 2. Define Tasks
    task1 = Task(
        description=f"Find the admission requirements for the '{desired_program}' program.",
        expected_output="A bulleted list of exact requirements (e.g., minimum GPA, required documents).",
        agent=req_agent
    )

    task2 = Task(
        description=f"Evaluate this student profile: {student_profile} against the requirements found by the Requirements Analyst.",
        expected_output="A clear 'ELIGIBLE' or 'NOT ELIGIBLE' decision with a brief justification.",
        agent=eligibility_agent
    )

    task3 = Task(
        description="Based on the eligibility decision, provide a final recommendation message for the student. Suggest alternative programs if they were rejected.",
        expected_output="A friendly, professional email to the student with their result and recommendations.",
        agent=rec_agent
    )

    # 3. Create and Run the Crew
    admissions_crew = Crew(
        agents=[req_agent, eligibility_agent, rec_agent],
        tasks=[task1, task2, task3],
        verbose=True,
        process=Process.sequential
    )

    result = admissions_crew.kickoff()
    return result
