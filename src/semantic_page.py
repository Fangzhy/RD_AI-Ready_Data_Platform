from graphviz import Digraph
import streamlit as st

from src.database import records
from src.graph import RELATIONS, build_graph, paths
from src.taxonomy import CONCEPTS, VOCAB, resolve
from src.workspace import session_db


def render():
    st.title("Taxonomy and ontology")
    query = st.text_input("Find an assay by preferred term or source synonym", "Cell viability")
    concept = resolve(query)
    if concept:
        st.write(f"{VOCAB['categories'][concept['category']]} → {concept['term']} ({concept['id']})")
    else:
        st.info("No unique concept matches this term.")
    st.dataframe([dict(concept_id=c["id"], preferred_term=c["term"], category=VOCAB["categories"][c["category"]],
                       **c["aliases"]) for c in CONCEPTS.values()], hide_index=True)
    st.subheader("Compound evidence")
    db = session_db()
    compound = st.selectbox("Compound", [r["compound_id"] for r in records(db,"SELECT compound_id FROM compound ORDER BY 1")])
    graph = build_graph(db)
    options = paths(graph,compound)
    if options:
        row = st.selectbox("Supporting result", options, format_func=lambda r: f"{r['result']} · {r['assay']}")
        chart = Digraph(graph_attr={"rankdir":"LR"})
        chart.edge(compound,row["assay"],label="testedIn")
        chart.edge(row["assay"],row["result"],label="hasResult")
        for subject in (row["assay"],row["result"]):
            for _,obj,edge in graph.out_edges(subject,data=True):
                if edge["relation"] in ("measuresTarget","reportedIn"):
                    chart.edge(subject,obj,label=edge["relation"])
        st.graphviz_chart(chart)
        st.write("Source record", row["source_record_id"])
        st.dataframe(options,hide_index=True)
    st.caption("A tested-in relationship records an observation. Activity against a target would require a separate supported assertion.")
    with st.expander("Relation definitions and provenance"):
        st.dataframe([dict(relation=k,domain=v[0],range=v[1],meaning=v[2]) for k,v in RELATIONS.items()],hide_index=True)
        st.dataframe([dict(subject=s,object=o,**v) for s,o,v in graph.edges(data=True)
                      if s == compound or (options and s in (row["assay"],row["result"]))],hide_index=True)
