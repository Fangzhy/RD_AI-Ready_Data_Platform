import streamlit as st

from src import mapping_page, model_page

st.set_page_config(page_title="R&D Data Platform", layout="wide")
st.navigation([
    st.Page(mapping_page.render, title="Schema mapping", url_path="mapping", default=True),
    st.Page(model_page.render, title="Data modeling studio", url_path="model"),
]).run()
