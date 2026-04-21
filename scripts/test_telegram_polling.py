# scripts/test_telegram_polling.py
import asyncio
import json
import os
import sys
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()

async def main():
    client = MultiServerMCPClient({
        "telegram": {
            "command": sys.executable,
            "args": ["src/mcp_servers/telegram_mcp.py"],
            "transport": "stdio"
        }
    })

    tools = await client.get_tools()
    poll_tool = None
    for tool in tools:
        if tool.name == "poll_updates":
            poll_tool = tool
            break

    if not poll_tool:
        print("❌ poll_updates tool not found")
        return

    print("Listening for messages... (Press Ctrl+C to stop)\n")

    while True:
        result = await poll_tool.ainvoke({})
        # Extract content from ToolMessage
        content = result.content if hasattr(result, 'content') else result

        # Handle both string (JSON) and already-parsed list/dict
        if isinstance(content, str):
            try:
                updates = json.loads(content)
            except json.JSONDecodeError:
                print(f"⚠️ Invalid JSON: {content}")
                await asyncio.sleep(2)
                continue
        else:
            # Already parsed (list or dict)
            updates = content

        if isinstance(updates, list):
            for upd in updates:
                print(f"📩 Received: {upd}")
                if upd.get("type") == "text" and upd.get("text") == "/digest":
                    print("   → Digest command received (will implement later)")
        elif isinstance(updates, dict) and "error" in updates:
            print(f"⚠️ Poll error: {updates['error']}")

        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())