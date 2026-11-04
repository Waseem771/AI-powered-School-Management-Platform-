import os
from crewai import Crew, Process
from langchain_groq import ChatGroq
from .agents.counselor import create_counselor_agent
from .agents.evaluator import create_evaluator_agent
from .agents.advisor import create_advisor_agent
from .agents.tasks import create_admissions_tasks

def run_admissions_evaluation(student_profile_text: str):
    """
    Main function to be called by FastAPI endpoint.
    Orchestrates the CrewAI multi-agent admissions process using Groq LLM.
    """
    
    # 1. Setup the Groq LLM using the key from .env
    # We use the fast versatile model, but you can swap to "openai/gpt-oss-120b" if preferred.
    llm = ChatGroq(
        api_key=os.environ.get("GROQ_API_KEY"),
        model="llama-3.3-70b-versatile" 
    )
    
    # 2. Initialize our Agents
    counselor = create_counselor_agent(llm)
    evaluator = create_evaluator_agent(llm)
    advisor = create_advisor_agent(llm)
    
    # 3. Initialize our Tasks with the student data
    tasks = create_admissions_tasks(counselor, evaluator, advisor, student_profile_text)
    
    # 4. Form the Crew
    admissions_crew = Crew(
        agents=[counselor, evaluator, advisor],
        tasks=tasks,
        process=Process.sequential, # Agents will execute their tasks one by one
        verbose=True
    )
    
    # 5. Kickoff the process and return the result
    result = admissions_crew.kickoff()
    
    # result is an object in newer CrewAI versions. We convert it to string for our API.
    return str(result)
