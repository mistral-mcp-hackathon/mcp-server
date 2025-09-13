#!/usr/bin/env python3
"""
Test script for ClickHouse integration
"""

import os
import sys
sys.path.insert(0, 'src')

from dotenv import load_dotenv
load_dotenv()

from clickhouse_config import get_clickhouse_config
import clickhouse_connect

def test_connection():
    """Test ClickHouse connection"""
    config = get_clickhouse_config()
    
    if not config.enabled:
        print("❌ ClickHouse is not configured (CLICKHOUSE_HOST not set)")
        return False
    
    print(f"Testing connection to ClickHouse at {config.host}:{config.port}")
    print(f"Database: {config.database}")
    print(f"Secure: {config.secure}")
    print(f"Has auth: {bool(config.username)}")
    
    try:
        client_config = config.get_client_config()
        client = clickhouse_connect.get_client(**client_config)
        
        # Test basic connection
        version = client.server_version
        print(f"✅ Connected to ClickHouse version: {version}")
        
        # List databases
        databases = client.command("SHOW DATABASES")
        print(f"\n📁 Available databases:")
        for db in databases.strip().split('\n')[:5]:  # Show first 5
            print(f"  - {db}")
        
        # Check if logs database exists
        if 'logs' in databases:
            print(f"\n✅ 'logs' database exists")
            
            # List tables in logs database
            tables_query = "SELECT name FROM system.tables WHERE database = 'logs' ORDER BY name LIMIT 5"
            result = client.query(tables_query)
            
            if result.result_rows:
                print(f"\n📊 Sample tables in 'logs' database:")
                for row in result.result_rows:
                    print(f"  - {row[0]}")
        else:
            print(f"\n⚠️  'logs' database not found")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Failed to connect: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Testing ClickHouse Integration")
    print("=" * 50)
    
    if test_connection():
        print("\n✅ ClickHouse integration test passed!")
    else:
        print("\n❌ ClickHouse integration test failed!")
