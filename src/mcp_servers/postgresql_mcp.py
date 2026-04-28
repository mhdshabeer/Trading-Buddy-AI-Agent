# src/mcp_servers/postgresql_mcp.py
import asyncio
import os
import sys
from datetime import datetime
import asyncpg
from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types
from dotenv import load_dotenv

load_dotenv()

pool = None

async def get_pool():
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "trading_buddy"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", ""),
            min_size=1,
            max_size=5
        )
    return pool

async def insert_trade(trade_data: dict) -> str:
    required = ["trade_date", "asset", "lot_size", "entry_price", "exit_price", "direction", "profit_loss"]
    for f in required:
        if f not in trade_data:
            return f"❌ Missing required field: {f}"
    try:
        # Convert date string to date object
        if isinstance(trade_data["trade_date"], str):
            trade_date_obj = datetime.strptime(trade_data["trade_date"], "%Y-%m-%d").date()
        else:
            trade_date_obj = trade_data["trade_date"]

        # Convert numeric fields to float
        lot_size = float(trade_data["lot_size"])
        entry_price = float(trade_data["entry_price"])
        exit_price = float(trade_data["exit_price"])
        profit_loss = float(trade_data["profit_loss"])

        p = await get_pool()
        async with p.acquire() as conn:
            await conn.execute("""
                INSERT INTO trades (
                    trade_date, asset, lot_size, entry_price, exit_price,
                    direction, profit_loss, htf_bias, trade_logic, confluences,
                    psychology_during, psychology_after, mistake, learning
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            """,
                trade_date_obj,
                trade_data["asset"],
                lot_size,
                entry_price,
                exit_price,
                trade_data["direction"],
                profit_loss,
                trade_data.get("htf_bias"),
                trade_data.get("trade_logic"),
                trade_data.get("confluences"),
                trade_data.get("psychology_during"),
                trade_data.get("psychology_after"),
                trade_data.get("mistake"),
                trade_data.get("learning")
            )
        return "✅ Trade inserted successfully"
    except Exception as e:
        return f"❌ Database error: {str(e)}"

app = Server("postgresql-server")

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="insert_trade",
            description="Insert a complete trade journal entry into PostgreSQL",
            inputSchema={
                "type": "object",
                "properties": {
                    "trade_data": {"type": "object"}
                },
                "required": ["trade_data"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "insert_trade":
        result = await insert_trade(arguments["trade_data"])
        return [types.TextContent(type="text", text=result)]
    raise ValueError(f"Unknown tool: {name}")

async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())