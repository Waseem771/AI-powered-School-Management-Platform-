import modal
from fastapi import FastAPI
from pydantic import BaseModel
from school_crew.crew import run_admissions_crew

# Define Modal App & Image (This tells Modal to install CrewAI and Langchain when deploying)
app = modal.App("educore-ai-school-platform")

image = modal.Image.debian_slim().pip_install(
    "fastapi", "crewai", "langchain-openai", "python-dotenv"
)

web_app = FastAPI()

class AdmissionRequest(BaseModel):
    student_profile: str
    desired_program: str

@web_app.post("/evaluate-admission")
def evaluate_admission(req: AdmissionRequest):
    # This runs the multi-agent system!
    final_recommendation = run_admissions_crew(req.student_profile, req.desired_program)
    return {"status": "success", "recommendation": final_recommendation}

# Expose the FastAPI app on Modal via a webhook
@app.function(image=image, secrets=[modal.Secret.from_dotenv()])
@modal.asgi_app()
def fastapi_app():
    return web_app
