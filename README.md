# S3 Butler

A Model Context Protocol (MCP) server that provides tools for S3 bucket management, IAM policy inspection, and ClickHouse analytics.

## Quick Start

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd mcp-server

# 2. Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Set up environment variables
cp .env.example .env
# Edit .env with your credentials (see Environment Setup below)

# 4. Install dependencies
uv sync

# 5. Run the server
uv run python src/server.py
```

Your MCP server is now running at `http://localhost:8000/mcp` 🎉

## Environment Setup

Create a `.env` file with your credentials:

```bash
# Server Configuration
MCP_HOST=0.0.0.0
MCP_PORT=8000
MCP_PATH=/mcp

# S3/IAM Configuration (Required)
S3_ENDPOINT=http://127.0.0.1:8000      # Your S3 endpoint
S3_ACCESS_KEY=your_access_key          # Your S3 access key
S3_SECRET_KEY=your_secret_key          # Your S3 secret key
IAM_ENDPOINT=http://127.0.0.1:8600     # Your IAM endpoint

# ClickHouse Configuration (Optional - for analytics)
CLICKHOUSE_HOST=localhost              # Leave blank to disable ClickHouse
CLICKHOUSE_USER=                       # Optional
CLICKHOUSE_PASSWORD=                   # Optional

# ngrok Configuration (Optional - for remote access)
NGROK_AUTH_TOKEN=                      # Get from https://dashboard.ngrok.com
```

## Available Tools

The server provides these MCP tools:

1. **`get_team_name`** - Returns the team name
2. **`list_buckets`** - Lists all S3 buckets
3. **`get_iam_policies_for_bucket`** - Shows IAM policies for a specific bucket
4. **`get_top_buckets_by_operations`** - Analytics: most active buckets (requires ClickHouse)
5. **`get_top_buckets_by_inbound_traffic`** - Analytics: buckets with most uploads (requires ClickHouse)
6. **`get_top_buckets_by_outbound_traffic`** - Analytics: buckets with most downloads (requires ClickHouse)

## Testing Your Server

### Option 1: MCP Inspector (Recommended)

```bash
# Install MCP Inspector
npm install -g @modelcontextprotocol/inspector

# Start the inspector
npx @modelcontextprotocol/inspector http://localhost:8000/mcp

# Open http://localhost:5173 in your browser
```

### Option 2: Test Scripts

```bash
# Test all tools
uv run python test_client.py

# Test list_buckets specifically
uv run python test_list_buckets.py
```

## Remote Access with ngrok

To access your server remotely:

```bash
# Run server with ngrok tunnel
uv run python scripts/run_with_ngrok.py

# The script will display your public URL
```

## Development

### Project Structure

```text
mcp-server/
├── src/
│   ├── server.py           # Main MCP server
│   ├── s3.py              # S3/IAM utilities
│   └── clickhouse_config.py # ClickHouse configuration
├── scripts/
│   └── run_with_ngrok.py  # ngrok launcher
├── .env                    # Your configuration (create from .env.example)
└── test_*.py              # Test scripts
```

### Adding New Tools

Edit `src/server.py` and add your tool:

```python
@mcp.tool()
def your_new_tool(param: str) -> str:
    """Description of your tool"""
    return f"Result for {param}"
```

### Code Quality

```bash
# Format code
uv run black src/ --line-length 100

# Lint
uv run ruff src/

# Type check
uv run mypy src/
```

## Troubleshooting

### Server won't start

- Check Python version: `python --version` (needs 3.10+)
- Verify `.env` file exists and has correct credentials
- Check if port 8000 is already in use

### Can't connect to S3/IAM

- Verify `S3_ENDPOINT` and `IAM_ENDPOINT` are correct
- Check `S3_ACCESS_KEY` and `S3_SECRET_KEY` are valid
- Test connection: `uv run python test_list_buckets.py`

### ClickHouse tools not showing

- Set `CLICKHOUSE_HOST` in `.env`
- Verify ClickHouse is running and accessible
- Check logs for connection errors