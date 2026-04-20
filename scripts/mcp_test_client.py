# scripts/06_mcp_client.py
import asyncio
import os
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from langchain_groq import ChatGroq

load_dotenv()

async def main():
    # Connect to the MT5 MCP server (spawns it as a subprocess)
    client = MultiServerMCPClient({
        "mt5": {
            "command": "python",
            "args": ["src/mcp_servers/mt5_mcp.py"],
            "transport": "stdio"
        }
    })

    # Get the tools from the MCP server
    tools = await client.get_tools()
    print(f"Discovered tools: {[tool.name for tool in tools]}")

    # Create agent with those tools
    llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=os.getenv("GROQ_API_KEY"))
    agent = create_agent(model=llm, tools=tools)

    # Ask a question
    result = await agent.ainvoke({"messages": "What is my trading account balance?"})
    print("\nAgent response:", result["messages"][-1].content)

if __name__ == "__main__":
    asyncio.run(main())