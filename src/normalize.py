import re
from lookup import lookup

INDICATION_PATTERNS = [
    ("neurovascular", [r"stroke", r"\btia\b", r"transient ischemic", r"neurovascular", r"carotid", r"aneurysm"]),
    ("ACS/PCI", [r"\bacs\b", r"acute coronary", r"\bpci\b", r"percutaneous", r"coronary stent"]),
    ("non-ACS non-PCI cardiovascular", [r"peripheral arter", r"\bpad\b", r"stable coronary"]),
]
DRUG_NAMES = {"clopidogrel": "clopidogrel", "plavix": "clopidogrel"}


def norm_gene(text):
    return "CYP2C19" if text.upper().replace(" ", "") == "CYP2C19" else None


def norm_diplotype(text):
    nums = re.findall(r"\*\s*(\d+)", text)      # find the two star alleles
    if len(nums) != 2:
        return None
    return f"*{nums[0]}/*{nums[1]}"


def norm_drug(text):
    return DRUG_NAMES.get(text.strip().lower())


def norm_indication(text):
    t = text.lower().strip()
    if re.search(r"non[- ]?acs|non[- ]?pci", t):
        return "non-ACS non-PCI cardiovascular"
    hits = [name for name, pats in INDICATION_PATTERNS if any(re.search(p, t) for p in pats)]
    return hits[0] if len(hits) == 1 else None   # unclear or ambiguous: refuse


def normalize_args(gene, diplotype, drug, indication):
    return {"gene": norm_gene(gene), "diplotype": norm_diplotype(diplotype),
            "drug": norm_drug(drug), "indication": norm_indication(indication)}


def lookup_v2(gene, diplotype, drug, indication):
    n = normalize_args(gene, diplotype, drug, indication)
    if any(v is None for v in n.values()):
        return None, n
    return lookup(**n), n