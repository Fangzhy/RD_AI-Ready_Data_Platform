import csv
import hashlib

import pandas as pd
import streamlit as st

from src.exports import OUTPUT_COLUMNS, VIEW_SQL, pandas_code, snapshot
from src.mapping import ROOT, TARGETS, Profile, load_profile, read_csv
from src.validation import preview


def render():
    st.title("Schema mapping")
    st.write("Map local result columns to the shared screening schema and review each quality decision.")
    profile = load_profile()
    upload = st.file_uploader("Source CSV", type="csv")
    content = upload.getvalue() if upload else (ROOT / "data/synthetic_raw/alpha.csv").read_bytes()
    config = st.file_uploader("Import a mapping profile", type="json")
    try:
        if config:
            profile = Profile.model_validate_json(config.getvalue())
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
        active = Profile(source_system=profile.source_system, version=version, fields=fields)
        accepted, flagged = preview(active, columns, rows, batch)
    except ValueError as error:
        st.error(str(error))
        return
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
