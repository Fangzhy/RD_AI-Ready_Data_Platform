import json

import streamlit as st

from src.evaluation import evaluate
from src.governance import now, visible_documents
from src.openrouter import GenerationError, generate
from src.retrieval import INSUFFICIENT, measurement_evidence, retrieve, search_measurements, supported
from src.workspace import session_db


def generation_button(question, candidates, key):
    if st.button("Generate cited answer with OpenRouter", type="primary", key=f"generate-{key}"):
        try:
            answer, model = generate(question, candidates)
            st.caption(f"Model-selected text · {model}")
            st.success(answer["quote"])
            st.text(answer["citation"])
        except GenerationError as error:
            st.info(str(error))
    st.caption("Generation sends the question and selected context to the configured free model.")


def show_measurement(db, item):
    st.caption("Generated context from curated fields")
    st.text(item.text)
    st.caption("Original CSV evidence")
    st.text(item.source_citation)
    raw = db.execute("SELECT raw_json FROM source_record WHERE source_record_id=?", (item.source_record_id,)).fetchone()
    st.json(json.loads(raw[0]))
    if st.button("Open cited mapping and lineage", key=f"lineage-{item.source_record_id}"):
        from src import lineage_page
        st.session_state["cited_origin"] = (item.source_record_id, item.mapping_version)
        st.switch_page(st.Page(lineage_page.render, title="Metadata and lineage", url_path="lineage"))


def structured_search(db):
    sources = [r[0] for r in db.execute("SELECT DISTINCT source_system FROM source_record ORDER BY 1")]
    left, right = st.columns(2)
    source = left.selectbox("Source system", sources, index=None, key="record_source")
    batches = [r[0] for r in db.execute(
        "SELECT DISTINCT batch_id FROM source_record WHERE (? IS NULL OR source_system=?) ORDER BY 1", (source, source))]
    batch = right.selectbox("Batch ID", batches, index=None, key="record_batch")
    experiment = left.text_input("Experiment ID", placeholder="EXP-A001", key="record_experiment").strip()
    result = right.text_input("Result ID", placeholder="RES-Alpha-0001", key="record_result").strip()
    if not any((source, batch, experiment, result)):
        st.info("Choose a source or batch, or enter a canonical experiment or result ID.")
        return
    matches = search_measurements(db, experiment_id=experiment, source_system=source, batch_id=batch, result_id=result)
    if not matches:
        st.info("No published measurements match these filters.")
        return
    st.caption(f"{len(matches)} published measurements")
    columns = ("result_id", "experiment_id", "source_system", "row_number", "result_value", "result_unit",
               "quality_status", "mapping_version", "batch_id")
    st.dataframe([{k: row[k] for k in columns} for row in matches], hide_index=True)
    row = st.selectbox("Inspect a result", matches, format_func=lambda r: r["result_id"])
    item = measurement_evidence(row)
    show_measurement(db, item)
    generation_button(f"What measurement was recorded for {row['result_id']}?", [item], "structured")


def document_search(db, role):
    target = st.query_params.get("document")
    if target:
        version = st.query_params.get("version")
        doc = next((d for d in visible_documents(db,role) if d["document_id"]==target and str(d["version"])==version),None)
        if doc:
            st.subheader(f"{doc['document_id']} · version {doc['version']}")
            st.text(doc["body"])
        else:
            st.info("This report version is unavailable for the selected role.")
    question = st.text_input("Ask about a recorded measurement", "What measurement was recorded in EXP-A001?", max_chars=500)
    mode = st.radio("Retrieval mode",["aware","baseline"],horizontal=True,
                    format_func=lambda s: "SQL relationships + TF-IDF" if s=="aware" else "TF-IDF baseline")
    hits = retrieve(db,question,role,mode)
    with db:
        db.execute("UPDATE dataset_catalog SET refreshed_at=? WHERE dataset='evidence_search'",(now(),))
    candidates = supported(question,hits)
    st.subheader("Answer")
    if candidates:
        item = candidates[0]
        if item.mapping_version:
            show_measurement(db, item)
        else:
            st.caption("Excerpt from the cited report")
            st.write(item.text)
            st.markdown(f"[{item.citation}]({item.source_link})")
        generation_button(question, candidates, "lookup")
    else:
        st.info(INSUFFICIENT)
    st.subheader("Retrieved evidence")
    if not hits:
        st.write("No matching evidence.")
    for h in hits:
        with st.expander(h.citation):
            st.caption("Generated context from curated fields" if h.mapping_version else "Report excerpt")
            st.text(h.text)
            st.write(f"{h.access_class} · source record {h.source_record_id}")
            if h.mapping_version:
                st.text(h.source_citation)
            else:
                st.markdown(f"[Open source]({h.source_link})")


def render():
    st.title("RAG assistant")
    db = session_db()
    role = st.selectbox("Demonstration access role", ["reader","reviewer"], key="rag_role")
    search, benchmark = st.tabs(["Evidence lookup","Retrieval evaluation"])
    with search:
        batch = st.session_state.pop("open_batch", None)
        if batch:
            st.session_state.update(rag_mode="Structured records", record_source=batch[0], record_batch=batch[1],
                                    record_experiment="", record_result="")
        mode = st.radio("Search collection", ["Reports and questions", "Structured records"],
                        horizontal=True, key="rag_mode")
        if mode == "Structured records":
            structured_search(db)
        else:
            document_search(db, role)
    with benchmark:
        st.write("Fourteen fixed lookups score exact section citations and result values. Recall@5 uses answerable questions. Citation correctness uses answers that issued a citation.")
        if st.button("Evaluate seeded demonstration"):
            from src.workspace import build
            fixture = build()
            try:
                metrics, details = evaluate(fixture)
            finally:
                fixture.close()
            st.dataframe(metrics,hide_index=True)
            st.dataframe(details,hide_index=True)
