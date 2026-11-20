import json

import streamlit as st

from src.database import records
from src.governance import impact, trace, visible_documents
from src.workspace import session_db


def render():
    db = session_db()
    st.title("Metadata and lineage")
    upstream, downstream, catalog = st.tabs(["Trace a record","Mapping impact","Catalog and access"])
    with upstream:
        origin = st.session_state.pop("cited_origin", None)
        if origin:
            st.session_state["trace_input"] = origin[0]
        elif "trace_input" not in st.session_state:
            st.session_state["trace_input"] = st.query_params.get("record", "RES-Alpha-0001")
        key = st.text_input("Result or source record ID", key="trace_input").strip()
        history = trace(db, key)
        versions = sorted({event["mapping_version"] for event in history})
        version_key = f"trace-version-{key}"
        requested = origin[1] if origin else st.query_params.get("mapping_version")
        if requested in versions and (origin or version_key not in st.session_state):
            st.session_state[version_key] = requested
        version = st.selectbox("Trace mapping version", [None, *versions],
                               format_func=lambda v: v or "All versions", key=version_key)
        if version:
            history = [event for event in history if event["mapping_version"] == version]
        if history:
            for event in history:
                st.subheader(f"{event['source_system']} · {event['quality_status']}")
                st.json({k:v for k,v in event.items() if k not in ("audit_json","raw_json")})
                st.json(json.loads(event["raw_json"]))
                audit = json.loads(event["audit_json"])
                for field in audit:
                    field["canonical"] = "" if field["canonical"] is None else str(field["canonical"])
                st.dataframe(audit, hide_index=True)
        else:
            st.info("No lineage events match this identifier.")
    with downstream:
        profiles = records(db, "SELECT source_system,mapping_version FROM mapping_profile ORDER BY 1,2")
        selected = st.selectbox("Published mapping", profiles, format_func=lambda p: " / ".join(p.values()))
        rows, datasets = impact(db,selected["source_system"],selected["mapping_version"])
        st.write("Dependent datasets and search indexes")
        st.dataframe(datasets, hide_index=True)
        st.write("Decisions made with this version")
        st.dataframe(rows, hide_index=True)
    with catalog:
        st.dataframe(records(db,"SELECT * FROM dataset_catalog ORDER BY dataset"),hide_index=True)
        role = st.selectbox("Demonstration access role", ["reader","reviewer"], key="lineage_role")
        st.dataframe([{k:r[k] for k in ("document_id","version","title","access_class")}
                      for r in visible_documents(db,role)], hide_index=True)
