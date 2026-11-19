import streamlit as st

from src import mapping_page

st.set_page_config(page_title="R&D Data Platform", layout="wide")
mapping_page.render()
