"""Manual check of the Modal DeepSeek endpoint. Not part of the test suite.

Needs the openai package, plus MODAL_PROXY_TOKEN_ID and MODAL_PROXY_TOKEN_SECRET in the
environment. Run with: python test_modal.py
"""
import os
import sys

from openai import OpenAI


def main() -> int:
    token_id = os.environ.get("MODAL_PROXY_TOKEN_ID", "").strip()
    token_secret = os.environ.get("MODAL_PROXY_TOKEN_SECRET", "").strip()
    if not token_id or not token_secret:
        print("Set MODAL_PROXY_TOKEN_ID and MODAL_PROXY_TOKEN_SECRET first.")
        return 1

    client = OpenAI(
        base_url="https://whassanshaikh--ep-deepseek-v4-1-flash-server.us-west.modal.direct/v1",
        api_key=f"{token_id}.{token_secret}",
    )

    print("Sending request to Modal endpoint...")
    try:
        completion = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-V4.1-Flash",
            messages=[
                {"role": "system", "content": "You are a concise technical assistant."},
                {"role": "user", "content": "Explain why low latency matters for LLM endpoints in three bullets."},
            ],
            temperature=0.3,
            max_tokens=2048,
            top_p=0.9,
            stream=False,
            extra_body={"reasoning_effort": "high"},
        )
    except Exception as error:
        print(f"\nError occurred: {error}")
        return 1

    print("\n--- Response ---")
    print(completion.choices[0].message.content)
    print("----------------")
    return 0


if __name__ == "__main__":
    sys.exit(main())
