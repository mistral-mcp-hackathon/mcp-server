#!/usr/bin/env python3
"""
Team MCP Server - Provides team information via MCP protocol
"""

from fastmcp import FastMCP
import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import json
from dotenv import load_dotenv
import boto3

import s3

load_dotenv()

# Import ClickHouse only if configured
try:
    from clickhouse_config import get_clickhouse_config
    import clickhouse_connect
    CLICKHOUSE_AVAILABLE = get_clickhouse_config().enabled
except ImportError:
    CLICKHOUSE_AVAILABLE = False
except Exception:
    CLICKHOUSE_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("TeamServer")

mcp = FastMCP("TeamServer")


@mcp.tool()
def get_team_name() -> str:
    """Get the name of the team
    
    Returns:
        str: The team name
    """
    return "team1"


# S3/IAM Tools
# Use environment variables for S3/IAM configuration
s3_access_key = os.getenv('S3_ACCESS_KEY')
s3_secret_key = os.getenv('S3_SECRET_KEY')
iam_endpoint = os.getenv('IAM_ENDPOINT', 'http://127.0.0.1:8600')

if s3_access_key and s3_secret_key:
    session = boto3.Session(
        aws_access_key_id=s3_access_key,
        aws_secret_access_key=s3_secret_key
    )
    iam_client = session.client('iam', endpoint_url=iam_endpoint)
else:
    # Fallback to profile if env vars not set
    session = boto3.Session(profile_name='scality-dev')
    iam_client = session.client('iam', endpoint_url=iam_endpoint)

# Create a wrapper function that FastMCP can use
@mcp.tool()
def get_iam_policies_for_bucket(bucket_name: str = "") -> str:
    """Retrieve all IAM policies for an account that reference a given bucket

    Args:
        bucket_name: The name of the S3 bucket to check policies for.

    Returns:
        JSON string containing IAM policies that reference the bucket
    """
    if not bucket_name or bucket_name.strip() == "":
        return json.dumps({
            "error": "Bucket name is required",
            "message": "Please provide a bucket name to check which IAM policies grant access to it.",
            "usage": "Specify a bucket name (e.g., 'finance', 'engineering')"
        })

    return s3.get_iam_policies_for_bucket(iam_client, bucket_name)

