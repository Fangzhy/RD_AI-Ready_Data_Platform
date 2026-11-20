import sqlite3

import pytest

from src.exports import snapshot
from src.mapping import ROOT, Profile, check_mapping, load_profile
from src.validation import review
from src.workspace import build


def test_roundtrip_and_failures():
    profile = load_profile()
    assert Profile.model_validate_json(profile.model_dump_json()) == profile
    workspace = build()
    content = (ROOT / "data/synthetic_raw/alpha.csv").read_bytes()
    batch = review(workspace, profile, content)
    assert [d.status for d in batch.decisions] == ["accepted", "corrected", "rejected", "rejected"]
    assert "nonnegative" in batch.decisions[2].reason
    assert "unit" in batch.decisions[3].reason
    assert review(workspace, profile, content) == batch
    valid = [d.summary(profile.version) for d in batch.decisions if d.status != "rejected"]
    failed = [d.summary(profile.version) for d in batch.decisions if d.status == "rejected"]
    workspace.close()
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
