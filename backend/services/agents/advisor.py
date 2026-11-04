from crewai import Agent

def create_advisor_agent(llm):
    return Agent(
        role='Program Advisor',
        goal='Recommend the absolute best academic tracks and support programs based on the academic evaluation.',
        backstory=(
            "You are a visionary student success advisor. You use the Academic Evaluator's notes to match "
            "students with the perfect academic tracks, clubs, or remedial support programs to ensure they thrive "
            "at Al-Noor Academy."
        ),
        verbose=True,
        allow_delegation=False,
        llm=llm
    )
