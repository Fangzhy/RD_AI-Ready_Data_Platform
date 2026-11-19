"""Materialize the published data contract for read-only SQL and external consumers."""
import sqlite3
import time

from src.database import records

QUERIES = {
    "Across projects": """SELECT project_id, assay_name, result_unit, COUNT(*) AS measurements,
       ROUND(AVG(result_value), 2) AS mean_value
FROM curated_results
GROUP BY project_id, assay_name, result_unit
ORDER BY assay_name, project_id""",
    "Follow one compound": """SELECT project_id, experiment_id, compound_id, assay_name, result_value, result_unit
FROM curated_results WHERE compound_id = 'C-001'
ORDER BY project_id, experiment_id, result_id""",
    "Original and converted values": """SELECT result_id, original_value, original_unit, result_value, result_unit
FROM curated_results WHERE original_unit <> result_unit
ORDER BY result_id""",
}


def published_db(db):
    dest = sqlite3.connect(":memory:", check_same_thread=False)
    dest.row_factory = sqlite3.Row
    for table in ("experiment","compound","curated_results"):
        schema = list(db.execute("SELECT name,type FROM pragma_table_info(?)", (table,)))
        columns = ", ".join(f'"{name}" {kind}' for name,kind in schema)
        dest.execute(f"CREATE TABLE {table} ({columns})")
        marks = ",".join("?" for _ in schema)
        dest.executemany(f"INSERT INTO {table} VALUES ({marks})", db.execute(f"SELECT * FROM {table}"))
    dest.commit()
    dest.execute("PRAGMA query_only=ON")
    return dest


def query(db, sql, limit=200):
    if not sql.strip() or len(sql)>16000:
        raise ValueError("Enter a SQL query within 16,000 characters.")
    view = published_db(db)
    deadline = time.monotonic() + 1.0
    allowed = {"count","avg","sum","min","max","round","abs","lower","upper","length","coalesce","like","substr"}
    def authorize(action, arg1, arg2, schema, trigger):
        if action in (sqlite3.SQLITE_SELECT,sqlite3.SQLITE_READ):
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_FUNCTION and arg2 in allowed:
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY
    try:
        view.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 100000)
        view.setlimit(sqlite3.SQLITE_LIMIT_COLUMN, 100)
        view.set_authorizer(authorize)
        view.set_progress_handler(lambda: int(time.monotonic()>deadline), 1000)
        cursor = view.execute(sql)
        data = cursor.fetchmany(limit+1)
        return [d[0] for d in cursor.description], [tuple(row) for row in data[:limit]], len(data)>limit
    except sqlite3.Error as error:
        raise ValueError(f"SQL query could not run: {error}") from error
    finally:
        view.close()
