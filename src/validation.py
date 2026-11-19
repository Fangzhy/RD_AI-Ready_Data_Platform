"""Illustrative result checks for the mapping preview."""
import math

from src.mapping import check_mapping, source_id

UNITS = {"nM", "uM", "%"}

def preview(profile, columns, rows, batch):
    check_mapping(profile, columns)
    accepted, flagged = [], []
    for number, raw in enumerate(rows, 1):
        mapped = {target: raw[source].strip() for source, target in profile.fields.items()}
        issues = [f"Missing {field}" for field, value in mapped.items() if not value]
        try:
            value = float(mapped["result_value"])
            if not math.isfinite(value) or value < 0:
                raise ValueError
        except ValueError:
            issues.append("Expected a finite nonnegative result")
        if mapped["result_unit"] and mapped["result_unit"] not in UNITS:
            issues.append("Unknown unit")
        mapped.update(source_record_id=source_id(profile.source_system, batch, number, raw),
                      mapping_version=profile.version)
        if issues:
            flagged.append(dict(mapped, reasons=" | ".join(issues)))
        else:
            accepted.append(dict(mapped, result_value=value))
    return accepted, flagged
