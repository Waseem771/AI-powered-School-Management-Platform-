from crewai import Agent
from school_crew.llm_config import deepseek_llm

def create_requirements_agent():
    return Agent(
        role="Admission Requirements Analyst",
        goal="Extract and verify the exact admission requirements for any given school program.",
        backstory="You are a meticulous analyst who knows the exact criteria (grades, documents, tests) required for every program in the school.",
        verbose=True,
        allow_delegation=False,
        llm=deepseek_llm
    )
