#!/usr/bin/env python3
"""
Run the MCP server with ngrok tunnel for remote testing
"""

import subprocess
import sys
import time
import os
import argparse
from pathlib import Path
from pyngrok import ngrok
from dotenv import load_dotenv

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Run MCP server with ngrok tunnel")
    parser.add_argument("--tunnel-only", action="store_true", 
                       help="Only create ngrok tunnel (don't start server)")
    args = parser.parse_args()
    
    server_host = os.getenv("MCP_HOST", "0.0.0.0")
    server_port = int(os.getenv("MCP_PORT", "8000"))
    server_path = os.getenv("MCP_PATH", "/mcp")
    ngrok_auth_token = os.getenv("NGROK_AUTH_TOKEN")
    
    if ngrok_auth_token:
        ngrok.set_auth_token(ngrok_auth_token)
    
    server_process = None
    
    if not args.tunnel_only:
        server_script = Path(__file__).parent.parent / "src" / "team_server.py"
        print(f"Starting MCP server on port {server_port}...")
        server_process = subprocess.Popen(
            [sys.executable, str(server_script)],
            env={**os.environ}
        )
        time.sleep(2)
    
    try:
        print(f"Creating ngrok tunnel to localhost:{server_port}...")
        public_url = ngrok.connect(server_port, "http")
        
        print("\n" + "="*60)
        print("🚀 MCP Server is accessible via ngrok tunnel!")
        print("="*60)
        print(f"Local URL:  http://localhost:{server_port}{server_path}")
        print(f"Public URL: {public_url}{server_path}")
        print("="*60)
        print("\nYour MCP server is now accessible from anywhere!")
        print("Use the public URL to connect from remote MCP clients.")
        print("\nPress Ctrl+C to close the tunnel...")
        
        if server_process:
            server_process.wait()
        else:
            # Keep running until interrupted
            while True:
                time.sleep(1)
        
    except KeyboardInterrupt:
        print("\n\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if server_process and server_process.poll() is None:
            server_process.terminate()
            server_process.wait()
        
        ngrok.disconnect(public_url.public_url if 'public_url' in locals() else None)
        ngrok.kill()
        print("Tunnel closed.")


if __name__ == "__main__":
    main()
