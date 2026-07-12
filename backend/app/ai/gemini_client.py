"""
Thin wrapper around Google's Gemini API.

Design goals for a live hackathon demo:
1. NEVER crash / block the request if the API key is missing, invalid, rate-limited,
   or there is no internet at demo time. Every public method degrades gracefully
   to a deterministic, rule-based fallback string built from the same data that
   would have gone into the prompt.
2. Keep prompt construction separate (see prompts.py) so this file only deals with
   transport + error handling.
3. Short timeout so the UI never hangs waiting on a flaky network.
"""

import os
import json
import logging
from typing import Optional

logger = logging.getLogger("ai.gemini_client")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_TIMEOUT_SECONDS = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "8"))
GEMINI_ENDPOINT = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)


class GeminiUnavailable(Exception):
    """Raised internally when the API cannot be reached; callers should catch this
    and fall back to rule-based text. It is never allowed to bubble up to FastAPI."""


class GeminiClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or GEMINI_API_KEY
        self.enabled = bool(self.api_key)
        if not self.enabled:
            logger.warning(
                "GEMINI_API_KEY not set — AI layer will run in offline fallback mode. "
                "This is safe for demos: every endpoint still returns a rule-based explanation."
            )

    def generate(self, prompt: str, max_output_tokens: int = 512) -> str:
        """
        Returns raw text from Gemini, or raises GeminiUnavailable.
        Caller is responsible for falling back.
        """
        if not self.enabled:
            raise GeminiUnavailable("No API key configured")

        try:
            import requests  # local import so the module still imports with no deps installed
        except ImportError as exc:
            raise GeminiUnavailable("requests library not installed") from exc

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": max_output_tokens,
            },
        }

        try:
            resp = requests.post(
                f"{GEMINI_ENDPOINT}?key={self.api_key}",
                json=payload,
                timeout=GEMINI_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise GeminiUnavailable("Empty response from Gemini")
            parts = candidates[0]["content"]["parts"]
            text = "".join(p.get("text", "") for p in parts).strip()
            if not text:
                raise GeminiUnavailable("Empty text in Gemini response")
            return text
        except GeminiUnavailable:
            raise
        except Exception as exc:  # noqa: BLE001 - intentionally broad, this is a demo-safety net
            logger.error("Gemini call failed, falling back: %s", exc)
            raise GeminiUnavailable(str(exc)) from exc

    def generate_json(self, prompt: str, max_output_tokens: int = 512) -> Optional[dict]:
        """Same as generate() but attempts to parse a JSON object out of the response.
        Returns None (never raises) if parsing fails, so callers can fall back cleanly."""
        try:
            text = self.generate(prompt, max_output_tokens=max_output_tokens)
        except GeminiUnavailable:
            return None

        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:]
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Gemini returned non-JSON when JSON was requested: %s", text[:200])
            return None


# Module-level singleton used by the rest of the AI layer
gemini_client = GeminiClient()
