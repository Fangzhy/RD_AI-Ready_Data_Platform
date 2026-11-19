"""Reproducible fictional source feeds and separately governed reference registries."""
import csv
import io

from src.mapping import load_profile

ASSAYS = {
    "AS-BIND": ("Binding", "nM", ("Binding", "Binding readout")),
    "AS-ENZ": ("Enzyme activity", "%", ("Enzyme activity", "Activity readout")),
    "AS-VIA": ("Viability", "%", ("Viability", "Cell viability")),
}
SYSTEMS = ("Alpha", "Beta")


def sample_compound(experiment, sample):
    return ((experiment - 1) * 3 + sample - 1) % 20 + 1


def seed_registry(db):
    with db:
        db.executemany("INSERT INTO assay VALUES (?,?,?)",
                       [(k, v[0], v[1]) for k, v in ASSAYS.items()])
        for c in range(1, 21):
            db.execute("INSERT INTO compound VALUES (?,?)", (f"C-{c:03}", f"Test article {c:02}"))
        for system in SYSTEMS:
            tag = system[0]
            db.execute("INSERT INTO research_project VALUES (?,?)", (tag, system))
            for c in range(1, 21):
                db.execute("INSERT INTO compound_crosswalk VALUES (?,?,?)",
                           (system, f"{tag}-C{c:02}", f"C-{c:03}"))
            for e in range(1, 51):
                eid = f"EXP-{tag}{e:03}"
                db.execute("INSERT INTO experiment VALUES (?,?,?)", (eid, tag, f"{system} screening {e:03}"))
                db.execute("INSERT INTO experiment_crosswalk VALUES (?,?,?)", (system, f"{tag}-E{e:03}", eid))
                for s in range(1, 4):
                    sid = f"S-{tag}{e:03}-{s}"
                    db.execute("INSERT INTO sample VALUES (?,?,?)", (sid, eid, f"C-{sample_compound(e,s):03}"))
                    db.execute("INSERT INTO sample_crosswalk VALUES (?,?,?)", (system, f"{tag}-{e:03}/{s}", sid))


def feed(system):
    p = load_profile(system.lower())
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow([*p.fields, p.sample_column, p.result_column])
    tag = system[0]
    for i in range(300):
        e, s = i // 6 + 1, i // 2 % 3 + 1
        term, unit, aliases = list(ASSAYS.values())[i % 3]
        value = str((i * 7 + (2 if system == "Beta" else 1)) % 97 + 1)
        if unit == "nM" and i % 2:
            unit, value = "uM", f"0.{int(value):03}"
        row = [f"{tag}-E{e:03}", f"{tag}-C{sample_compound(e,s):02}", aliases[system == "Beta"],
               value, unit, f"{tag}-{e:03}/{s}", f"{i+1:04}"]
        defects = {10: (4, ""), 20: (3, "trace"), 30: (5, "unknown"), 40: (1, "unknown"),
                   50: (4, "mg"), 60: (6, "0060"), 70: (2, "Unclassified")}
        if i in defects:
            j, row_value = defects[i]
            row[j] = row_value
        writer.writerow(row)
    return output.getvalue().encode()
