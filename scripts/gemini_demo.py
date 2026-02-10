#!/usr/bin/env python3
"""
Gemini demo: chat with Gemini; when you ask to find products, Gemini calls our
orchestrator via function calling and shows the result.

Usage:
  export GOOGLE_AI_API_KEY=your_key   # or GEMINI_API_KEY
  export ORCHESTRATOR_URL=https://uso-orchestrator.onrender.com  # optional
  export GEMINI_MODEL=gemini-2.5-flash   # optional; list: curl ".../v1beta/models?key=$GOOGLE_AI_API_KEY"
  python scripts/gemini_demo.py

Then type e.g. "find flowers" or "I want birthday cakes".
"""

import json
import os
import sys
from typing import Optional

# Optional: add project root for local runs
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_SCRIPT_DIR)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "https://uso-orchestrator.onrender.com").rstrip("/")
GEMINI_API_KEY = os.getenv("GOOGLE_AI_API_KEY") or os.getenv("GEMINI_API_KEY")
# Model: gemini-2.5-flash default; override with GEMINI_MODEL (e.g. gemini-2.0-flash, gemini-flash-latest)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Gemini function declaration: discover_products → POST /api/v1/chat
DISCOVER_PRODUCTS_DECLARATION = {
    "name": "discover_products",
    "description": "Discover products from natural language. Call this when the user wants to find, search, or browse products (e.g. 'find flowers', 'I want cakes'). Returns a human-readable summary and product list.",
    "parameters": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The user's message or search request (e.g. 'find flowers')",
            },
            "limit": {
                "type": "integer",
                "description": "Max products to return (default 20)",
            },
            "thread_id": {"type": "string", "description": "Optional chat thread ID"},
            "platform": {
                "type": "string",
                "enum": ["chatgpt", "gemini"],
                "description": "Use 'gemini' when calling from Gemini",
            },
        },
        "required": ["text"],
    },
}


def call_orchestrator(text: str, limit: int = 20, thread_id: Optional[str] = None, platform: str = "gemini") -> dict:
    """Call USO orchestrator POST /api/v1/chat. Returns the JSON response."""
    import httpx

    payload = {"text": text, "limit": limit}
    if thread_id:
        payload["thread_id"] = thread_id
    payload["platform"] = platform
    r = httpx.post(
        f"{ORCHESTRATOR_URL}/api/v1/chat",
        json=payload,
        timeout=60.0,
    )
    r.raise_for_status()
    return r.json()


def run_demo():
    if not GEMINI_API_KEY:
        print("Set GOOGLE_AI_API_KEY or GEMINI_API_KEY", file=sys.stderr)
        sys.exit(1)

    import warnings
    warnings.filterwarnings("ignore", message=".*google.generativeai.*", category=FutureWarning)
    import google.generativeai as genai

    genai.configure(api_key=GEMINI_API_KEY)

    model = genai.GenerativeModel(
        GEMINI_MODEL,
        tools=[{"function_declarations": [DISCOVER_PRODUCTS_DECLARATION]}],
    )

    print("Gemini + USO Product Discovery demo")
    print("Orchestrator:", ORCHESTRATOR_URL)
    print("Type a message (e.g. 'find flowers') or 'quit' to exit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Bye.")
            break

        # Single turn: send user message and get model response (possibly a function call)
        last_err = None
        for attempt in range(3):
            try:
                response = model.generate_content(
                    user_input,
                    generation_config={"temperature": 0.2, "max_output_tokens": 1024},
                )
                break
            except Exception as e:
                last_err = e
                err_str = str(e).lower()
                if "429" in err_str or "resourceexhausted" in err_str or "quota" in err_str:
                    delay = 60
                    if "retry in" in err_str:
                        import re
                        m = re.search(r"retry in (\d+(?:\.\d+)?)\s*s", err_str)
                        if m:
                            delay = min(120, max(10, int(float(m.group(1)))))
                    if attempt < 2:
                        print(f"  Rate limited (429). Retrying in {delay}s...")
                        import time
                        time.sleep(delay)
                    else:
                        print(
                            f"Quota exceeded. Try again later or set GEMINI_MODEL=gemini-2.5-flash or gemini-flash-latest. See https://ai.google.dev/gemini-api/docs/rate-limits",
                            file=sys.stderr,
                        )
                        raise
                else:
                    raise

        if not response.candidates:
            print("(No response from Gemini)\n")
            continue

        parts = response.candidates[0].content.parts if response.candidates[0].content else []
        function_call_part = None
        for part in parts:
            if getattr(part, "function_call", None):
                function_call_part = part
                break

        if function_call_part and function_call_part.function_call.name == "discover_products":
            fc = function_call_part.function_call
            args = dict(fc.args) if hasattr(fc, "args") else {}
            text_arg = args.get("text", user_input)
            limit_arg = args.get("limit", 20)
            print(f"  [Calling orchestrator: text={text_arg!r}, limit={limit_arg}]")
            try:
                api_response = call_orchestrator(
                    text=text_arg,
                    limit=limit_arg,
                    platform="gemini",
                )
            except Exception as e:
                api_response = {"summary": f"Error calling API: {e}", "data": {}}
            summary = api_response.get("summary", str(api_response))
            # Show product names and prices if present
            data = api_response.get("data", {})
            products_data = data.get("products") or {}
            product_list = products_data.get("products") or []
            if product_list:
                lines = [f"  • {p.get('name', 'Product')} – {p.get('currency', 'USD')} {p.get('price', 0):.2f}" for p in product_list[:10]]
                print("\n".join(lines))
            print(f"\nGemini (from USO): {summary}\n")
        else:
            # Model replied with text only
            text = getattr(response, "text", None) or ""
            if text:
                print(f"Gemini: {text}\n")
            else:
                print("(No text in response)\n")


if __name__ == "__main__":
    run_demo()
