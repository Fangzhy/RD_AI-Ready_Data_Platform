from pydantic import BaseModel

from src.database import records


class Experiment(BaseModel):
    experiment_id: str
    project_id: str
    title: str


class Compound(BaseModel):
    compound_id: str
    label: str


class AssayResult(BaseModel):
    result_id: str
    project_id: str
    experiment_id: str
    sample_id: str
    compound_id: str
    assay_id: str
    assay_name: str
    run_id: str
    result_value: float
    result_unit: str
    original_value: str
    original_unit: str
    source_system: str
    source_record_id: str
    mapping_version: str


def result_page(db, project_id=None, compound_id=None, limit=25, offset=0):
    if not 1 <= limit <= 100 or offset < 0:
        raise ValueError("Limit must be 1–100 and offset must be nonnegative.")
    where, values = [], []
    for field, value in (("project_id",project_id), ("compound_id",compound_id)):
        if value is not None:
            where.append(f"{field}=?")
            values.append(value)
    clause = " WHERE " + " AND ".join(where) if where else ""
    rows = records(db, "SELECT * FROM curated_results" + clause + " ORDER BY result_id LIMIT ? OFFSET ?",
                   (*values,limit,offset))
    return [AssayResult.model_validate(row) for row in rows]
