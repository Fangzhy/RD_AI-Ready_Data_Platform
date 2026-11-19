import csv
import hashlib

import pandas as pd
import streamlit as st

from src.exports import OUTPUT_COLUMNS, VIEW_SQL, pandas_code, snapshot
from src.fixtures import SYSTEMS, feed
from src.workspace import session_db
from src.ingestion import ingest
from src.mapping import TARGETS, Profile, load_profile, read_csv
from src.validation import preview


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
    batch = hashlib.sha256(content).hexdigest()
    try:
        active = Profile(**{**profile.model_dump(), 'version': version, 'fields': fields})
        accepted, flagged = preview(active, columns, rows, batch)
    except ValueError as error:
        st.error(str(error))
        return
    st.download_button("Download source CSV", content, f"{system}.csv")
    if st.button("Publish batch to the shared model", type="primary"):
        try:
            outcome = ingest(session_db(), active, content)
            st.success(f"Published {system} batch. Decisions: {outcome}")
        except ValueError as error:
            st.error(str(error))
    st.caption("The preview below checks mapped values. Publication also validates registered IDs, duplicates, assay terms and compatible units.")
    st.download_button("Export mapping JSON", active.model_dump_json(indent=2), "mapping.json")
    for label, records, names in [("Accepted", accepted, OUTPUT_COLUMNS),
                                  ("Flagged", flagged, OUTPUT_COLUMNS + ["reasons"])]:
        frame = pd.DataFrame(records, columns=names)
        st.subheader(f"{label} · {len(records)}")
        st.dataframe(frame, hide_index=True)
        st.download_button(f"Download {label.lower()} CSV", frame.to_csv(index=False), f"{label}.csv")
    with st.expander("Transformation and database exports"):
        st.code(pandas_code(active), language="python")
        st.code(VIEW_SQL, language="sql")
        st.download_button("Download SQLite snapshot", snapshot(accepted, flagged), "mapping.sqlite")
