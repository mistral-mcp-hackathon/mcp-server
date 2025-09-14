#!/usr/bin/env python3
"""
Test the get_top_buckets functionality
"""

import os
import sys
sys.path.insert(0, 'src')

from dotenv import load_dotenv
load_dotenv()

from clickhouse_config import get_clickhouse_config
import clickhouse_connect

def test_top_buckets():
    """Test the top buckets query"""
    config = get_clickhouse_config()
    client_config = config.get_client_config()
    client = clickhouse_connect.get_client(**client_config)
    
    # Test query for top 10 buckets
    query = """
    SELECT 
        bucketName,
        sum(contentLength) AS totalContentLength,
        formatReadableSize(sum(contentLength)) AS readableSize,
        count() AS operationCount
    FROM logs.cloudserver_aggregated_federated 
    WHERE action IN ('PutObject', 'UploadPart')
    GROUP BY bucketName 
    ORDER BY totalContentLength DESC, bucketName ASC 
    LIMIT 10
    """
    
    print("Testing top buckets query...")
    print("=" * 60)
    
    try:
        result = client.query(query)
        
        if result.result_rows:
            print(f"Found {len(result.result_rows)} top buckets:\n")
            print(f"{'Bucket Name':<30} {'Total Size':<15} {'Operations':<10}")
            print("-" * 60)
            
            for row in result.result_rows:
                bucket_name = row[0]
                total_bytes = row[1]
                readable_size = row[2]
                op_count = row[3]
                
                print(f"{bucket_name:<30} {readable_size:<15} {op_count:<10}")
        else:
            print("No bucket data found")
            
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    test_top_buckets()
