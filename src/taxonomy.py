import json

from src.mapping import ROOT

VOCAB = json.loads((ROOT / "configs/taxonomy.json").read_text(encoding="utf8"))
CONCEPTS = {c["id"]: c for c in VOCAB["assays"]}


def resolve(term, source=None):
    key = term.strip().casefold()
    matches = []
    for concept in CONCEPTS.values():
        aliases = list(concept["aliases"].values()) if source is None else [concept["aliases"].get(source, "")]
        if key and key in {name.casefold() for name in [concept["term"], *aliases]}:
            matches.append(concept)
    return matches[0] if len(matches) == 1 else None
