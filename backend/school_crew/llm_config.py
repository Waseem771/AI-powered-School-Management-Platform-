import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Load variables from .env file
load_dotenv()

token_id = os.environ.get("MODAL_PROXY_TOKEN_ID")
token_secret = os.environ.get("MODAL_PROXY_TOKEN_SECRET")

# This creates an LLM object compatible with CrewAI but uses your Modal DeepSeek endpoint
deepseek_llm = ChatOpenAI(
    model="deepseek-ai/DeepSeek-V4.1-Flash",
    openai_api_base="https://whassanshaikh--ep-deepseek-v4-1-flash-server.us-west.modal.direct/v1",
    openai_api_key=f"{token_id}.{token_secret}",
    temperature=0.3,
    max_tokens=2048
)
