import streamlit as st

from src import mapping_page, model_page, overview_page, quality_page, lineage_page, semantic_page

st.set_page_config(page_title="R&D Data Platform", layout="wide")
st.navigation([
    st.Page(overview_page.render, title="Overview", url_path="overview"),
    st.Page(mapping_page.render, title="Schema mapping", url_path="mapping", default=True),
    st.Page(model_page.render, title="Data modeling studio", url_path="model"),
    st.Page(quality_page.render, title="Data quality", url_path="quality"),
    st.Page(lineage_page.render, title="Metadata and lineage", url_path="lineage"),
    st.Page(semantic_page.render, title="Taxonomy and ontology", url_path="semantics"),
]).run()
