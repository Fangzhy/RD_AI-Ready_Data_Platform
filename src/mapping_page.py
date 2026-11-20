import csv

import pandas as pd
import streamlit as st

from src.exports import OUTPUT_COLUMNS, VIEW_SQL, pandas_code, snapshot
from src.fixtures import SYSTEMS, feed
from src.workspace import session_db
from src.ingestion import ingest
from src.mapping import TARGETS, Profile, load_profile, read_csv
from src.validation import review


def render():
    st.title("Schema mapping")
    st.write("Map local result columns to the shared screening schema and review each quality decision.")
    system = st.selectbox('Source system', SYSTEMS)
    profile = load_profile(system.lower())
    upload = st.file_uploader("Source CSV", type="csv")
    content = upload.getvalue() if upload else feed(system)
    config = st.file_uploader("Import a mapping profile", type="json")
    try:
        if config:
            profile = Profile.model_validate_json(config.getvalue())
        if profile.source_system != system:
            raise ValueError('Select the source system named in the imported profile.')
        columns, rows = read_csv(content)
    except (ValueError, csv.Error) as error:
        st.error(str(error))
        return
    st.subheader("Source records")
    st.dataframe(pd.DataFrame(rows, columns=columns), hide_index=True)
    version = st.text_input("Mapping version", profile.version, key=f"version-{profile.version}")
    fields = {}
    with st.expander("Edit field assignments", expanded=False):
        options = ["(skip)", *TARGETS]
        for column in columns:
            default = profile.fields.get(column)
            selected = st.selectbox(column, options, index=options.index(default) if default in options else 0,
                                    key=f"{profile.model_dump_json()}-{column}")
            if selected != "(skip)":
                fields[column] = selected
    db = session_db()
    try:
        active = Profile(**{**profile.model_dump(), 'version': version, 'fields': fields})
        batch = review(db, active, content)
    except ValueError as error:
        st.error(str(error))
        return
    st.download_button("Download source CSV", content, f"{system}.csv")
    if st.button("Publish batch to the shared model", type="primary"):
        try:
            outcome = ingest(db, active, content)
            st.session_state.last_publication = (system, batch.batch_id)
            st.success(f"Published {system} batch. Decisions: {outcome}")
        except ValueError as error:
            st.error(str(error))
    if st.session_state.get("last_publication") == (system, batch.batch_id):
        st.code(batch.batch_id, language=None)
        if st.button("Find this batch in RAG"):
            from src import rag_page
            st.session_state["open_batch"] = (system, batch.batch_id)
            st.switch_page(st.Page(rag_page.render, title="RAG assistant", url_path="assistant"))
    st.download_button("Export mapping JSON", active.model_dump_json(indent=2), "mapping.json")
    decisions = [d.summary(active.version) for d in batch.decisions]
    frame = pd.DataFrame(decisions, columns=OUTPUT_COLUMNS)
    st.subheader("Row decisions")
    st.caption("Preview uses the publication rules and current registry. Row numbers count data records starting at 1.")
    st.dataframe(frame, hide_index=True)
    accepted = [r for r in decisions if r["quality_status"] != "rejected"]
    flagged = [r for r in decisions if r["quality_status"] == "rejected"]
    for label, records in [("Accepted", accepted), ("Flagged", flagged)]:
        subset = pd.DataFrame(records, columns=OUTPUT_COLUMNS)
        st.download_button(f"Download {label.lower()} CSV", subset.to_csv(index=False), f"{label}.csv")
    with st.expander("Transformation and database exports"):
        st.code(pandas_code(active), language="python")
        st.code(VIEW_SQL, language="sql")
        st.download_button("Download SQLite snapshot", snapshot(accepted, flagged), "mapping.sqlite")
