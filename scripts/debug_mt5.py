import asyncio
import json
import sys
from langchain_mcp_adapters.client import MultiServerMCPClient

async def main():
    client = MultiServerMCPClient({
        "mt5": {
            "command": sys.executable,
            "args": ["src/mcp_servers/mt5_mcp.py"],
            "transport": "stdio"
        }
    })
    tools = await client.get_tools()
    get_trades = next((t for t in tools if t.name == "get_closed_trades"), None)
    if not get_trades:
        print("Tool not found")
        return
    result = await get_trades.ainvoke({"days_back": 1})
    content = result.content if hasattr(result, 'content') else result
    print("Raw content:", content)
    if isinstance(content, str):
        try:
            trades = json.loads(content)
            print(f"Found {len(trades)} trades in last 1 day")
        except:
            print("JSON parse error")
    else:
        print("Content is not string")

asyncio.run(main())