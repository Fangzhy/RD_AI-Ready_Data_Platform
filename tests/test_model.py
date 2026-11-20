import sqlite3

import pytest

from src.database import connect
from src.model import ENTITIES, describe, diagram


def test_physical_keys_and_join():
    db = connect()
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_schema WHERE type='table'")}
    for table in tables:
        assert all(k["parent"] in tables for k in describe(db, table)[1])
    assert ENTITIES.keys() <= tables
    assert "assay_result" in diagram(db).source
    db.executescript("""
        INSERT INTO research_project VALUES ('A','Alpha');
        INSERT INTO experiment VALUES ('E','A','Pilot');
        INSERT INTO compound VALUES ('C','Test article');
        INSERT INTO sample VALUES ('S','E','C');
        INSERT INTO assay VALUES ('B','Binding','nM');
        INSERT INTO assay_run VALUES ('U','E','B');
        INSERT INTO source_record VALUES ('SRC','Alpha','file',1,'{}');
        INSERT INTO assay_result VALUES ('R','E','S','U',12,'nM','12','nM','SRC','1');
    """)
    row = db.execute("SELECT * FROM curated_results").fetchone()
    assert [row[k] for k in ("experiment_id","sample_id","compound_id","assay_id")] == ["E","S","C","B"]
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO sample VALUES ('bad','E','absent')")
    assert not db.execute("PRAGMA foreign_key_check").fetchall()
    db.close()
