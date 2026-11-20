from src.database import records
from src.fixtures import feed
from src.ingestion import ingest
from src.mapping import load_profile
from src.workspace import build


def test_harmonization_quarantine_and_replay():
    db = build()
    sql = "SELECT source_system,count(*) AS n FROM curated_results GROUP BY 1 ORDER BY 1"
    assert records(db,sql) == [{"source_system":"Alpha","n":292},{"source_system":"Beta","n":292}]
    reasons = " ".join(r[0] for r in db.execute("SELECT reasons FROM quarantine"))
    for term in ("sample","compound","Duplicate","unit","nonnegative","assay"):
        assert term in reasons
    assert not db.execute("SELECT 1 FROM quarantine JOIN assay_result USING(source_record_id)").fetchone()
    row = db.execute("SELECT * FROM curated_results WHERE original_unit='uM'").fetchone()
    assert row["result_value"] == float(row["original_value"])*1000 and row["result_unit"] == "nM"
    ingest(db,load_profile(),feed("Alpha"))
    assert db.execute("SELECT count(*) FROM source_record").fetchone()[0] == 600
    assert records(db,sql)[0]["n"] == 292
    assert db.execute("SELECT count(*) FROM quarantine").fetchone()[0] == 16
    db.close()
