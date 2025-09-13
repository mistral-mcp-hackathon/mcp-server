#!/usr/bin/env python3
"""
ClickHouse configuration for Team MCP Server
"""

import os
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class ClickHouseConfig:
    """Configuration for ClickHouse connection settings.
    
    Environment variables:
        CLICKHOUSE_HOST: The hostname of the ClickHouse server (required if using ClickHouse)
        CLICKHOUSE_USER: Username for authentication (optional)
        CLICKHOUSE_PASSWORD: Password for authentication (optional)
        CLICKHOUSE_PORT: Port number (default: 8123 for HTTP)
        CLICKHOUSE_DATABASE: Default database (default: logs)
        CLICKHOUSE_SECURE: Enable HTTPS (default: false)
        CLICKHOUSE_VERIFY: Verify SSL certificates (default: true)
        CLICKHOUSE_CONNECT_TIMEOUT: Connection timeout in seconds (default: 30)
        CLICKHOUSE_SEND_RECEIVE_TIMEOUT: Send/receive timeout in seconds (default: 300)
    """
    
    @property
    def enabled(self) -> bool:
        """Check if ClickHouse is configured (host is set)."""
        return bool(os.getenv("CLICKHOUSE_HOST"))
    
    @property
    def host(self) -> Optional[str]:
        """Get the ClickHouse host."""
        return os.getenv("CLICKHOUSE_HOST")
    
    @property
    def port(self) -> int:
        """Get the ClickHouse port (default: 8123 for HTTP)."""
        return int(os.getenv("CLICKHOUSE_PORT", "8123"))
    
    @property
    def username(self) -> Optional[str]:
        """Get the ClickHouse username (optional)."""
        return os.getenv("CLICKHOUSE_USER")
    
    @property
    def password(self) -> Optional[str]:
        """Get the ClickHouse password (optional)."""
        return os.getenv("CLICKHOUSE_PASSWORD")
    
    @property
    def database(self) -> str:
        """Get the default database name (default: logs)."""
        return os.getenv("CLICKHOUSE_DATABASE", "logs")
    
    @property
    def secure(self) -> bool:
        """Get whether HTTPS is enabled (default: false)."""
        return os.getenv("CLICKHOUSE_SECURE", "false").lower() == "true"
    
    @property
    def verify(self) -> bool:
        """Get whether SSL certificate verification is enabled (default: true)."""
        return os.getenv("CLICKHOUSE_VERIFY", "true").lower() == "true"
    
    @property
    def connect_timeout(self) -> int:
        """Get the connection timeout in seconds (default: 30)."""
        return int(os.getenv("CLICKHOUSE_CONNECT_TIMEOUT", "30"))
    
    @property
    def send_receive_timeout(self) -> int:
        """Get the send/receive timeout in seconds (default: 300)."""
        return int(os.getenv("CLICKHOUSE_SEND_RECEIVE_TIMEOUT", "300"))
    
    def get_client_config(self) -> Dict[str, Any]:
        """Get the configuration dictionary for clickhouse_connect client.
        
        Returns:
            dict: Configuration ready to be passed to clickhouse_connect.get_client()
        """
        if not self.enabled:
            raise ValueError("ClickHouse is not configured. Set CLICKHOUSE_HOST to enable.")
        
        config = {
            "host": self.host,
            "port": self.port,
            "secure": self.secure,
            "verify": self.verify,
            "connect_timeout": self.connect_timeout,
            "send_receive_timeout": self.send_receive_timeout,
            "client_name": "team_mcp_server",
        }
        
        # Add optional authentication if provided
        if self.username:
            config["username"] = self.username
        if self.password:
            config["password"] = self.password
        
        # Add default database
        config["database"] = self.database
        
        return config


# Global singleton instance
_CONFIG = None


def get_clickhouse_config() -> ClickHouseConfig:
    """Get the singleton ClickHouse configuration instance."""
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = ClickHouseConfig()
    return _CONFIG
