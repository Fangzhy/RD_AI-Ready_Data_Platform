import json

import pytest

from src.fixtures import feed
from src.governance import trace
from src.ingestion import ingest
from src.mapping import load_profile
from src.retrieval import retrieve, supported
from src.workspace import build


def test_changed_mapping_retracts_results_without_losing_history_or_report():
    db = build()
    profile = load_profile()
    profile.fields["ResultUnits"], profile.fields["TestName"] = "assay_name", "result_unit"
    with pytest.raises(ValueError, match="version"):
        ingest(db, profile, feed("Alpha"))
    assert db.execute("SELECT count(*) FROM ingestion_run").fetchone()[0] == 2
    profile.version = "2.0"
    ingest(db, profile, feed("Alpha"))
    assert not db.execute("SELECT * FROM curated_results WHERE source_system='Alpha'").fetchone()
    events = trace(db, "RES-Alpha-0001")
    assert [r["quality_status"] for r in events] == ["rejected", "accepted"]
    assert any(f["operation"]=="rejected" and f["reasons"] for f in json.loads(events[0]["audit_json"]))
    q = "What measurement was recorded in DOC-A001?"
    assert supported(q,retrieve(db,q))[0].citation == "DOC-A001/v2/Measurement"
    q = "What was the curated measurement for RES-Alpha-0001?"
    assert not supported(q,retrieve(db,q))
    db.close()
