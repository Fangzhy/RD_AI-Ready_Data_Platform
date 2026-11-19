"""Atomic mapping, validation and publication of one identified source batch."""
from collections import Counter
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math

from src.taxonomy import resolve
from src.governance import now, start_run
from src.mapping import check_mapping, read_csv, source_id

REVIEW = "Review the original row against the source registry and versioned mapping."
UNIT_SCALE = {("nM", "nM"): 1, ("uM", "nM"): 1000, ("%", "%"): 1}


def lookup(db, entity, system, local):
    sql = f"SELECT {entity}_id FROM {entity}_crosswalk WHERE source_system=? AND local_id=?"
    row = db.execute(sql, (system, local)).fetchone()
    return row[0] if row else None


def register_profile(db, profile):
    key = (profile.source_system, profile.version)
    encoded = json.dumps(profile.model_dump(), sort_keys=True)
    old = db.execute("SELECT profile_json FROM mapping_profile WHERE source_system=? AND mapping_version=?", key).fetchone()
    if old and old[0] != encoded:
        raise ValueError("This mapping version already exists with different assignments. Choose a new version.")
    db.execute("INSERT OR IGNORE INTO mapping_profile VALUES (?,?,?)", (*key, encoded))


def assess(db, profile, row, duplicate, src):
    fields = {target: row[column].strip() for column, target in profile.fields.items()}
    system = profile.source_system
    sid = lookup(db, "sample", system, row[profile.sample_column].strip())
    eid = lookup(db, "experiment", system, fields["experiment_id"])
    cid = lookup(db, "compound", system, fields["compound_id"])
    issues = []
    field_issues = {}

    def flag(target, reason):
        issues.append(reason)
        field_issues.setdefault(target, []).append(reason)
    for field, value in [("sample", sid), ("experiment", eid), ("compound", cid)]:
        if value is None:
            flag(f"{field}_id", f"Unknown or missing {field} ID")
    if sid and cid and eid and not db.execute(
        "SELECT 1 FROM sample WHERE sample_id=? AND compound_id=? AND experiment_id=?", (sid,cid,eid)
    ).fetchone():
        flag("sample_id", "Sample has a different registered compound or experiment")
    local_id = row[profile.result_column].strip()
    rid = f"RES-{system}-{local_id}"
    if not local_id:
        flag("result_id", "Missing result ID")
    if duplicate or db.execute("SELECT 1 FROM assay_result WHERE result_id=? AND source_record_id<>?", (rid,src)).fetchone():
        flag("result_id", "Duplicate result ID")
    concept = resolve(fields["assay_name"], system)
    assay = term = unit = None
    if concept:
        assay, term, unit = concept["id"], concept["term"], concept["unit"]
    else:
        flag("assay_name", "Unknown assay term")
    scale = UNIT_SCALE.get((fields["result_unit"], unit))
    if scale is None:
        flag("result_unit", "Missing or incompatible result unit")
    number = None
    try:
        decimal_value = Decimal(fields["result_value"])
        if not decimal_value.is_finite() or decimal_value < 0:
            raise ValueError
        number = float(decimal_value * (scale or 1))
        if not math.isfinite(number) or (decimal_value and number == 0):
            raise ValueError
    except (InvalidOperation, ArithmeticError, ValueError):
        number = None
        flag("result_value", "Expected a finite nonnegative result")
    corrected = bool((scale and scale != 1) or (term and term != fields["assay_name"]))
    values = dict(experiment_id=eid, compound_id=cid, sample_id=sid, assay_name=term,
                  result_value=number if number is not None and math.isfinite(number) else None,
                  result_unit=unit if scale else None, result_id=rid)
    source_fields = {target:source for source,target in profile.fields.items()}
    assignments = {**profile.fields, profile.sample_column: "sample_id", profile.result_column: "result_id"}
    audit = []
    for col, target in assignments.items():
        reasons = field_issues.get(target, [])
        canonical = values[target]
        if reasons:
            operation = "rejected"
        elif target == "result_value":
            operation = "unit conversion" if scale != 1 else "numeric parse"
        elif target in ("compound_id","experiment_id","sample_id","result_id"):
            operation = "identifier mapping"
        elif str(canonical) != row[col]:
            operation = "normalized"
        else:
            operation = "copied"
        audit.append(dict(source=col,target=target,raw=row[col],canonical=canonical,
                          operation=operation,reasons=reasons))
    if not issues:
        run = f"RUN-{eid}-{assay}"
        db.execute("INSERT OR IGNORE INTO assay_run VALUES (?,?,?)", (run,eid,assay))
        db.execute("INSERT INTO assay_result VALUES (?,?,?,?,?,?,?,?,?,?)",
                   (rid,eid,sid,run,number,unit,row[source_fields["result_value"]],
                    row[source_fields["result_unit"]],src,profile.version))
    return ("rejected" if issues else "corrected" if corrected else "accepted"), issues, audit


def ingest(db, profile, content):
    columns, rows = read_csv(content)
    check_mapping(profile, columns)
    if not {profile.sample_column, profile.result_column} <= set(columns):
        raise ValueError(f"Publication needs {profile.sample_column} and {profile.result_column} from the registered source.")
    if len(set([*profile.fields, profile.sample_column, profile.result_column])) != len(profile.fields) + 2:
        raise ValueError("Sample and result identity columns must be distinct from mapped measurement columns.")
    batch = hashlib.sha256(content).hexdigest()
    counts = Counter(row[profile.result_column].strip() for row in rows)
    totals = Counter()
    with db:
        register_profile(db, profile)
        run, transformation = start_run(db, profile, batch)
        sources = [(source_id(profile.source_system,batch,i,row),row) for i,row in enumerate(rows,1)]
        for src, _ in sources:
            db.execute("DELETE FROM assay_result WHERE source_record_id=?", (src,))
        for i, (src,row) in enumerate(sources,1):
            db.execute("INSERT OR IGNORE INTO source_record VALUES (?,?,?,?,?)",
                       (src,profile.source_system,batch,i,json.dumps(row,ensure_ascii=False)))
            duplicate = counts[row[profile.result_column].strip()] > 1
            status, issues, audit = assess(db,profile,row,duplicate,src)
            reason = " | ".join(issues)
            db.execute("DELETE FROM quarantine WHERE source_record_id=?", (src,))
            db.execute("""INSERT INTO quality_decision VALUES (?,?,?,?,?,?)
                       ON CONFLICT(source_record_id) DO UPDATE SET mapping_version=excluded.mapping_version,
                       quality_status=excluded.quality_status,reasons=excluded.reasons,audit_json=excluded.audit_json""",
                       (src,profile.source_system,profile.version,status,reason,json.dumps(audit)))
            if issues:
                db.execute("INSERT INTO quarantine VALUES (?,?,?)", (src,reason,REVIEW))
            result_id = None if issues else audit[-1]["canonical"]
            db.execute("INSERT INTO lineage_event VALUES (?,?,?,?,?,?,?)",
                       (run,src,transformation,status,result_id,reason,json.dumps(audit)))
            totals[status] += 1
        db.execute("UPDATE dataset_catalog SET refreshed_at=? WHERE dataset='curated_results'", (now(),))
    return dict(totals)
