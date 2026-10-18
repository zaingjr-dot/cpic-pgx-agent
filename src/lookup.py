import re
from pathlib import Path
import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data" / "ground_truth.csv"
_df = pd.read_csv(DATA)


def _norm(diplotype):
    """Put alleles in a standard order, so *17/*2 and *2/*17 match."""
    alleles = [a.strip() for a in diplotype.split("/")]
    return "/".join(sorted(alleles, key=lambda a: int(re.sub(r"\D", "", a) or 0)))


_df["diplotype_norm"] = _df["diplotype"].map(_norm)


def lookup(gene, diplotype, drug, indication):
    """Return the matching guideline row as a dict, or None if not covered."""
    m = _df[
        (_df["gene"] == gene)
        & (_df["diplotype_norm"] == _norm(diplotype))
        & (_df["drug"] == drug)
        & (_df["indication"] == indication)
    ]
    if m.empty:
        return None
    return m.iloc[0].to_dict()