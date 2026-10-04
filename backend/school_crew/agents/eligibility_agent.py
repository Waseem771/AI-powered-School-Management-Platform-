from crewai import Agent
from school_crew.llm_config import deepseek_llm

def create_eligibility_agent():
    return Agent(
        role="Student Eligibility Evaluator",
        goal="Compare a student's profile against program requirements to determine if they are eligible.",
        backstory="You are an experienced admissions officer. You strictly and fairly evaluate if a student's grades and documents meet the required threshold.",
        verbose=True,
        allow_delegation=False,
        llm=deepseek_llm
    )
