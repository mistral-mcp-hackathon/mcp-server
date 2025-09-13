#!/usr/bin/env python3
"""
Team MCP Server - Provides team information via MCP protocol
"""

from fastmcp import FastMCP
import os
from dotenv import load_dotenv
import boto3

import s3

load_dotenv()

mcp = FastMCP("TeamServer")


@mcp.tool()
def get_team_name() -> str:
    """Get the name of the team
    
    Returns:
        str: The team name
    """
    return "team1"


session = boto3.Session(profile_name='scality-dev')
iam_client = session.client('iam', endpoint_url="http://127.0.0.1:8600")

mcp.tool(s3.with_client(iam_client)(s3.get_iam_policies_for_bucket))

if __name__ == "__main__":
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8000"))
    path = os.getenv("MCP_PATH", "/mcp")

    print(f"Starting TeamServer MCP server...")
    print(f"Server will be available at http://{host}:{port}{path}")
    print(f"Using HTTP streaming transport (FastMCP 2.3+)")

    mcp.run(
        transport="http",
        host=host,
        port=port,
        path=path
    )
