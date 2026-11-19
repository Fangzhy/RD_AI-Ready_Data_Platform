import streamlit as st

from src.database import connect, records
from src.model import ENTITIES, describe, diagram


def render():
    st.title("Data modeling studio")
    db = connect()
    try:
        st.graphviz_chart(diagram(db))
        tables = [r["name"] for r in records(db, "SELECT name FROM sqlite_schema WHERE type='table' ORDER BY name")]
        table = st.selectbox("Inspect an entity or reference table", tables, index=tables.index("assay_result"))
        if table in ENTITIES:
            st.write(ENTITIES[table])
        columns, keys, ddl = describe(db, table)
        logical, physical = st.tabs(["Logical attributes and relationships", "Physical SQLite definition"])
        with logical:
            st.dataframe(columns, hide_index=True)
            if keys:
                st.dataframe(keys, hide_index=True)
        with physical:
            st.code(ddl, language="sql")
            for row in records(db, "SELECT sql FROM sqlite_schema WHERE type='index' AND tbl_name=? AND sql IS NOT NULL", (table,)):
                st.code(row["sql"], language="sql")
    finally:
        db.close()
