import streamlit as st

from src.database import connect, records
from src.design import REQUIREMENTS
from src.model import ENTITIES, describe, diagram


def render():
    st.title("Data modeling studio")
    db = connect()
    try:
        st.subheader("Requirements and design decisions")
        requirement = st.selectbox("Scientific requirement", REQUIREMENTS, format_func=lambda r: r.need)
        st.markdown(f"**Modeled field**  \n`{requirement.entity}.{requirement.field}` — {requirement.definition}")
        st.markdown(f"**Key or relationship**  \n{requirement.relationship}")
        st.markdown(f"**Quality rule**  \n{requirement.quality_rule}")
        st.markdown(f"**Modeling decision**  \n{requirement.decision}")
        st.subheader("Entity relationships")
        st.graphviz_chart(diagram(db))
        tables = [r["name"] for r in records(db, "SELECT name FROM sqlite_schema WHERE type='table' ORDER BY name")]
        table = st.selectbox("Inspect an entity or reference table", tables, index=tables.index(requirement.entity),
                             key=f"inspect-{requirement.entity}")
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
