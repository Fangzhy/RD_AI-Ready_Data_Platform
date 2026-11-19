import sqlite3

import pytest

from src.exports import snapshot
from src.mapping import ROOT, Profile, check_mapping, load_profile, read_csv
from src.validation import preview


def test_roundtrip_and_failures():
    profile = load_profile()
    assert Profile.model_validate_json(profile.model_dump_json()) == profile
    columns, rows = read_csv((ROOT / "data/synthetic_raw/alpha.csv").read_bytes())
    valid, failed = preview(profile, columns, rows, "fixture")
    assert len(valid) == len(failed) == 2
    assert "nonnegative" in failed[0]["reasons"]
    assert "Missing result_unit" in failed[1]["reasons"]
    assert preview(profile, columns, rows, "fixture") == (valid, failed)
    db = sqlite3.connect(":memory:")
    db.deserialize(snapshot(valid, failed))
    assert db.execute("SELECT count(*) FROM curated_results").fetchone() == (2,)
    db.close()


@pytest.mark.parametrize("change", ["duplicate", "missing", "unknown"])
def test_invalid_profile(change):
    profile = load_profile()
    columns = list(profile.fields)
    if change == "duplicate":
        profile.fields["TestName"] = "compound_id"
    elif change == "missing":
        del profile.fields["TestName"]
    else:
        columns.remove("ExpNumber")
    with pytest.raises(ValueError):
        check_mapping(profile, columns)


def test_ui():
    from streamlit.testing.v1 import AppTest
    assert not AppTest.from_file(str(ROOT / "app.py")).run(timeout=30).exception
