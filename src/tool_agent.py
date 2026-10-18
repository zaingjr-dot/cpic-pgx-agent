import json, hashlib, time
from pathlib import Path
from dotenv import load_dotenv
from lookup import lookup
from evaluate import PHENOTYPES, ACTIONS, STRENGTHS

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
CACHE = ROOT / "cache"
CACHE.mkdir(exist_ok=True)


def make_tool(log):
    def guideline_lookup(gene: str, diplotype: str, drug: str, indication: str) -> dict:
        """Look up the CPIC 2022 guideline row for a gene, diplotype, drug and indication.
        Returns found=False if the guideline table does not cover this exact case."""
        row = lookup(gene, diplotype, drug, indication)
        if row is None:
            out = {"found": False,
                   "message": "No row in the guideline table for this exact gene, diplotype, drug and indication."}
        else:
            out = {"found": True, "phenotype": row["phenotype"],
                   "recommendation": row["recommendation"], "strength": row["strength"]}
        log.append({"args": {"gene": gene, "diplotype": diplotype,
                             "drug": drug, "indication": indication}, "result": out})
        return out
    return guideline_lookup


def prompt_tool(gene, diplotype, drug, indication):
    return f"""You are a pharmacogenomics assistant. You have a tool called guideline_lookup that reads the CPIC 2022 guideline table. Always call it once for the case below, and base your answer ONLY on what it returns. Do not use other knowledge.

Case:
- Gene: {gene}
- Diplotype: {diplotype}
- Drug: {drug}
- Indication: {indication}

If the tool returns found=False, the guideline table does not cover this case: use action "not_covered" and strength "NOT COVERED". Give the phenotype only if the tool returned one, otherwise "Unknown".

After the tool answers, reply with ONLY a JSON object, no other text, with exactly these keys:
- "phenotype": one of {PHENOTYPES}
- "action": one of {ACTIONS}
- "strength": one of {STRENGTHS}

Meaning of the actions:
- standard_dose: use clopidogrel at the standard dose
- avoid_clopidogrel: avoid clopidogrel if possible
- consider_alternative: consider an alternative P2Y12 inhibitor
- no_recommendation: the guideline explicitly says there is no recommendation
- not_covered: the guideline table does not cover this case
For no_recommendation use strength "No recommendation". For not_covered use strength "NOT COVERED"."""


def call_with_tool(prompt, model, max_tokens=2000):
    key = hashlib.sha256(json.dumps([model, prompt, "tool-v1"]).encode()).hexdigest()
    f = CACHE / f"{key}.json"
    if f.exists():
        d = json.loads(f.read_text(encoding="utf-8"))
        return d["text"], d["tool_calls"]
    from google import genai
    from google.genai import types
    client = genai.Client()
    log = []
    cfg = types.GenerateContentConfig(temperature=0, max_output_tokens=max_tokens,
                                      tools=[make_tool(log)])
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