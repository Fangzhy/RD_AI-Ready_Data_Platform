"""Versioned source-to-target contracts and immutable input row identities."""
import csv
import hashlib
import io
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parents[1]
TARGETS = ("experiment_id", "compound_id", "assay_name", "result_value", "result_unit")


class Profile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_system: str = Field(min_length=1)
    version: str = Field(min_length=1)
    fields: dict[str, str]
    sample_column: str = 'SampleID'
    result_column: str = 'ObservationID'


def load_profile(name="alpha"):
    return Profile.model_validate_json((ROOT / f"configs/mappings_{name}.json").read_bytes())


def read_csv(content):
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig"), newline=""), strict=True)
    columns = reader.fieldnames or []
    if not columns or len(columns) != len(set(columns)) or any(not c.strip() for c in columns):
        raise ValueError("CSV requires distinct, nonempty column headers.")
    rows = list(reader)
    if any(None in row or None in row.values() for row in rows):
        raise ValueError("A CSV row has a different field count from its header.")
    return columns, rows


def check_mapping(profile, columns):
    targets = list(profile.fields.values())
    if len(set(targets)) != len(targets):
        raise ValueError("Multiple source fields map to the same target.")
    if set(profile.fields) - set(columns):
        raise ValueError("A mapped source column is absent from the input.")
    if set(targets) != set(TARGETS):
        raise ValueError("Assign each required target exactly once.")


def digest(data):
    encoded = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def source_id(system, batch, number, row):
    return digest([system, batch, number, row])
