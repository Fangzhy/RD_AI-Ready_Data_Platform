import sqlite3

from src.mapping import ROOT


def connect():
    db = sqlite3.connect(":memory:", check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.executescript((ROOT / "models/physical_schema.sql").read_text(encoding="utf8"))
    return db


def records(db, sql, params=()):
    return [dict(row) for row in db.execute(sql, params)]
