from src.graph import RELATIONS, build_graph, paths
from src.taxonomy import resolve
from src.workspace import build


def test_vocab_and_supported_paths():
    assert resolve("  CELL viability ")["category"] == "CAT-CELL"
    assert resolve("Binding readout", "Alpha") is None
    assert resolve("absent") is None
    db = build()
    graph = build_graph(db)
    for s,o,edge in graph.edges(data=True):
        domain,target,_ = RELATIONS[edge["relation"]]
        assert graph.nodes[s]["kind"] == domain and graph.nodes[o]["kind"] == target and edge["origin"]
    actual = {(p["result"],p["source_record_id"]) for p in paths(graph,"C-001")}
    expected = {tuple(r) for r in db.execute("SELECT result_id,source_record_id FROM curated_results WHERE compound_id='C-001'")}
    assert actual == expected and actual
    assert not any("DOC-A004" in node for node in graph.nodes)
    db.close()
