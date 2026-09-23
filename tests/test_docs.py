import collections

from tokyo_ckan_stac.docs import node_docs, root_docs


def _stats():
    return {"datasets": 10, "resources": 30, "organisations": 2, "datastore_schemas": 4,
            "basis": collections.Counter({"resource-name": 6, "resource-created": 4}),
            "footprint": collections.Counter({"municipality": 7, "prefecture": 3}),
            "licenses": collections.Counter({"CC-BY-4.0": 10})}


def test_root_docs_carry_the_counted_numbers():
    readme, agents = root_docs(_stats(), "https://x.test/tokyo-ckan")
    assert "6 (60%)" in readme
    assert "| resource-name | 6 |" in agents
    assert "https://x.test/tokyo-ckan/assets.parquet" in agents


def test_no_bold_and_no_em_dash_in_generated_docs():
    readme, agents = root_docs(_stats(), "https://x.test")
    node = node_docs({"type": "Catalog", "title": "t", "description": "d", "links": []}, "../")
    for text in (readme, agents, *node):
        assert "**" not in text
        assert "—" not in text


def test_node_docs_point_at_the_root():
    readme, agents = node_docs({"type": "Collection", "title": "港区", "description": "d",
                                "links": [{"rel": "item"}, {"rel": "item"}]}, "../../")
    assert "2 item links" in readme
    assert "../../AGENTS.md" in agents
