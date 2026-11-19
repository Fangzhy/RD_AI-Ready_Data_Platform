import streamlit as st

from src.evaluation import evaluate
from src.governance import now, visible_documents
from src.openrouter import GenerationError, generate
from src.retrieval import INSUFFICIENT, retrieve, supported
from src.workspace import session_db


def render():
    st.title("RAG assistant")
    db = session_db()
    role = st.selectbox("Demonstration access role", ["reader","reviewer"],key="rag_role")
    search, benchmark = st.tabs(["Evidence lookup","Retrieval evaluation"])
    with search:
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
            st.write(item.text)
            st.markdown(f"[{item.citation}]({item.source_link})")
            if st.button("Generate cited answer with OpenRouter",type="primary"):
                try:
                    answer, model = generate(question,candidates)
                    st.success(answer["quote"])
                    st.write(f"{answer['citation']} · {model}")
                except GenerationError as error:
                    st.info(str(error))
            st.caption("Generation sends the question and selected evidence to the configured free model.")
        else:
            st.info(INSUFFICIENT)
        st.subheader("Retrieved evidence")
        if not hits:
            st.write("No matching evidence.")
        for h in hits:
            with st.expander(h.citation):
                st.text(h.text)
                st.write(f"{h.access_class} · source record {h.source_record_id}")
                st.markdown(f"[Open source]({h.source_link})")
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
