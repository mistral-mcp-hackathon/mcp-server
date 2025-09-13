#!/usr/bin/env python3
"""
Simple test client for the MCP server
"""

import asyncio
from fastmcp.client import Client

async def test_server(url="http://localhost:8000/mcp"):
    # Connect to the server
    print(f"Connecting to: {url}")
    async with Client(url) as client:
        print("Connected to MCP server!")
        print("\nAvailable tools:")
        
        # List available tools
        tools = await client.list_tools()
        for tool in tools:
            print(f"  - {tool.name}: {tool.description}")
        
        print("\nCalling get_team_name tool...")
        
        # Call the get_team_name tool
        result = await client.call_tool("get_team_name", {})
        print(f"Result: {result}")

if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/mcp"
    asyncio.run(test_server(url))
