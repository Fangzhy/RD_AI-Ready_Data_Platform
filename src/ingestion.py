"""Persist a batch and its shared quality decisions in one transaction."""
from collections import Counter
import json

from src.governance import now, start_run
from src.validation import review

REVIEW = "Review the original row against the source registry and versioned mapping."


def ingest(db, profile, content):
    totals = Counter()
    with db:
        # Acquire the SQLite writer lock before checking result IDs and mapping versions.
        if not db.in_transaction:
            db.execute("BEGIN IMMEDIATE")
        batch = review(db, profile, content)
        db.execute("INSERT OR IGNORE INTO mapping_profile VALUES (?,?,?)",
                   (profile.source_system, profile.version, batch.profile_json))
        run, transformation = start_run(db, profile, batch.batch_id)
        db.executemany("DELETE FROM assay_result WHERE source_record_id=?",
                       ((d.source_record_id,) for d in batch.decisions))
        source_fields = {target: source for source, target in profile.fields.items()}
        for d in batch.decisions:
            src = d.source_record_id
            db.execute("INSERT OR IGNORE INTO source_record VALUES (?,?,?,?,?)",
                       (src, profile.source_system, batch.batch_id, d.row_number, json.dumps(d.raw, ensure_ascii=False)))
            audit = json.dumps(d.audit)
            db.execute("""INSERT INTO quality_decision VALUES (?,?,?,?,?,?)
                       ON CONFLICT(source_record_id) DO UPDATE SET mapping_version=excluded.mapping_version,
                       quality_status=excluded.quality_status,reasons=excluded.reasons,audit_json=excluded.audit_json""",
                       (src, profile.source_system, profile.version, d.status, d.reason, audit))
            db.execute("DELETE FROM quarantine WHERE source_record_id=?", (src,))
            result_id = None
            if d.status == "rejected":
                db.execute("INSERT INTO quarantine VALUES (?,?,?)", (src, d.reason, REVIEW))
            else:
                row = d.canonical
                result_id = row["result_id"]
                eid, assay = row["experiment_id"], row["assay_id"]
                assay_run = f"RUN-{eid}-{assay}"
                db.execute("INSERT OR IGNORE INTO assay_run VALUES (?,?,?)", (assay_run, eid, assay))
                db.execute("INSERT INTO assay_result VALUES (?,?,?,?,?,?,?,?,?,?)",
                           (result_id, eid, row["sample_id"], assay_run, row["result_value"], row["result_unit"],
                            d.raw[source_fields["result_value"]], d.raw[source_fields["result_unit"]], src, profile.version))
            db.execute("INSERT INTO lineage_event VALUES (?,?,?,?,?,?,?)",
                       (run, src, transformation, d.status, result_id, d.reason, audit))
            totals[d.status] += 1
        db.execute("UPDATE dataset_catalog SET refreshed_at=? WHERE dataset='curated_results'", (now(),))
    return dict(totals)
