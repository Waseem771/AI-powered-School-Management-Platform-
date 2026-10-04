import os
from openai import OpenAI

# Hardcoding the tokens directly as strings
token_id = "wk-ARXl6PIFWUyOOM2InPD1iV"
token_secret = "ws-kKi9AitPLvT5FZipnCr0LF"

print(f"Token ID loaded: {'Yes' if token_id else 'No'}")
print(f"Token Secret loaded: {'Yes' if token_secret else 'No'}")

client = OpenAI(
    base_url="https://whassanshaikh--ep-deepseek-v4-1-flash-server.us-west.modal.direct/v1",
    api_key=f"{token_id}.{token_secret}",
)

print("Sending request to Modal endpoint...")

try:
    completion = client.chat.completions.create(
        model="deepseek-ai/DeepSeek-V4.1-Flash",
        messages=[
            {
                "role": "system",
                "content": "You are a concise technical assistant.",
            },
            {
                "role": "user",
                "content": "Explain why low latency matters for LLM endpoints in three bullets.",
            },
        ],
        temperature=0.3,
        max_tokens=2048,
        top_p=0.9,
        stream=False,
        extra_body={"reasoning_effort": "high"},
    )
    print("\n--- Response ---")
    print(completion.choices[0].message.content)
    print("----------------")
except Exception as e:
    print(f"\nError occurred: {e}")
