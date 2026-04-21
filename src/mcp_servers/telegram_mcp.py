# src/mcp_servers/telegram_mcp.py (improved version)
import asyncio
import os
import sys
import httpx
from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types
from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    print("Error: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in .env", file=sys.stderr)
    sys.exit(1)

# Tool implementation: send a message (async, no markdown, full error reporting)
async def send_message(text: str) -> str:
    """Send a plain text message to the user's Telegram chat."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        # No parse_mode -> plain text, never fails due to formatting
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return "✅ Message sent successfully"
    except httpx.HTTPStatusError as e:
        # Return full Telegram error details
        error_body = e.response.text
        return f"❌ Telegram API error (status {e.response.status_code}): {error_body}"
    except Exception as e:
        return f"❌ Failed to send message: {str(e)}"


# Create MCP server
app = Server("telegram-server")

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="send_message",
            description="Send a text message to the user's Telegram chat",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The message text to send"
                    }
                },
                "required": ["text"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "send_message":
        text = arguments.get("text")
        if not text:
            raise ValueError("Missing 'text' argument")
        result = await send_message(text)
        return [types.TextContent(type="text", text=result)]
    raise ValueError(f"Unknown tool: {name}")

async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())