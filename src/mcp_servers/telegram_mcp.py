# src/mcp_servers/telegram_mcp.py
import asyncio
import os
import sys
import json
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

# ----- File-based persistence for last_update_id -----
LAST_ID_FILE = "last_update_id.txt"

def get_last_id() -> int:
    try:
        with open(LAST_ID_FILE, "r") as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 0

def set_last_id(value: int) -> None:
    with open(LAST_ID_FILE, "w") as f:
        f.write(str(value))

# ----- Tool: send_message -----
async def send_message(text: str) -> str:
    """Send a plain text message to the user's Telegram chat."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return "✅ Message sent successfully"
    except httpx.HTTPStatusError as e:
        return f"❌ Telegram API error (status {e.response.status_code}): {e.response.text}"
    except Exception as e:
        return f"❌ Failed to send message: {str(e)}"

# ----- Tool: poll_updates (with memory) -----
async def poll_updates() -> str:
    """
    Returns new messages (text or voice) since the last call.
    Uses file-based persistence to remember the last processed update_id.
    Returns a JSON string containing a list of new updates.
    """
    offset = get_last_id() + 1
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"offset": offset, "timeout": 10}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            if not data.get("ok"):
                return f'{{"error": "{data.get("description")}"}}'

            updates = data.get("result", [])
            if not updates:
                return "[]"

            # Extract relevant info and update the stored last_update_id
            new_updates = []
            max_update_id = offset - 1  # fallback
            for upd in updates:
                msg = upd.get("message")
                if not msg:
                    continue
                # Only process messages from our authorized chat_id
                if str(msg.get("chat", {}).get("id")) != CHAT_ID:
                    continue
                update_info = {"update_id": upd["update_id"]}
                if "text" in msg:
                    update_info["type"] = "text"
                    update_info["text"] = msg["text"]
                elif "voice" in msg:
                    update_info["type"] = "voice"
                    update_info["file_id"] = msg["voice"]["file_id"]
                    update_info["duration"] = msg["voice"].get("duration")
                else:
                    continue
                new_updates.append(update_info)
                if upd["update_id"] > max_update_id:
                    max_update_id = upd["update_id"]

            # Save the highest update_id seen
            if new_updates:
                set_last_id(max_update_id)

            return json.dumps(new_updates)
    except Exception as e:
        return f'{{"error": "Failed to poll updates: {str(e)}"}}'

# ----- MCP Server Setup -----
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
                    "text": {"type": "string", "description": "The message text to send"}
                },
                "required": ["text"]
            }
        ),
        types.Tool(
            name="poll_updates",
            description="Check for new messages (text or voice) from Telegram. Returns a JSON list of updates.",
            inputSchema={"type": "object", "properties": {}, "required": []}
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
    elif name == "poll_updates":
        result = await poll_updates()
        return [types.TextContent(type="text", text=result)]
    else:
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