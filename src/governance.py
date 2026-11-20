from datetime import datetime, timezone
import json
import uuid

from src.database import records
from src.mapping import digest


def now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def start_run(db, profile, batch):
    run = str(uuid.uuid4())
    db.execute("INSERT INTO ingestion_run VALUES (?,?,?,?,?)",
               (run,profile.source_system,profile.version,batch,now()))
    return run, digest(["harmonization-v1", profile.model_dump()])


def trace(db, search):
    return records(db, """SELECT i.loaded_at, i.source_system, i.mapping_version, l.*, s.batch_id, s.row_number,
                       s.raw_json FROM lineage_event l JOIN ingestion_run i USING(ingestion_run_id)
                       JOIN source_record s USING(source_record_id)
                       WHERE l.source_record_id IN (SELECT source_record_id FROM lineage_event WHERE curated_record_id=?) OR l.source_record_id=?
                       ORDER BY i.loaded_at DESC, i.ingestion_run_id""", (search,search))


def impact(db, system, version):
    impacted = records(db, """SELECT DISTINCT l.source_record_id, l.curated_record_id, l.quality_status
                          FROM lineage_event l JOIN ingestion_run i USING(ingestion_run_id)
                          WHERE i.source_system=? AND i.mapping_version=? ORDER BY l.source_record_id""",
                       (system,version))
    datasets = records(db, """WITH RECURSIVE affected(dataset) AS (
                   SELECT 'curated_results' UNION SELECT downstream FROM dataset_dependency
                   JOIN affected ON affected.dataset=upstream)
                   SELECT dataset FROM affected""") if any(r["curated_record_id"] for r in impacted) else []
    return impacted, datasets


def visible_documents(db, role="reader"):
    classes = ("public","restricted") if role == "reviewer" else ("public",)
    marks = ",".join("?" for _ in classes)
    return records(db, f"""SELECT * FROM document WHERE access_class IN ({marks}) AND lifecycle='current'
                            ORDER BY document_id,version""", classes)


def seed_documents(db):
    """Freeze a small report collection from the initially published synthetic data."""
    with db:
        for project in ("A","B"):
            for i in range(1,13):
                eid = f"EXP-{project}{i:03}"
                doc = f"DOC-{project}{i:03}"
                rows = db.execute("SELECT * FROM curated_results WHERE experiment_id=? ORDER BY result_id", (eid,)).fetchall()
                row = rows[(i-1) % len(rows)]
                title = f"{eid} screening report"
                scope = "restricted" if i % 4 == 0 else "public"
                body = (f"Observation\nExperiment {eid} recorded result {row['result_id']} for sample {row['sample_id']}.\n\n"
                        f"Measurement\nCompound {row['compound_id']} had a synthetic {row['assay_name']} measurement "
                        f"of {row['result_value']:g} {row['result_unit']} in {eid} ({row['result_id']}).")
                version = 2 if i == 1 else 1
                if version == 2:
                    db.execute("INSERT INTO document VALUES (?,?,?,?,?,?,?)",
                               (doc,1,eid,title,"Archived draft pending measurement review.",scope,"superseded"))
                db.execute("INSERT INTO document VALUES (?,?,?,?,?,?,?)", (doc,version,eid,title,body,scope,"current"))
                db.execute("INSERT INTO document_result VALUES (?,?,?,?,?)",
                           (doc,version,row["result_id"],row["source_record_id"],json.dumps(dict(row))))
        db.execute("UPDATE dataset_catalog SET refreshed_at=? WHERE dataset='document_evidence'", (now(),))
