import os

from crewai import LLM
from dotenv import load_dotenv

load_dotenv()

token_id = os.environ.get("MODAL_PROXY_TOKEN_ID", "").strip()
token_secret = os.environ.get("MODAL_PROXY_TOKEN_SECRET", "").strip()

if not token_id or not token_secret:
    raise RuntimeError(
        "MODAL_PROXY_TOKEN_ID and MODAL_PROXY_TOKEN_SECRET must be set to use AI admissions."
    )

# An LLM object compatible with CrewAI, backed by the Modal DeepSeek endpoint.
deepseek_llm = LLM(
    model="openai/deepseek-ai/DeepSeek-V4.1-Flash",
    base_url="https://whassanshaikh--ep-deepseek-v4-1-flash-server.us-west.modal.direct/v1",
    api_key=f"{token_id}.{token_secret}",
    temperature=0.3,
)
