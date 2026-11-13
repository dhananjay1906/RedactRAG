from mcp.server.mcpserver import MCPServer  # mcp 2.x name for FastMCP
mcp = MCPServer("redactrag")

@mcp.tool()
def search_policies(query: str, k: int = 5) -> list[dict]:
    """Search Harbor County Probation policy documents.
    Returns text chunks with their source file. All PII is already masked."""
    from app.search import search  # loaded on first call so the server starts instantly
    return search(query, k)

if __name__ == "__main__":
    mcp.run()
