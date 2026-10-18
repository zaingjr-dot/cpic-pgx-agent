import json, hashlib, time
from pathlib import Path
from dotenv import load_dotenv
from normalize import lookup_v2

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
CACHE = ROOT / "cache"
CACHE.mkdir(exist_ok=True)


def make_tool_v2(log):
    def guideline_lookup(gene: str, diplotype: str, drug: str, indication: str) -> dict:
        """Look up the CPIC 2022 guideline row for a gene, diplotype, drug and indication.
        Inputs may be written loosely: the tool cleans them before searching.
        Returns found=False if the guideline table does not cover this case."""
        row, norm = lookup_v2(gene, diplotype, drug, indication)
        if row is None:
            out = {"found": False,
                   "message": "No row in the guideline table for this case (input not understood or not covered)."}
        else:
            out = {"found": True, "phenotype": row["phenotype"],
                   "recommendation": row["recommendation"], "strength": row["strength"]}
        log.append({"args": {"gene": gene, "diplotype": diplotype, "drug": drug,
                             "indication": indication}, "normalized": norm, "result": out})
        return out
    return guideline_lookup


def call_with_tool_v2(prompt, model, max_tokens=2000):
    key = hashlib.sha256(json.dumps([model, prompt, "tool-v2"]).encode()).hexdigest()
    f = CACHE / f"{key}.json"
    if f.exists():
        d = json.loads(f.read_text(encoding="utf-8"))
        return d["text"], d["tool_calls"]
    from google import genai
    from google.genai import types
    client = genai.Client()
    log = []
    cfg = types.GenerateContentConfig(temperature=0, max_output_tokens=max_tokens,
                                      tools=[make_tool_v2(log)])
    for attempt in range(6):
        try:
            log.clear()
            resp = client.models.generate_content(model=model, contents=prompt, config=cfg)
            break
        except Exception as e:
            msg = str(e).lower()
            busy = any(k in msg for k in ("429", "quota", "503", "unavailable",
                                          "high demand", "overloaded"))
            if attempt == 5 or not busy or "perday" in msg:
                raise
            wait = 20 * (attempt + 1)
            print(f"Model busy, waiting {wait}s, then retrying...")
            time.sleep(wait)
    text = resp.text or ""
    f.write_text(json.dumps({"model": model, "prompt": prompt, "text": text,
                             "tool_calls": log}), encoding="utf-8")
    return text, list(log)