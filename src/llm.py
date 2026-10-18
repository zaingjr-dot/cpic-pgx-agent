import os, json, hashlib, time
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
CACHE = ROOT / "cache"
CACHE.mkdir(exist_ok=True)

DEFAULT_MODEL = "gemini-3.5-flash"


def _gemini(prompt, model, system, max_tokens):
    from google import genai
    from google.genai import types
    client = genai.Client()  # reads GEMINI_API_KEY from .env
    cfg = types.GenerateContentConfig(
        temperature=0, max_output_tokens=max_tokens,
        system_instruction=system or None)
    resp = client.models.generate_content(model=model, contents=prompt, config=cfg)
    return resp.text or ""


def _anthropic(prompt, model, system, max_tokens):
    import anthropic  # for later, when billing works
    client = anthropic.Anthropic()
    kw = dict(model=model, max_tokens=max_tokens, temperature=0,
              messages=[{"role": "user", "content": prompt}])
    if system:
        kw["system"] = system
    return client.messages.create(**kw).content[0].text


def call_llm(prompt, model=DEFAULT_MODEL, system="", max_tokens=2000):
    """One function for every model call. Every answer is saved to disk."""
    key = hashlib.sha256(json.dumps([model, system, prompt]).encode()).hexdigest()
    f = CACHE / f"{key}.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))["text"]
    fn = _anthropic if model.startswith("claude") else _gemini
    for attempt in range(6):
        try:
            text = fn(prompt, model, system, max_tokens)
            break
        except Exception as e:
            msg = str(e).lower()
            busy = any(k in msg for k in ("429", "quota", "503", "unavailable",
                                          "high demand", "overloaded"))
            if attempt == 5 or not busy:
                raise
            wait = 20 * (attempt + 1)
            print(f"Model busy, waiting {wait}s, then retrying...")
            time.sleep(wait)
    f.write_text(json.dumps({"model": model, "system": system,
                             "prompt": prompt, "text": text}), encoding="utf-8")
    return text