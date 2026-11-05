from config import SCHOOL_NAME
from crewai import Agent

def create_counselor_agent(llm):
    return Agent(
        role='Admissions Counselor',
        goal='Collect student details and verify they meet the basic baseline admission requirements.',
        backstory=(
            f"You are the friendly but detail-oriented first point of contact for {SCHOOL_NAME}. "
            "You ensure that all prospective students meet the baseline criteria (like age and previous grade completion) "
            "before they move forward in the process."
        ),
        verbose=True,
        allow_delegation=False,
        llm=llm
    )
