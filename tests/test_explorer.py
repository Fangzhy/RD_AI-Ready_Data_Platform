from fastapi.testclient import TestClient
import pytest

from src.api import app
from src.explorer import QUERIES, query
from src.workspace import build


def test_readonly_cross_project_and_pagination():
    db = build()
    names, rows, clipped = query(db,QUERIES["Across projects"])
    assert {r[0] for r in rows} == {"A","B"} and not clipped
    assert rows == query(db,QUERIES["Across projects"])[1]
    for sql in ("DELETE FROM curated_results","SELECT * FROM document","PRAGMA database_list"):
        with pytest.raises(ValueError):
            query(db,sql)
    with TestClient(app) as client:
        expected = dict(db.execute("SELECT * FROM curated_results ORDER BY result_id LIMIT 1 OFFSET 1").fetchone())
        assert client.get("/assay-results?limit=1&offset=1").json() == [expected]
        assert client.get("/assay-results?limit=101").status_code == 422
        assert client.get("/assay-results?offset=-1").status_code == 422
        assert client.get("/experiments/EXP-B001").json()["project_id"] == "B"
        assert client.get("/compounds/C-001").json()["compound_id"] == "C-001"
        assert client.get("/experiments/unknown").status_code == 404
    db.close()
