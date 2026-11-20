from graphviz import Digraph

from src.database import records

ENTITIES = {
    "research_project": "A research team's collection of related experiments.",
    "experiment": "A planned investigation within one research project.",
    "compound": "A registered synthetic test article shared across projects.",
    "sample": "An identified instance of one compound assigned to an experiment.",
    "assay": "A defined measurement with an approved result unit.",
    "assay_run": "An execution of an assay within an experiment.",
    "assay_result": "A measured value for one sample in one assay run.",
    "source_record": "One immutable input row in an identified source batch.",
    "document": "A versioned research note associated with an experiment.",
}


def describe(db, table):
    ddl = db.execute("SELECT sql FROM sqlite_schema WHERE type='table' AND name=?", (table,)).fetchone()
    if not ddl:
        raise ValueError("Unknown entity")
    columns = records(db, "SELECT name, type, [notnull] AS required, pk AS key_position FROM pragma_table_info(?)", (table,))
    keys = records(db, 'SELECT id, seq, [from] AS child_key, [table] AS parent, [to] AS parent_key FROM pragma_foreign_key_list(?)', (table,))
    return columns, keys, ddl[0]


def diagram(db):
    graph = Digraph(graph_attr={"rankdir": "LR"}, node_attr={"shape": "box"})
    for table in ENTITIES:
        graph.node(table)
        _, keys, _ = describe(db, table)
        for key in keys:
            if key["seq"] == 0:
                label = "1 : 0..1" if key["child_key"] == "source_record_id" else "1 : many"
                graph.edge(key["parent"], table, label=label)
    return graph
