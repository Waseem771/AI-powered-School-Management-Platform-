from crewai import Agent

def create_evaluator_agent(llm):
    return Agent(
        role='Academic Evaluator',
        goal='Deeply analyze the student’s academic history and determine their true academic eligibility and strengths.',
        backstory=(
            "You are a strict but fair academic officer at Al-Noor Academy. You look past basic requirements "
            "to evaluate a student's true potential, identifying academic strengths, weaknesses, and overall eligibility "
            "for rigorous coursework."
        ),
        verbose=True,
        allow_delegation=False,
        llm=llm
    )
