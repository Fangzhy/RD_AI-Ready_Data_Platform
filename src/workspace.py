import streamlit as st

from src.database import connect
from src.fixtures import SYSTEMS, feed, seed_registry
from src.ingestion import ingest
from src.mapping import ROOT, load_profile


def build():
    db = connect()
    db.executescript((ROOT / "models/quality.sql").read_text(encoding="utf8"))
    seed_registry(db)
    for system in SYSTEMS:
        ingest(db, load_profile(system.lower()), feed(system))
    return db


def session_db():
    if "research_db" not in st.session_state:
        st.session_state.research_db = build()
    return st.session_state.research_db
