import json

import pandas as pd
import streamlit as st

from src.contracts import result_page
from src.explorer import QUERIES, published_db, query
from src.workspace import session_db


def render():
    st.title("AI-ready data explorer")
    db = session_db()
    selected = st.selectbox("Start from a query", list(QUERIES))
    sql = st.text_area("Read-only SQL", QUERIES[selected], height=160, key=f"sql-{selected}")
    try:
        names, rows, truncated = query(db,sql)
        st.dataframe(pd.DataFrame(rows,columns=names),hide_index=True)
        st.caption(f"Showing {len(rows)} rows." + (" Preview limited to 200." if truncated else ""))
    except ValueError as error:
        st.error(str(error))
    with st.expander("JSON and API access"):
        project = st.selectbox("Project filter", ["All","A","B"])
        data = [r.model_dump() for r in result_page(db, None if project=="All" else project)]
        st.json(data[:1])
        st.download_button("Download JSON page",json.dumps(data,indent=2),"assay-results.json")
        st.code("GET /experiments/EXP-A001\nGET /compounds/C-001\nGET /assay-results?project_id=A&limit=25&offset=0")
        snap = published_db(db)
        try:
            st.download_button("Download published SQLite database",snap.serialize(),"published.sqlite")
        finally:
            snap.close()
