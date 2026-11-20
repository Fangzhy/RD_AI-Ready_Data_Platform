import streamlit as st

from src.database import records
from src.workspace import session_db


def render():
    st.title("Data quality")
    db = session_db()
    st.dataframe(records(db, """SELECT source_system, quality_status, count(*) AS records
                     FROM quality_decision GROUP BY 1,2 ORDER BY 1,2"""), hide_index=True)
    accepted, quarantined = st.tabs(["Curated results", "Quarantine"])
    with accepted:
        st.dataframe(records(db, """SELECT s.row_number, d.quality_status, d.reasons, r.* FROM curated_results r
                         JOIN quality_decision d USING (source_record_id) JOIN source_record s USING (source_record_id)
                         ORDER BY r.result_id"""), hide_index=True)
    with quarantined:
        st.dataframe(records(db, """SELECT s.source_system,s.row_number,d.mapping_version,d.quality_status,q.reasons,q.recommendation,
                         s.raw_json,s.source_record_id FROM quarantine q JOIN quality_decision d USING(source_record_id) JOIN source_record s USING(source_record_id)
                         ORDER BY s.source_system,s.row_number"""), hide_index=True)
