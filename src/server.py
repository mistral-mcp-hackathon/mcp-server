#!/usr/bin/env python3
"""
S3 Butler - MCP server for S3 bucket management and analytics
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
logger = logging.getLogger("S3Butler")

mcp = FastMCP("S3Butler")


@mcp.tool()
def get_team_name() -> str:
    """Get the name of the team or organization
    
    This tool returns the team or organization name associated with this S3 Butler instance.
    Currently returns a hardcoded value but can be configured to return dynamic team information.
    
    Returns:
        str: The team/organization name (default: 'team1')
    """
    return "team1"


# S3/IAM Tools
# Use environment variables for S3/IAM configuration
s3_access_key = os.getenv('S3_ACCESS_KEY')
s3_secret_key = os.getenv('S3_SECRET_KEY')
iam_endpoint = os.getenv('IAM_ENDPOINT', 'http://127.0.0.1:8600')
s3_endpoint = os.getenv('S3_ENDPOINT', 'http://127.0.0.1:8000')

if s3_access_key and s3_secret_key:
    session = boto3.Session(
        aws_access_key_id=s3_access_key,
        aws_secret_access_key=s3_secret_key
    )
    iam_client = session.client('iam', endpoint_url=iam_endpoint)
    s3_client = session.client('s3', endpoint_url=s3_endpoint)
else:
    # Fallback to profile if env vars not set
    session = boto3.Session(profile_name='scality-dev')
    iam_client = session.client('iam', endpoint_url=iam_endpoint)
    s3_client = session.client('s3', endpoint_url=s3_endpoint)

# Create a wrapper function that FastMCP can use
@mcp.tool()
def get_iam_policies_for_bucket(bucket_name: str = "") -> str:
    """Retrieve all IAM policies that grant access to a specific S3 bucket
    
    This tool scans all IAM users in your account and identifies which policies
    (both inline and attached) grant permissions to the specified S3 bucket.
    Useful for auditing bucket access and understanding permission boundaries.

    Args:
        bucket_name: The name of the S3 bucket to check policies for (e.g., 'my-data-bucket').
                    Required parameter - must provide a valid bucket name.

    Returns:
        JSON string containing a dictionary where keys are usernames and values are
        their policies that reference the bucket. Returns error message if bucket name
        is not provided.
    """
    if not bucket_name or bucket_name.strip() == "":
        return json.dumps({
            "error": "Bucket name is required",
            "message": "Please provide a bucket name to check which IAM policies grant access to it.",
            "usage": "Specify a bucket name (e.g., 'finance', 'engineering')"
        })

    return s3.get_iam_policies_for_bucket(iam_client, bucket_name)

@mcp.tool()
def list_buckets() -> str:
    """List all S3 buckets accessible with the configured credentials
    
    This tool retrieves all S3 buckets that the configured AWS credentials have
    permission to list. Provides bucket names, creation dates, and owner information.
    Useful for discovering available storage resources and auditing bucket inventory.
    
    Returns:
        JSON string containing:
        - 'buckets': List of bucket objects with 'name' and 'creation_date'
        - 'count': Total number of buckets found
        - 'owner': Bucket owner information (DisplayName and ID)
        Returns error message if S3 access fails.
    """
    try:
        response = s3_client.list_buckets()
        
        buckets = []
        for bucket in response.get('Buckets', []):
            buckets.append({
                'name': bucket['Name'],
                'creation_date': bucket['CreationDate'].isoformat() if bucket.get('CreationDate') else None
            })
        
        result = {
            'buckets': buckets,
            'count': len(buckets),
            'owner': response.get('Owner', {})
        }
        
        logger.info(f"Listed {len(buckets)} buckets")
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error listing buckets: {e}")
        return json.dumps({
            "error": "Failed to list buckets",
            "message": str(e)
        })

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
        """Get the top N buckets ranked by total number of operations
        
        This analytics tool queries ClickHouse to identify which S3 buckets have the most
        activity based on total operation count. Useful for identifying hot buckets,
        understanding usage patterns, and capacity planning.
        
        Time range defaults to last 10 days if not specified. End time always defaults to
        current time if not provided.
        
        Args:
            limit: Number of top buckets to return (default: 10, max recommended: 100)
            hours_back: Number of hours to look back from now (e.g., 24 for last day)
                       Mutually exclusive with start_time/end_time
            start_time: Start time in ISO format (e.g., '2024-01-01T00:00:00Z')
                       If provided without end_time, end_time defaults to now
            end_time: End time in ISO format (e.g., '2024-01-31T23:59:59Z')
                     Optional, defaults to current time
            
        Returns:
            List[Dict[str, Any]]: List of dictionaries, each containing:
            - 'bucket_name': Name of the S3 bucket
            - 'number_of_operations': Total operation count in the time period
            Sorted by operation count (descending)
        """
        logger.info(f"Getting top {limit} buckets by operations")
        
        # Build time filter with defaults
        time_conditions = []
        
        if hours_back:
            time_conditions.append(
                f"timestamp >= now() - INTERVAL {hours_back} HOUR"
            )
            time_conditions.append("timestamp <= now()")
        elif start_time or end_time:
            if start_time:
                time_conditions.append(f"timestamp >= '{start_time}'")
            if end_time:
                time_conditions.append(f"timestamp <= '{end_time}'")
            else:
                time_conditions.append("timestamp <= now()")
        else:
            # Default to last 10 days
            time_conditions.append("timestamp >= now() - INTERVAL 10 DAY")
            time_conditions.append("timestamp <= now()")
        
        # Build the query based on the Grafana template for operations
        where_clause = "WHERE " + " AND ".join(time_conditions) + " AND "
        
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
        """Get the top N buckets ranked by inbound traffic (data uploaded)
        
        This analytics tool queries ClickHouse to identify which S3 buckets receive the most
        data uploads, tracking PutObject and UploadPart operations. Useful for understanding
        data ingestion patterns, identifying heavy write workloads, and storage growth trends.
        
        Time range defaults to last 10 days if not specified. End time always defaults to
        current time if not provided.
        
        Args:
            limit: Number of top buckets to return (default: 10, max recommended: 100)
            hours_back: Number of hours to look back from now (e.g., 24 for last day)
                       Mutually exclusive with start_time/end_time
            start_time: Start time in ISO format (e.g., '2024-01-01T00:00:00Z')
                       If provided without end_time, end_time defaults to now
            end_time: End time in ISO format (e.g., '2024-01-31T23:59:59Z')
                     Optional, defaults to current time
            
        Returns:
            List[Dict[str, Any]]: List of dictionaries, each containing:
            - 'bucket_name': Name of the S3 bucket
            - 'total_bytes': Total bytes uploaded (raw number)
            - 'inbound_traffic': Human-readable size (e.g., '1.5 GB', '500 MB')
            Sorted by total bytes uploaded (descending)
        """
        logger.info(f"Getting top {limit} buckets by inbound traffic")
        
        # Build time filter with defaults
        time_conditions = []
        
        if hours_back:
            time_conditions.append(
                f"timestamp >= now() - INTERVAL {hours_back} HOUR"
            )
            time_conditions.append("timestamp <= now()")
        elif start_time or end_time:
            if start_time:
                time_conditions.append(f"timestamp >= '{start_time}'")
            if end_time:
                time_conditions.append(f"timestamp <= '{end_time}'")
            else:
                time_conditions.append("timestamp <= now()")
        else:
            # Default to last 10 days
            time_conditions.append("timestamp >= now() - INTERVAL 10 DAY")
            time_conditions.append("timestamp <= now()")
        
        # Build the query based on the Grafana template for inbound traffic
        where_clause = "WHERE " + " AND ".join(time_conditions) + " AND "
        
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
        """Get the top N buckets ranked by outbound traffic (data downloaded)
        
        This analytics tool queries ClickHouse to identify which S3 buckets serve the most
        data downloads, tracking GetObject operations. Useful for understanding data
        consumption patterns, identifying high-demand content, and optimizing CDN strategies.
        
        Time range defaults to last 10 days if not specified. End time always defaults to
        current time if not provided.
        
        Args:
            limit: Number of top buckets to return (default: 10, max recommended: 100)
            hours_back: Number of hours to look back from now (e.g., 24 for last day)
                       Mutually exclusive with start_time/end_time
            start_time: Start time in ISO format (e.g., '2024-01-01T00:00:00Z')
                       If provided without end_time, end_time defaults to now
            end_time: End time in ISO format (e.g., '2024-01-31T23:59:59Z')
                     Optional, defaults to current time
            
        Returns:
            List[Dict[str, Any]]: List of dictionaries, each containing:
            - 'bucket_name': Name of the S3 bucket
            - 'total_bytes': Total bytes downloaded (raw number)
            - 'outbound_traffic': Human-readable size (e.g., '10.5 TB', '750 GB')
            Sorted by total bytes downloaded (descending)
        """
        logger.info(f"Getting top {limit} buckets by outbound traffic")
        
        # Build time filter with defaults
        time_conditions = []
        
        if hours_back:
            time_conditions.append(
                f"timestamp >= now() - INTERVAL {hours_back} HOUR"
            )
            time_conditions.append("timestamp <= now()")
        elif start_time or end_time:
            if start_time:
                time_conditions.append(f"timestamp >= '{start_time}'")
            if end_time:
                time_conditions.append(f"timestamp <= '{end_time}'")
            else:
                time_conditions.append("timestamp <= now()")
        else:
            # Default to last 10 days
            time_conditions.append("timestamp >= now() - INTERVAL 10 DAY")
            time_conditions.append("timestamp <= now()")
        
        # Build the query based on the Grafana template for outbound traffic
        where_clause = "WHERE " + " AND ".join(time_conditions) + " AND "
        
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

    print(f"Starting S3 Butler MCP server...")
    print(f"Server will be available at http://{host}:{port}{path}")
    print(f"Using HTTP streaming transport (FastMCP 2.3+)")

    mcp.run(
        transport="http",
        host=host,
        port=port,
        path=path
    )
