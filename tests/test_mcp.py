from mcp_server import search_policies

def test_mcp_tool_returns_masked_chunks():
    rows = search_policies("who is the records request contact", k=5)
    assert rows
    assert all("@" not in r["content"] for r in rows)
    assert all("doc" in r for r in rows)
