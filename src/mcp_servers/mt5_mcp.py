# src/mcp_servers/mt5_mcp.py
import asyncio
import json
import sys
import MetaTrader5 as mt5
from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

# Helper to initialize MT5
def init_mt5() -> bool:
    if not mt5.initialize():
        print(f"MT5 init failed: {mt5.last_error()}", file=sys.stderr)
        return False
    print("MT5 initialized", file=sys.stderr)
    return True

# Tool implementation
async def get_account_balance() -> str:
    account = mt5.account_info()
    if account is None:
        return "Failed to fetch account info"
    return f"{account.balance} {account.currency}"

# Create MCP server
app = Server("mt5-server")

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_account_balance",
            description="Returns the current account balance with currency",
            inputSchema={"type": "object", "properties": {}, "required": []}
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "get_account_balance":
        result = await get_account_balance()
        return [types.TextContent(type="text", text=result)]
    raise ValueError(f"Unknown tool: {name}")

async def main():
    if not init_mt5():
        return
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())