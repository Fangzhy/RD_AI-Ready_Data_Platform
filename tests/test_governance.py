from src.fixtures import feed
from src.governance import impact, trace, visible_documents
from src.ingestion import ingest
from src.mapping import load_profile
from src.workspace import build


def test_mapping_history_and_downstream_impact():
    db = build()
    assert not db.execute("""SELECT 1 FROM assay_result r WHERE NOT EXISTS (
        SELECT 1 FROM lineage_event e WHERE e.curated_record_id=r.result_id AND
        e.source_record_id=r.source_record_id AND e.quality_status <> 'rejected')""").fetchone()
    p = load_profile()
    p.version = "2.0"
    ingest(db,p,feed("Alpha"))
    history = trace(db,"RES-Alpha-0001")
    assert [r["mapping_version"] for r in history] == ["2.0","1.0"]
    assert len({r["transformation_id"] for r in history}) == 2
    assert all(r["raw_json"] and r["audit_json"] and r["loaded_at"] for r in history)
    rows, datasets = impact(db,"Alpha","1.0")
    assert len(rows) == 300 and {"dataset":"evidence_search"} in datasets
    assert {r["quality_status"] for r in rows} == {"rejected","corrected","accepted"}
    db.close()


def test_filter_before_document_search():
    db = build()
    public = visible_documents(db,"reader")
    assert len(public) == 18 and len(visible_documents(db,"reviewer")) == 24
    assert all(r["access_class"] == "public" and r["lifecycle"] == "current" for r in public)
    assert visible_documents(db,"invalid") == public
    db.close()
