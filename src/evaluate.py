import json, re

PHENOTYPES = ["Ultrarapid metabolizer", "Rapid metabolizer", "Normal metabolizer",
              "Likely intermediate metabolizer", "Intermediate metabolizer",
              "Likely poor metabolizer", "Poor metabolizer",
              "Indeterminate", "Unknown"]
ACTIONS = ["standard_dose", "avoid_clopidogrel", "consider_alternative",
           "no_recommendation", "not_covered"]
STRENGTHS = ["Strong", "Moderate", "No recommendation", "NOT COVERED"]


def action_of(rec):
    """Turn the guideline sentence in the table into one of 5 simple actions."""
    if rec == "NOT COVERED":
        return "not_covered"
    if rec == "No recommendation":
        return "no_recommendation"
    if rec.startswith("If considering clopidogrel"):
        return "standard_dose"
    if rec.startswith("Avoid"):
        return "avoid_clopidogrel"
    if rec.startswith("Consider an alternative"):
        return "consider_alternative"
    return "unknown"


def prompt_alone(gene, diplotype, drug, indication):
    return f"""You are a pharmacogenomics assistant. Answer using what you know about the CPIC guideline for CYP2C19 and clopidogrel (2022 update).

Case:
- Gene: {gene}
- Diplotype: {diplotype}
- Drug: {drug}
- Indication: {indication}

Reply with ONLY a JSON object, no other text, with exactly these keys:
- "phenotype": one of {PHENOTYPES}
- "action": one of {ACTIONS}
- "strength": one of {STRENGTHS}

Meaning of the actions:
- standard_dose: use clopidogrel at the standard dose
- avoid_clopidogrel: avoid clopidogrel if possible
- consider_alternative: consider an alternative P2Y12 inhibitor
- no_recommendation: the guideline explicitly says it has no recommendation
- not_covered: this guideline does not cover this exact gene, diplotype, drug and indication combination
For no_recommendation use strength "No recommendation". For not_covered use strength "NOT COVERED"."""


def parse_json(text):
    """Pull the JSON object out of a model answer, even if wrapped in ``` fences."""
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def norm(s):
    return str(s).strip().lower()


def score_row(case, ans):
    """Compare the model's answer with the answer key. 1 = right, 0 = wrong."""
    parsed = 1 if ans else 0
    ans = ans or {}
    exp = action_of(case["expected_recommendation"])
    act = norm(ans.get("action"))
    ph_scored = case["expected_phenotype"] != "NOT COVERED"
    return dict(
        parsed=parsed,
        phenotype_ok=float(norm(ans.get("phenotype")) == norm(case["expected_phenotype"])) if ph_scored else float("nan"),
        action_ok=float(act == norm(exp)),
        strength_ok=float(norm(ans.get("strength")) == norm(case["expected_strength"])),
        dangerous=float(exp in ("avoid_clopidogrel", "consider_alternative") and act == "standard_dose"),
        overreach=float(exp in ("no_recommendation", "not_covered")
                        and act in ("standard_dose", "avoid_clopidogrel", "consider_alternative")),
    )