import json

import pytest

from src.design import REQUIREMENTS
from src.fixtures import feed
from src.governance import trace
from src.ingestion import ingest
from src.mapping import ROOT, load_profile
from src.model import describe
from src.retrieval import measurement_evidence, retrieve, search_measurements, supported
from src.validation import review
from src.workspace import build


@pytest.fixture
def db():
    connection = build()
    yield connection
    connection.close()


def test_design_fields_resolve(db):
    for requirement in REQUIREMENTS:
        columns, _, _ = describe(db, requirement.entity)
        assert requirement.field in {c["name"] for c in columns}
        assert all((requirement.definition, requirement.relationship, requirement.quality_rule, requirement.decision))


@pytest.mark.parametrize("system", ["Alpha", "Beta"])
def test_replay_preview_matches_every_published_decision(db, system):
    profile = load_profile(system.lower())
    data = feed(system)
    changes = db.total_changes
    reviewed = review(db, profile, data)
    assert db.total_changes == changes
    ingest(db, profile, data)
    stored = db.execute("""SELECT d.source_record_id, d.quality_status, d.reasons, d.audit_json
                           FROM quality_decision d JOIN source_record s USING(source_record_id)
                           WHERE s.batch_id=? AND s.source_system=? ORDER BY s.row_number""",
                        (reviewed.batch_id, system)).fetchall()
    assert len(reviewed.decisions) == len(stored) == 300
    for decision, (src, status, reason, audit) in zip(reviewed.decisions, stored):
        assert (decision.source_record_id, decision.status, decision.reason, decision.audit) == (
            src, status, reason, json.loads(audit))


def test_uploaded_filters_and_source_citation(db):
    profile = load_profile()
    content = (ROOT / "data/synthetic_raw/alpha.csv").read_bytes()
    profile.version = "upload-v2"
    batch = review(db, profile, content)
    assert ingest(db, profile, content) == {"accepted": 1, "corrected": 1, "rejected": 2}
    rid = "RES-Alpha-UPLOAD-02"
    for filters in ({"experiment_id": "EXP-A002"}, {"source_system": "Alpha"},
                    {"batch_id": batch.batch_id}, {"result_id": rid}):
        assert rid in {r["result_id"] for r in search_measurements(db, **filters)}
    assert len(search_measurements(db, batch_id=batch.batch_id)) == 2
    assert not search_measurements(db, source_system="Beta", batch_id=batch.batch_id)
    assert not search_measurements(db, result_id="RES-Alpha-UPLOAD-03")
    row, = search_measurements(db, result_id=rid, batch_id=batch.batch_id, experiment_id="EXP-A002")
    evidence = measurement_evidence(row)
    event, = trace(db, evidence.source_record_id)
    assert event["mapping_version"] == evidence.mapping_version == "upload-v2"
    assert json.loads(event["raw_json"])["ResultValue"] == "0.078"
    assert "78 nM" in evidence.text
    for identifier in (batch.batch_id, event["source_record_id"], "data row 2", "upload-v2"):
        assert identifier in evidence.source_citation
    question = f"What measurement was recorded for {rid}?"
    assert supported(question, retrieve(db, question)) == [evidence]
    assert review(db, profile, content) == batch
    collision = content.replace(b"UPLOAD-02", b"UPLOAD-05")
    assert "Duplicate result ID" in review(db, profile, collision).decisions[0].reason
    profile.version = "upload-v3"
    ingest(db, profile, content)
    assert search_measurements(db, result_id=rid)[0]["mapping_version"] == "upload-v3"
    assert {r["mapping_version"] for r in trace(db, evidence.source_record_id)} == {"upload-v2", "upload-v3"}
