#!/usr/bin/env python3
"""
Test the list_buckets MCP tool
"""

import asyncio
import sys
from fastmcp.client import Client
import json


async def test_list_buckets():
    """Test the list_buckets tool"""
    server_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/mcp"
    
    print(f"Testing MCP server at: {server_url}")
    print("-" * 60)
    
    async with Client(server_url) as client:
        # Test list_buckets tool
        print("\n📦 Testing list_buckets tool...")
        try:
            result = await client.call_tool("list_buckets", {})
            
            # The result is already the response - if it's a string, parse it
            if isinstance(result.content, str):
                buckets_data = json.loads(result.content)
            elif isinstance(result.content, list) and len(result.content) > 0:
                # Sometimes the content is a list with one element
                buckets_data = json.loads(result.content[0].text)
            else:
                # Fall back to just printing the raw result
                print(f"Raw result: {result}")
                return
            
            if "error" in buckets_data:
                print(f"❌ Error: {buckets_data['error']}")
                print(f"   Message: {buckets_data.get('message', 'Unknown error')}")
            else:
                print(f"✅ Successfully listed buckets!")
                print(f"   Total buckets: {buckets_data.get('count', 0)}")
                
                if buckets_data.get('owner'):
                    owner = buckets_data['owner']
                    print(f"   Owner: {owner.get('DisplayName', 'N/A')} (ID: {owner.get('ID', 'N/A')})")
                
                if buckets_data.get('buckets'):
                    print("\n   Buckets:")
                    for bucket in buckets_data['buckets']:
                        print(f"   - {bucket['name']}")
                        if bucket.get('creation_date'):
                            print(f"     Created: {bucket['creation_date']}")
                else:
                    print("   No buckets found")
                    
        except Exception as e:
            print(f"❌ Failed to call list_buckets: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_list_buckets())
