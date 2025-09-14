#!/usr/bin/env python3
"""
List available tools in the MCP server
"""

import sys
import asyncio
sys.path.insert(0, 'src')

# Import the mcp instance
from server import mcp, CLICKHOUSE_AVAILABLE

async def main():
    print("=" * 50)
    print("Available MCP Tools")
    print("=" * 50)
    
    # Get all registered tools
    tools = await mcp.get_tools()
    
    print(f"\nClickHouse enabled: {CLICKHOUSE_AVAILABLE}")
    print(f"\nTotal tools registered: {len(tools)}")
    print("-" * 50)
    
    for tool_name in tools:
        print(f"\n📦 Tool: {tool_name}")
        # Tools are returned as names in FastMCP 2.x
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    asyncio.run(main())
