"""
Call to the Gemini LLM.
"""
import time
import random
from google import genai
from google.genai import types
from src.config import GEMINI_API_KEY, GEMINI_MODEL, MAX_TOKENS, TEMPERATURES,MAX_RETRIES, BASE_WAIT, MAX_WAIT, is_retryable_error

_client = genai.Client(api_key=GEMINI_API_KEY)


def call_gemini(messages: list[dict]) -> str: # type: ignore
    """Call the Gemini LLM with the given messages and return the response text."""
    for attempt in range(MAX_RETRIES):
        try:
            # Extract the system prompt and the user/assistant messages
            system_instruction = ""
            contents = []

            for msg in messages:
                if msg["role"] == "system":
                    system_instruction += msg["content"] + "\n"
                elif msg["role"] == "user":
                    contents.append(types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=msg["content"])]
                    ))
                elif msg["role"] == "assistant":
                    contents.append(types.Content(
                        role="model",
                        parts=[types.Part.from_text(text=msg["content"])]
                    ))

            response = _client.models.generate_content(
                model=GEMINI_MODEL, # type: ignore
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction.strip(),
                    temperature=TEMPERATURES,
                    max_output_tokens=MAX_TOKENS,
                ),
            
            )
            text = response.text
            if text is None:
                print(f"    Empty response (attempt {attempt+1})")
                time.sleep(BASE_WAIT)
                continue
            return text.strip()
        except Exception as e:
            last_exc = e
            if not is_retryable_error(e):
                raise
            wait = min(BASE_WAIT * (2 ** attempt) + random.uniform(0, 1.5), MAX_WAIT)
            print(f"    Retry {attempt+1}/{MAX_RETRIES} — waiting {wait:.0f}s ({e})")
            time.sleep(wait)

    raise RuntimeError(f"Failed after {MAX_RETRIES} retries") from last_exc # type: ignore

