"""Typed assertions linked to source records, current reports, or the vocabulary."""
import networkx as nx

from src.database import records
from src.governance import visible_documents
from src.taxonomy import CONCEPTS, VOCAB

RELATIONS = {
    "testedIn": ("Compound", "Assay", "A source records a measurement of the compound with this assay."),
    "hasResult": ("Assay", "Result", "The assay produced this measured result."),
    "usesSample": ("Experiment", "Sample", "The experiment includes this registered sample."),
    "measuresTarget": ("Assay", "Target", "The vocabulary assigns this fictional measurement target."),
    "reportedIn": ("Result", "Document", "The source measurement is cited in this report version."),
}


def assertion(graph, subject, relation, obj, origin):
    domain, target, _ = RELATIONS[relation]
    graph.add_node(subject, kind=domain)
    graph.add_node(obj, kind=target)
    graph.add_edge(subject,obj,key=(relation,origin),relation=relation,origin=origin)


def build_graph(db, role="reader"):
    graph = nx.MultiDiGraph()
    for key,c in CONCEPTS.items():
        assertion(graph,key,"measuresTarget",c["target"],f"taxonomy/{VOCAB['version']}/{key}")
    for r in records(db,"SELECT * FROM curated_results ORDER BY result_id"):
        src = r["source_record_id"]
        assertion(graph,r["compound_id"],"testedIn",r["assay_id"],src)
        assertion(graph,r["assay_id"],"hasResult",r["result_id"],src)
        assertion(graph,r["experiment_id"],"usesSample",r["sample_id"],src)
    for doc in visible_documents(db,role):
        key = (doc["document_id"], doc["version"])
        for r in records(db,"""SELECT l.result_id FROM document_result l JOIN assay_result r
                          ON r.result_id=l.result_id AND r.source_record_id=l.source_record_id
                          WHERE document_id=? AND version=?
                          AND r.mapping_version=json_extract(l.measurement_json,'$.mapping_version')""",key):
            ref = f"{key[0]}/v{key[1]}"
            assertion(graph,r["result_id"],"reportedIn",ref,ref)
    return graph


def paths(graph, compound):
    """Retain only assay-result links supported by the same compound observation."""
    result = []
    for _, assay, first in graph.out_edges(compound, data=True):
        if first["relation"] != "testedIn":
            continue
        for _, rid, second in graph.out_edges(assay, data=True):
            if second["relation"] == "hasResult" and first["origin"] == second["origin"]:
                result.append(dict(compound=compound,assay=assay,result=rid,source_record_id=first["origin"]))
    return result
