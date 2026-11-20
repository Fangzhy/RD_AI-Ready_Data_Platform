import json

from src.mapping import ROOT
from src.retrieval import retrieve, supported


def evaluate(db):
    cases = json.loads((ROOT / "data/evaluation/questions.json").read_text(encoding="utf8"))
    details, metrics = [], []
    for mode in ("baseline","aware"):
        answered = correct = recalled = unsupported_answers = abstained = 0
        positives = sum(c["citation"] is not None for c in cases)
        for case in cases:
            hits = retrieve(db,case["question"],case["role"],mode)
            answer = supported(case["question"],hits)
            gold = case["citation"]
            identifiers = [h.citation for h in hits]
            hit = bool(gold and gold in identifiers)
            recalled += hit
            citation = answer[0].citation if answer else None
            valid = bool(answer and citation==gold and case["value"] in answer[0].text)
            correct += valid
            answered += bool(answer)
            abstained += not answer
            unsupported_answers += bool(answer and not gold)
            details.append(dict(mode=mode,question=case["question"],role=case["role"],expected=gold,
                                retrieved=identifiers,cited=citation,recall_hit=hit if gold else None,
                                citation_correct=valid if answer else None,unanswered=not answer))
        metrics.append(dict(mode=mode,cases=len(cases),answerable=positives,recalled=recalled,
                            recall_at_5=recalled/positives,citations=answered,correct_citations=correct,
                            citation_correctness=correct/answered if answered else None,
                            unanswered=abstained,unsupported_cases=len(cases)-positives,
                            unsupported_answered=unsupported_answers))
    return metrics, details
