"""List the Gemini models this API key can actually use.

Model names move faster than any hardcoded default, so set GEMINI_MODEL in .env
to whatever this prints rather than trusting the fallback in extract.py.

    python -m corpus.models
"""

import os

from dotenv import load_dotenv
from google import genai

load_dotenv()


def main() -> None:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise SystemExit("GEMINI_API_KEY is not set — copy .env.example to .env")

    client = genai.Client(api_key=key)
    print(f"{'model':<45} {'in':>9} {'out':>8}")
    print("-" * 65)
    for m in client.models.list():
        actions = getattr(m, "supported_actions", None) or []
        if actions and "generateContent" not in actions:
            continue
        name = m.name.removeprefix("models/")
        print(f"{name:<45} {m.input_token_limit or '-':>9} {m.output_token_limit or '-':>8}")

    print(f"\ncurrently configured: GEMINI_MODEL={os.getenv('GEMINI_MODEL', 'gemini-2.5-pro')}")


if __name__ == "__main__":
    main()
