"""Read-only publication rules shared by preview and ingestion."""
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math

from src.taxonomy import resolve
from src.mapping import check_mapping, read_csv, source_id

UNIT_SCALE = {("nM", "nM"): 1, ("uM", "nM"): 1000, ("%", "%"): 1}


@dataclass
class Decision:
    row_number: int
    source_record_id: str
    raw: dict
    canonical: dict
    status: str
    reason: str
    audit: list

    def summary(self, version):
        return dict(row_number=self.row_number, quality_status=self.status, reasons=self.reason,
                    **self.canonical, source_record_id=self.source_record_id, mapping_version=version)


@dataclass
class BatchReview:
    batch_id: str
    profile_json: str
    decisions: list[Decision]


def lookup(db, entity, system, local):
    sql = f"SELECT {entity}_id FROM {entity}_crosswalk WHERE source_system=? AND local_id=?"
    row = db.execute(sql, (system, local)).fetchone()
    return row[0] if row else None


def check_profile(db, profile):
    key = (profile.source_system, profile.version)
    encoded = json.dumps(profile.model_dump(), sort_keys=True)
    old = db.execute("SELECT profile_json FROM mapping_profile WHERE source_system=? AND mapping_version=?", key).fetchone()
    if old and old[0] != encoded:
        raise ValueError("This mapping version already exists with different assignments. Choose a new version.")
    return encoded


def assess(db, profile, row, duplicate, src, row_number):
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
    if duplicate:
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
    corrections = []
    if term and term != fields["assay_name"]:
        corrections.append(f"Normalized assay {fields['assay_name']} to {term}")
    if scale and scale != 1:
        corrections.append(f"Converted {fields['result_unit']} to {unit} (×{scale})")
    values = dict(experiment_id=eid, compound_id=cid, sample_id=sid, assay_name=term,
                  result_value=number,
                  result_unit=unit if scale else None, result_id=rid)

    assignments = {**profile.fields, profile.sample_column: "sample_id", profile.result_column: "result_id"}
    audit = []
    for col, target in assignments.items():
        reasons = field_issues.get(target, [])
        canonical = values[target]
        if reasons:
            operation = "rejected"
        elif target == "result_value":
            operation = "unit conversion" if scale and scale != 1 else "numeric parse"
        elif target in ("compound_id","experiment_id","sample_id","result_id"):
            operation = "identifier mapping"
        elif str(canonical) != row[col]:
            operation = "normalized"
        else:
            operation = "copied"
        audit.append(dict(source=col,target=target,raw=row[col],canonical=canonical,
                          operation=operation,reasons=reasons))
    values["assay_id"] = assay
    if issues:
        status, reason = "rejected", " | ".join(issues)
    elif corrections:
        status, reason = "corrected", " | ".join(corrections)
    else:
        status, reason = "accepted", "All publication checks passed."
    return Decision(row_number, src, row, values, status, reason, audit)


def review(db, profile, content):
    """Evaluate a batch against the current registry and other published batches."""
    columns, rows = read_csv(content)
    check_mapping(profile, columns)
    if not {profile.sample_column, profile.result_column} <= set(columns):
        raise ValueError(f"The mapping requires {profile.sample_column} and {profile.result_column} from the registered source.")
    if len(set([*profile.fields, profile.sample_column, profile.result_column])) != len(profile.fields) + 2:
        raise ValueError("Sample and result identity columns must be distinct from mapped measurement columns.")
    batch = hashlib.sha256(content).hexdigest()
    counts = Counter(row[profile.result_column].strip() for row in rows)
    encoded = check_profile(db, profile)
    # Replaying this batch replaces its own results. Other batches retain their IDs.
    occupied = {r[0] for r in db.execute(
        """SELECT result_id FROM assay_result JOIN source_record USING(source_record_id)
           WHERE source_system=? AND batch_id<>?""", (profile.source_system, batch))}
    decisions = []
    for i, row in enumerate(rows, 1):
        local_id = row[profile.result_column].strip()
        duplicate = counts[local_id] > 1 or f"RES-{profile.source_system}-{local_id}" in occupied
        src = source_id(profile.source_system, batch, i, row)
        decisions.append(assess(db, profile, row, duplicate, src, i))
    return BatchReview(batch, encoded, decisions)
