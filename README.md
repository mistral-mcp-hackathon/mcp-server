# Team MCP Server

A Model Context Protocol (MCP) server built with FastMCP 2.0+ that provides team information through HTTP streaming transport.

## Quick Start

```bash
# Clone the repository
git clone <your-repo-url>
cd mcp-server

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Run the server
uv run python src/team_server.py

# Server is now running at http://localhost:8000/mcp
```

**Test it with MCP Inspector:**

```bash
# Install MCP Inspector (one-time setup)
npm install -g @modelcontextprotocol/inspector

# Run the inspector (in a new terminal)
npx @modelcontextprotocol/inspector http://localhost:8000/mcp

# Open browser to http://localhost:5173 to test your tools
```

That's it! Your MCP server is running and you can test it interactively with MCP Inspector.

## Overview

This MCP server exposes tools for retrieving team information. It's designed for deployment on servers and includes ngrok integration for easy testing and development.

## Prerequisites

- Python 3.10 or higher
- Either `uv` (recommended) or `pip` for package management
- Node.js and npm (optional, for MCP Inspector)
- ngrok account (optional, for remote testing)

## Installation

### Option 1: Using uv (Recommended)

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync
```

### Option 2: Using pip

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Edit `.env` to configure:
   - `MCP_HOST`: Server host (default: 0.0.0.0)
   - `MCP_PORT`: Server port (default: 8000)
   - `MCP_PATH`: MCP endpoint path (default: /mcp)
   - `NGROK_AUTH_TOKEN`: Your ngrok auth token (optional)

## Running the Server

### Local Development

```bash
# Using uv
uv run python src/team_server.py

# Using pip
python src/team_server.py
```

The server will start on `http://localhost:8000/mcp` using HTTP streaming transport.

### With ngrok Tunnel

For remote testing or exposing your local server to the internet:

```bash
# Using uv
uv run python scripts/run_with_ngrok.py

# Using pip
python scripts/run_with_ngrok.py

# Or tunnel only (if server is already running)
uv run python scripts/run_with_ngrok.py --tunnel-only
```

This will:
1. Start the MCP server locally (unless --tunnel-only is used)
2. Create an ngrok tunnel
3. Display the public URL you can use to access your server remotely

## API Documentation

### Endpoint

- **URL**: `http://localhost:8000/mcp` (or your configured host/port/path)
- **Transport**: HTTP streaming (FastMCP 2.3+)
- **Protocol**: Model Context Protocol

### Available Tools

#### `get_team_name`

Returns the name of the team.

**Parameters**: None

**Returns**:

```json
{
  "result": "team1"
}
```

**Example Usage with MCP Client**:

```python
from fastmcp.client import Client

async with Client("http://localhost:8000/mcp") as client:
    result = await client.call_tool("get_team_name", {})
    print(result)  # Returns "team1"
```

## Testing

### Using MCP Inspector (Recommended)

MCP Inspector provides a web-based UI to test your MCP server's tools interactively.

1. Install MCP Inspector globally:

```bash
npm install -g @modelcontextprotocol/inspector
```

2. Start your MCP server:

```bash
uv run python src/team_server.py
```

3. In a new terminal, run the Inspector:

```bash
npx @modelcontextprotocol/inspector http://localhost:8000/mcp
```

4. Open your browser to the URL shown (typically `http://localhost:5173`)

5. In the Inspector UI, you can:
   - View all available tools
   - Test the `get_team_name` tool interactively
   - See request/response details
   - Inspect the server's capabilities

### Using the Test Client

1. Start the server:

```bash
uv run python src/team_server.py
```

2. Test with the provided test client:

```bash
uv run python test_client.py
```

3. Or test with a remote URL using ngrok:

```bash
uv run python test_client.py https://your-ngrok-url.ngrok-free.app/mcp
```

### Remote Testing with ngrok

1. Start server with ngrok:

```bash
uv run python scripts/run_with_ngrok.py
```

2. Use the displayed public URL (e.g., `https://abc123.ngrok.io/mcp`) to connect from any MCP client.

## Development

### Adding New Tools

To add new tools, edit `src/team_server.py`:

```python
@mcp.tool()
def your_new_tool(param: str) -> str:
    """Description of your tool"""
    return f"Result for {param}"
```

### Updating Dependencies

When adding new dependencies:

1. Add to `pyproject.toml`
2. Regenerate `requirements.txt`:

```bash
uv pip compile pyproject.toml > requirements.txt
```

3. Install:
   - uv: `uv sync`
   - pip: `pip install -r requirements.txt`

## Deployment

For production deployment:

1. Set environment variables appropriately
2. Use a process manager like systemd or supervisor
3. Consider using a reverse proxy (nginx, Apache) for SSL termination
4. Ensure firewall rules allow traffic on your configured port

### Example systemd service

```ini
[Unit]
Description=Team MCP Server
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/mcp-server
Environment="PATH=/usr/bin:/usr/local/bin"
ExecStart=/usr/bin/python /path/to/mcp-server/src/team_server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## Troubleshooting

### Server won't start

- Check Python version: `python --version` (needs 3.10+)
- Verify all dependencies are installed
- Check if port 8000 is already in use

### ngrok issues

- Ensure you have an ngrok account and auth token
- Check ngrok status at <https://dashboard.ngrok.com>
- Verify firewall isn't blocking ngrok

### MCP client can't connect

- Verify server is running and accessible
- Check the endpoint URL is correct
- Ensure you're using HTTP streaming transport (not SSE)

## License

MIT License - see LICENSE file for details