"""
SilkCocoonAI - Sarvam API key checker (check_key.py)

Run this when the app says the API key was rejected. It tests the key in
isolation (no Streamlit, no image) and prints exactly what it found.

Usage (from the project folder, with the venv active):

    python check_key.py

The output is safe to share - the key itself is masked.

Note: the /v2/models endpoint lists model IDs but does NOT authenticate, so it
returns 200 even for a bad key. The real auth test is the chat completion call.
"""

import os
import sys

try:
    import requests
except ImportError:
    print("The 'requests' package is missing. Run: python -m pip install -r requirements.txt")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
    _DOTENV = True
except ImportError:
    _DOTENV = False

HERE = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(HERE, ".env")
MODELS_URL = os.getenv("SARVAM_MODELS_URL", "https://api.sarvam.ai/v2/models").strip()
CHAT_URL = os.getenv("SARVAM_CHAT_URL", "https://api.sarvam.ai/v2/chat/completions").strip()
MODEL = os.getenv("SARVAM_MODEL", "gemma4").strip() or "gemma4"


def mask(value: str) -> str:
    if not value:
        return "(empty)"
    if len(value) <= 8:
        return value[0] + "*" * (len(value) - 1)
    return f"{value[:4]}...{value[-3:]}"


def main() -> int:
    print("=" * 64)
    print(" SilkCocoon AI - Sarvam API key check")
    print("=" * 64)

    print(f"python-dotenv installed:   {_DOTENV}")
    print(f".env file found:           {os.path.exists(ENV_PATH)}  ({ENV_PATH})")

    raw = os.getenv("SARVAM_API_KEY", "")
    key = raw.strip()

    print(f"SARVAM_API_KEY present:    {bool(key)}")
    if key:
        has_quotes = key[:1] in ('"', "'") or key[-1:] in ('"', "'")
        print(f"  masked:                  {mask(key)}")
        print(f"  length:                  {len(key)} characters")
        print(f"  starts with 'sk_':       {key.startswith('sk_')}")
        print(f"  surrounding whitespace:  {'YES (problem!)' if raw != key else 'no'}")
        print(f"  wrapped in quotes:       {'YES (problem!)' if has_quotes else 'no'}")
        print(f"  contains non-ASCII:      {'YES (problem!)' if any(ord(c) > 127 for c in key) else 'no'}")
        print(f"  contains inner spaces:   {'YES (problem!)' if ' ' in key else 'no'}")
    print(f"SARVAM_MODEL:              {MODEL}")

    if not key:
        print("\nVERDICT: no key found.")
        print("  Create a .env file next to app.py containing:")
        print("      SARVAM_API_KEY=your_key_here")
        print("  (copy .env.example to .env first).")
        return 1

    headers = {"api-subscription-key": key, "Content-Type": "application/json"}

    # Informational only - this endpoint does NOT validate the key.
    print("-" * 64)
    try:
        rm = requests.get(MODELS_URL, headers={"api-subscription-key": key}, timeout=20)
        if rm.status_code == 200:
            ids = [m.get("id") for m in rm.json().get("data", [])]
            print(f"Model IDs advertised:      {', '.join(ids)}")
        else:
            print(f"Model list:                HTTP {rm.status_code}")
    except Exception as e:
        print(f"Model list:                network error -> {e}")
    print("(Note: the model list is NOT an auth test - it returns 200 even for a bad key.)")

    # The real auth test: a tiny chat completion.
    print("-" * 64)
    print(f"Auth test (POST /v2/chat/completions, model={MODEL}):")
    try:
        payload = {
            "model": MODEL,
            "messages": [{"role": "user", "content": "Reply with the single word: ready"}],
            "max_tokens": 8,
        }
        rc = requests.post(CHAT_URL, headers=headers, json=payload, timeout=60)
        print(f"  HTTP {rc.status_code}")
        body = (rc.text or "")[:300]
        if rc.status_code == 200:
            try:
                content = rc.json()["choices"][0]["message"]["content"]
                print(f"  model replied:           {str(content).strip()[:60]!r}")
            except Exception:
                print("  (reply received, but could not be parsed)")
            print("-" * 64)
            print("VERDICT: your key works. Auth and generation both succeeded.")
            print("  If the app still fails, restart Streamlit after editing .env")
            print("  (Ctrl+C in the terminal, then 'streamlit run app.py' again).")
            return 0

        print(f"  response:                {body}")
        low = body.lower()
        if rc.status_code in (401, 403) and ("invalid_api_key" in low or "authentication" in low or "credential" in low):
            print("-" * 64)
            print("VERDICT: Sarvam REJECTED this key (invalid or missing credentials).")
            print("  The key was sent but is not valid/active. Most common causes:")
            print("   1. A typo or a partial paste (compare the length shown above).")
            print("   2. The key was rotated/regenerated - use the current one.")
            print("   3. Extra characters: quotes, spaces, or a trailing newline.")
            print("   4. The key was deleted, or the workspace changed.")
            print("  Get a fresh key at https://dashboard.sarvam.ai and paste it into .env.")
            return 1

        if rc.status_code == 403:
            print("-" * 64)
            print("VERDICT: the key is valid, but this endpoint/model is not permitted for it.")
            print(f"  '{MODEL}' is served on Sarvam's beta V2 route and must be enabled per key.")
            print("  Request beta access from Sarvam, or try another model in the sidebar.")
            return 1

        print("-" * 64)
        print(f"VERDICT: unexpected response (HTTP {rc.status_code}). See the response above.")
        return 1

    except Exception as e:
        print(f"  network error -> {e}")
        print("  (check your internet connection / firewall)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
