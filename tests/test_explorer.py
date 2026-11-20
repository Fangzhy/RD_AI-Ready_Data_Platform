import asyncio

import httpx
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
    async def check_api():
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                expected = dict(db.execute("SELECT * FROM curated_results ORDER BY result_id LIMIT 1 OFFSET 1").fetchone())
                assert (await client.get("/assay-results?limit=1&offset=1")).json() == [expected]
                assert (await client.get("/assay-results?limit=101")).status_code == 422
                assert (await client.get("/assay-results?offset=-1")).status_code == 422
                assert (await client.get("/experiments/EXP-B001")).json()["project_id"] == "B"
                assert (await client.get("/compounds/C-001")).json()["compound_id"] == "C-001"
                assert (await client.get("/experiments/unknown")).status_code == 404

    asyncio.run(check_api())
    db.close()
