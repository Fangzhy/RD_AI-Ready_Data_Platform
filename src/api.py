"""Serve deterministic fixtures or a published SQLite snapshot exported from the UI."""
from contextlib import asynccontextmanager
import os
from pathlib import Path
import sqlite3

from fastapi import FastAPI, HTTPException, Query, Request

from src.contracts import AssayResult, Compound, Experiment, result_page
from src.explorer import published_db
from src.workspace import build


@asynccontextmanager
async def lifespan(app):
    path = os.getenv("RD_API_SNAPSHOT")
    if path:
        db = sqlite3.connect(Path(path).resolve().as_uri()+"?mode=ro", uri=True, check_same_thread=False)
        db.row_factory = sqlite3.Row
    else:
        source = build()
        try:
            db = published_db(source)
        finally:
            source.close()
    app.state.db = db
    try:
        yield
    finally:
        db.close()


app = FastAPI(title="Synthetic R&D data API", version="1.0", lifespan=lifespan)


def entity(request, table, field, value):
    row = request.app.state.db.execute(f"SELECT * FROM {table} WHERE {field}=?", (value,)).fetchone()
    if row is None:
        raise HTTPException(404,"Unknown identifier")
    return dict(row)


@app.get("/experiments/{experiment_id}", response_model=Experiment)
def experiment(experiment_id: str, request: Request):
    return entity(request,"experiment","experiment_id",experiment_id)


@app.get("/compounds/{compound_id}", response_model=Compound)
def compound(compound_id: str, request: Request):
    return entity(request,"compound","compound_id",compound_id)


@app.get("/assay-results", response_model=list[AssayResult])
def results(request: Request, project_id: str | None = None, compound_id: str | None = None,
            limit: int = Query(25,ge=1,le=100), offset: int = Query(0,ge=0)):
    return result_page(request.app.state.db,project_id,compound_id,limit,offset)
