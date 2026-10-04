import os
from dotenv import load_dotenv
from crewai import LLM

# Load variables from .env file
load_dotenv()

token_id = os.environ.get("MODAL_PROXY_TOKEN_ID", "wk-ARXl6PIFWUyOOM2InPD1iV")
token_secret = os.environ.get("MODAL_PROXY_TOKEN_SECRET", "ws-kKi9AitPLvT5FZipnCr0LF")

# This creates an LLM object compatible with CrewAI but uses your Modal DeepSeek endpoint
deepseek_llm = LLM(
    model="openai/deepseek-ai/DeepSeek-V4.1-Flash",
    base_url="https://whassanshaikh--ep-deepseek-v4-1-flash-server.us-west.modal.direct/v1",
    api_key=f"{token_id}.{token_secret}",
    temperature=0.3
)
