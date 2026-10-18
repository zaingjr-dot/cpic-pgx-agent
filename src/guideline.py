import pandas as pd
from pathlib import Path
from evaluate import PHENOTYPES, ACTIONS, STRENGTHS

DATA = Path(__file__).resolve().parent.parent / "data" / "ground_truth.csv"

RULES = """GUIDELINE EXCERPT: CPIC 2022 update, CYP2C19 genotype and clopidogrel therapy

Allele function: *1 = normal function; *2 and *3 = no function; *9 = decreased function; *17 = increased function. Any other allele (for example *12) has uncertain function.

How a diplotype becomes a phenotype:
- two normal-function alleles: Normal metabolizer
- one normal-function + one increased-function allele: Rapid metabolizer
- two increased-function alleles: Ultrarapid metabolizer
- one normal-function + one no-function allele, OR one increased-function + one no-function allele: Intermediate metabolizer
- two no-function alleles: Poor metabolizer
- one normal + one decreased, OR one increased + one decreased, OR two decreased: Likely intermediate metabolizer
- one decreased + one no-function allele: Likely poor metabolizer
- one or two uncertain-function alleles: Indeterminate (the recommendation tables below contain no recommendation for it)

A "Likely" phenotype gets the same recommendation and strength as the corresponding confirmed phenotype (Likely intermediate = Intermediate; Likely poor = Poor).

Recommendations when considering clopidogrel, by indication:"""


def build_guideline_text():
    gt = pd.read_csv(DATA)
    gt = gt[~gt["phenotype"].str.startswith("Likely")]
    order = ["Ultrarapid metabolizer", "Rapid metabolizer", "Normal metabolizer",
             "Intermediate metabolizer", "Poor metabolizer"]
    lines = []
    for ind in gt["indication"].unique():
        lines.append(f"\nIndication: {ind}")
        sub = gt[gt["indication"] == ind]
        for ph in order:
            r = sub[sub["phenotype"] == ph]
            if r.empty:
                continue
            r = r.iloc[0]
            lines.append(f"- {ph}: {r['recommendation']} (strength: {r['strength']})")
    return RULES + "\n".join(lines)


def prompt_guideline(gene, diplotype, drug, indication):
    return f"""You are a pharmacogenomics assistant. Use ONLY the guideline excerpt below. Do not use any other knowledge.

{build_guideline_text()}

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
- no_recommendation: the excerpt explicitly says there is no recommendation
- not_covered: the excerpt does not cover this case (other drug, indication not listed, or Indeterminate phenotype)
For no_recommendation use strength "No recommendation". For not_covered use strength "NOT COVERED"."""