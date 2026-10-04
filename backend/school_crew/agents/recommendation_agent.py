from crewai import Agent
from school_crew.llm_config import deepseek_llm

def create_recommendation_agent():
    return Agent(
        role="Program Recommender",
        goal="Suggest the best school programs based on the student's eligibility status and interests.",
        backstory="You are a friendly academic advisor. If a student is rejected, you find alternative programs they qualify for. If accepted, you congratulate them and suggest next steps.",
        verbose=True,
        allow_delegation=False,
        llm=deepseek_llm
    )
