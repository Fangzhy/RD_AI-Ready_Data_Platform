import json

import pytest

from src.evaluation import evaluate
from src.openrouter import GenerationError, configuration, generate
from src.retrieval import document_chunks, retrieve, supported
from src.workspace import build


def test_evaluation_and_access():
    db = build()
    chunks = document_chunks(db,"reader")
    assert len(chunks)==36 and all(c.access_class=="public" and c.source_link and c.source_record_id for c in chunks)
    assert not any(c.document_id=="DOC-A004" or (c.document_id=="DOC-A001" and c.version==1) for c in chunks)
    metrics, details = evaluate(db)
    assert len(details)==28 and metrics[1]["unsupported_answered"]==0
    assert metrics[1]["recalled"]==metrics[1]["answerable"]==10
    assert metrics[1]["correct_citations"]==10
    assert all(r["cited"] is None for r in details if r["expected"] is None)
    db.close()


def test_generation_checks_quotes_and_free_routes(monkeypatch):
    db = build()
    question = "What measurement was recorded in EXP-A001?"
    candidates = supported(question,retrieve(db,question))
    monkeypatch.setenv("OPEN_ROUTER_API","test-only")
    monkeypatch.setenv("OPENROUTER_MODEL","example/free:free")
    monkeypatch.setenv("OPENROUTER_MODEL_BACKUP","example/backup:free")
    calls = []
    class Response:
        status_code = 200
        def json(self):
            e = candidates[0]
            content = {"quote":e.text if len(calls)>1 else "invented","citation":e.citation}
            return {"choices":[{"message":{"content":json.dumps(content)}}]}
    def post(url, **kwargs):
        calls.append(kwargs["json"]["model"])
        return Response()
    monkeypatch.setattr("src.openrouter.requests.post",post)
    answer,model = generate(question,candidates)
    assert len(calls)==2 and answer["quote"]==candidates[0].text and model==calls[-1]
    monkeypatch.setenv("OPENROUTER_MODEL_BACKUP","example/paid")
    with pytest.raises(GenerationError):
        configuration()
    db.close()
