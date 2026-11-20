import sqlite3

import pandas as pd

from src.mapping import TARGETS

OUTPUT_COLUMNS = ["row_number", "quality_status", "reasons", "result_id", "sample_id", *TARGETS,
                  "assay_id", "source_record_id", "mapping_version"]
VIEW_SQL = "CREATE VIEW curated_results AS SELECT * FROM accepted_results"


def snapshot(accepted, flagged):
    db = sqlite3.connect(":memory:")
    try:
        for table, rows, columns in [
            ("accepted_results", accepted, OUTPUT_COLUMNS),
            ("flagged_results", flagged, OUTPUT_COLUMNS),
        ]:
            pd.DataFrame(rows, columns=columns).to_sql(table, db, index=False)
        db.execute(VIEW_SQL)
        return db.serialize()
    finally:
        db.close()


def pandas_code(profile):
    return (f"mapping = {profile.fields!r}\n"
            "mapped = raw[list(mapping)].rename(columns=mapping).copy()\n"
            "mapped['result_value'] = pd.to_numeric(mapped['result_value'], errors='coerce')")
