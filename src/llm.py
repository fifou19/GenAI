"""
Wrapper LLM multi-provider.
Centralise les appels LLM pour que rag.py et tools.py n'aient pas à se
soucier du provider choisi (Gemini, OpenAI, Anthropic, Mistral, Groq).
"""
import time
import random
from src.config import (
    GEMINI_API_KEY, GEMINI_MODEL,MAX_TOKENS,TEMPERATURES, 
    
    MAX_RETRIES, BASE_WAIT, MAX_WAIT,is_retryable_error
)



# ============================================================
# GEMINI
# ============================================================
def call_gemini(messages: list[dict]) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GEMINI_API_KEY)
    for attempt in range(MAX_RETRIES):
        try:
    # Extraire le system prompt et les messages user/assistant
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

            response = client.models.generate_content(
                model=GEMINI_MODEL,
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

        raise RuntimeError(f"Failed after {MAX_RETRIES} retries") from last_exc

