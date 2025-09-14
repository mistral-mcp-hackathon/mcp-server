#!/usr/bin/env python3
"""
Test all three bucket query tools
"""

import os
import sys
sys.path.insert(0, 'src')

from dotenv import load_dotenv
load_dotenv()

from clickhouse_config import get_clickhouse_config
import clickhouse_connect

def test_all_tools():
    """Test all three top bucket queries"""
    config = get_clickhouse_config()
    client_config = config.get_client_config()
    client = clickhouse_connect.get_client(**client_config)
    
    print("=" * 70)
    print("Testing All Three Top Bucket Tools")
    print("=" * 70)
    
    # Test 1: Top buckets by operations
    print("\n1. TOP BUCKETS BY OPERATIONS")
    print("-" * 40)
    
    operations_query = """
    SELECT 
        bucketName,
        sum(number_of_op) as number_of_operations
    FROM logs.cloudserver_aggregated_federated 
    WHERE bucketName <> ''
    GROUP BY bucketName 
    ORDER BY number_of_operations DESC, bucketName ASC 
    LIMIT 5
    """
    
    try:
        result = client.query(operations_query)
        
        if result.result_rows:
            print(f"{'Bucket Name':<35} {'Operations':<15}")
            print("-" * 50)
            
            for row in result.result_rows:
                bucket_name = row[0]
                operations = row[1]
                print(f"{bucket_name:<35} {operations:<15,}")
        else:
            print("No data found")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: Top buckets by inbound traffic
    print("\n2. TOP BUCKETS BY INBOUND TRAFFIC (PutObject/UploadPart)")
    print("-" * 40)
    
    inbound_query = """
    SELECT 
        bucketName,
        sum(contentLength) AS totalContentLength,
        formatReadableSize(sum(contentLength)) AS readableSize
    FROM logs.cloudserver_aggregated_federated 
    WHERE action IN ('PutObject', 'UploadPart')
    GROUP BY bucketName 
    ORDER BY totalContentLength DESC, bucketName ASC 
    LIMIT 5
    """
    
    try:
        result = client.query(inbound_query)
        
        if result.result_rows:
            print(f"{'Bucket Name':<35} {'Inbound Traffic':<15}")
            print("-" * 50)
            
            for row in result.result_rows:
                bucket_name = row[0]
                readable_size = row[2]
                print(f"{bucket_name:<35} {readable_size:<15}")
        else:
            print("No data found")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 3: Top buckets by outbound traffic
    print("\n3. TOP BUCKETS BY OUTBOUND TRAFFIC (GetObject)")
    print("-" * 40)
    
    outbound_query = """
    SELECT 
        bucketName,
        sum(contentLength) AS totalContentLength,
        formatReadableSize(sum(contentLength)) AS readableSize
    FROM logs.cloudserver_aggregated_federated 
    WHERE action = 'GetObject'
    GROUP BY bucketName 
    ORDER BY totalContentLength DESC, bucketName ASC 
    LIMIT 5
    """
    
    try:
        result = client.query(outbound_query)
        
        if result.result_rows:
            print(f"{'Bucket Name':<35} {'Outbound Traffic':<15}")
            print("-" * 50)
            
            for row in result.result_rows:
                bucket_name = row[0]
                readable_size = row[2]
                print(f"{bucket_name:<35} {readable_size:<15}")
        else:
            print("No outbound traffic data found")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    test_all_tools()