# ClickHouse Tools - only registered if ClickHouse is configured
if CLICKHOUSE_AVAILABLE:
    def create_clickhouse_client():
        """Create a ClickHouse client connection."""
        config = get_clickhouse_config()
        client_config = config.get_client_config()
        
        logger.info(
            f"Creating ClickHouse client connection to {client_config['host']}:{client_config['port']} "
            f"(secure={client_config['secure']}, database={client_config.get('database', 'default')})"
        )
        
        try:
            client = clickhouse_connect.get_client(**client_config)
            # Test the connection
            version = client.server_version
            logger.info(f"Successfully connected to ClickHouse server version {version}")
            return client
        except Exception as e:
            logger.error(f"Failed to connect to ClickHouse: {str(e)}")
            raise
    
    
    @mcp.tool()
    def get_top_buckets_by_operations(
        limit: int = 10,
        hours_back: Optional[int] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get the top N buckets by number of operations
        
        Args:
            limit: Number of top buckets to return (default: 10)
            hours_back: Number of hours to look back from now (optional)
            start_time: Start time in ISO format (optional)
            end_time: End time in ISO format (optional)
            
        Returns:
            List[Dict[str, Any]]: List of buckets with their operation counts
        """
        logger.info(f"Getting top {limit} buckets by operations")
        
        # Build time filter
        time_conditions = []
        
        if hours_back:
            time_conditions.append(
                f"timestamp >= now() - INTERVAL {hours_back} HOUR"
            )
        elif start_time or end_time:
            if start_time:
                time_conditions.append(f"timestamp >= '{start_time}'")
            if end_time:
                time_conditions.append(f"timestamp <= '{end_time}'")
        
        # Build the query based on the Grafana template for operations
        where_clause = ""
        if time_conditions:
            where_clause = "WHERE " + " AND ".join(time_conditions) + " AND "
        else:
            where_clause = "WHERE "
        
        query = f"""
        SELECT 
            bucketName,
            sum(number_of_op) as number_of_operations
        FROM logs.cloudserver_aggregated_federated 
        {where_clause}
            bucketName <> ''
        GROUP BY bucketName 
        ORDER BY number_of_operations DESC, bucketName ASC 
        LIMIT {limit}
        """
        
        client = create_clickhouse_client()
        
        try:
            result = client.query(query)
            
            buckets = []
            for row in result.result_rows:
                buckets.append({
                    "bucket_name": row[0],
                    "number_of_operations": row[1]
                })
            
            logger.info(f"Found {len(buckets)} buckets")
            return buckets
            
        except Exception as e:
            logger.error(f"Error getting top buckets by operations: {e}")
            raise ValueError(f"Failed to get top buckets by operations: {str(e)}")
    
    
    @mcp.tool()
    def get_top_buckets_by_inbound_traffic(
        limit: int = 10,
        hours_back: Optional[int] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get the top N buckets by inbound traffic (PutObject and UploadPart operations)
        
        Args:
            limit: Number of top buckets to return (default: 10)
            hours_back: Number of hours to look back from now (optional)
            start_time: Start time in ISO format (optional)
            end_time: End time in ISO format (optional)
            
        Returns:
            List[Dict[str, Any]]: List of buckets with their inbound traffic
        """
        logger.info(f"Getting top {limit} buckets by inbound traffic")
        
        # Build time filter
        time_conditions = []
        
        if hours_back:
            time_conditions.append(
                f"timestamp >= now() - INTERVAL {hours_back} HOUR"
            )
        elif start_time or end_time:
            if start_time:
                time_conditions.append(f"timestamp >= '{start_time}'")
            if end_time:
                time_conditions.append(f"timestamp <= '{end_time}'")
        
        # Build the query based on the Grafana template for inbound traffic
        where_clause = ""
        if time_conditions:
            where_clause = "WHERE " + " AND ".join(time_conditions) + " AND "
        else:
            where_clause = "WHERE "
        
        query = f"""
        SELECT 
            bucketName,
            sum(contentLength) AS totalContentLength,
            formatReadableSize(sum(contentLength)) AS readableSize
        FROM logs.cloudserver_aggregated_federated 
        {where_clause}
            action IN ('PutObject', 'UploadPart')
        GROUP BY bucketName 
        ORDER BY totalContentLength DESC, bucketName ASC 
        LIMIT {limit}
        """
        
        client = create_clickhouse_client()
        
        try:
            result = client.query(query)
            
            buckets = []
            for row in result.result_rows:
                buckets.append({
                    "bucket_name": row[0],
                    "total_bytes": row[1],
                    "inbound_traffic": row[2]
                })
            
            logger.info(f"Found {len(buckets)} buckets")
            return buckets
            
        except Exception as e:
            logger.error(f"Error getting top buckets by inbound traffic: {e}")
            raise ValueError(f"Failed to get top buckets by inbound traffic: {str(e)}")
    
    
    @mcp.tool()
    def get_top_buckets_by_outbound_traffic(
        limit: int = 10,
        hours_back: Optional[int] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get the top N buckets by outbound traffic (GetObject operations)
        
        Args:
            limit: Number of top buckets to return (default: 10)
            hours_back: Number of hours to look back from now (optional)
            start_time: Start time in ISO format (optional)
            end_time: End time in ISO format (optional)
            
        Returns:
            List[Dict[str, Any]]: List of buckets with their outbound traffic
        """
        logger.info(f"Getting top {limit} buckets by outbound traffic")
        
        # Build time filter
        time_conditions = []
        
        if hours_back:
            time_conditions.append(
                f"timestamp >= now() - INTERVAL {hours_back} HOUR"
            )
        elif start_time or end_time:
            if start_time:
                time_conditions.append(f"timestamp >= '{start_time}'")
            if end_time:
                time_conditions.append(f"timestamp <= '{end_time}'")
        
        # Build the query based on the Grafana template for outbound traffic
        where_clause = ""
        if time_conditions:
            where_clause = "WHERE " + " AND ".join(time_conditions) + " AND "
        else:
            where_clause = "WHERE "
        
        query = f"""
        SELECT 
            bucketName,
            sum(contentLength) AS totalContentLength,
            formatReadableSize(sum(contentLength)) AS readableSize
        FROM logs.cloudserver_aggregated_federated 
        {where_clause}
            action = 'GetObject'
        GROUP BY bucketName 
        ORDER BY totalContentLength DESC, bucketName ASC 
        LIMIT {limit}
        """
        
        client = create_clickhouse_client()
        
        try:
            result = client.query(query)
            
            buckets = []
            for row in result.result_rows:
                buckets.append({
                    "bucket_name": row[0],
                    "total_bytes": row[1],
                    "outbound_traffic": row[2]
                })
            
            logger.info(f"Found {len(buckets)} buckets")
            return buckets
            
        except Exception as e:
            logger.error(f"Error getting top buckets by outbound traffic: {e}")
            raise ValueError(f"Failed to get top buckets by outbound traffic: {str(e)}")
    
    
    logger.info("ClickHouse tools registered")
else:
    logger.info("ClickHouse is not configured, skipping ClickHouse tools")


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
