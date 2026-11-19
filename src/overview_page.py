import streamlit as st

from src.database import records
from src.workspace import session_db


def render():
    st.title("Research data overview")
    st.write("Two synthetic screening projects share a compound registry and publish results into one SQLite model.")
    db = session_db()
    for column, (label, table) in zip(st.columns(4), [
        ("Source rows","source_record"), ("Curated results","assay_result"),
        ("Quarantined","quarantine"), ("Experiments","experiment")]):
        column.metric(label, db.execute(f"SELECT count(*) FROM {table}").fetchone()[0])
    st.subheader("Source decisions")
    st.dataframe(records(db, """SELECT source_system, mapping_version, quality_status, count(*) AS rows
                                FROM quality_decision GROUP BY 1,2,3 ORDER BY 1,2,3"""), hide_index=True)
    st.caption("Each browser session starts with the deterministic demonstration feeds. Uploaded batches live in that session.")
