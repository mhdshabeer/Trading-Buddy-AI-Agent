# scripts/07_telegram_mcp_client.py
import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from langchain_groq import ChatGroq

load_dotenv()

async def main():
    # Connect to the Telegram MCP server
    SERVER_PATH = Path(__file__).parent.parent / "src" / "mcp_servers" / "telegram_mcp.py"
    client = MultiServerMCPClient({
        "telegram": {
            "command": sys.executable,
            "args": [str(SERVER_PATH)],
            "transport": "stdio"
        }
    })

    tools = await client.get_tools()
    print(f"Discovered tools: {[tool.name for tool in tools]}")

    # Create agent with the Telegram tool
    llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=os.getenv("GROQ_API_KEY"))
    agent = create_agent(model=llm, tools=tools)

    # Ask the agent to send a message
    result = await agent.ainvoke({"messages": "Send a message to my Telegram saying 'Trading Buddy is online!'"})
    print("\nAgent response:", result["messages"][-1].content)

if __name__ == "__main__":
    asyncio.run(main())