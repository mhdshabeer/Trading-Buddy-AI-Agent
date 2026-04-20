import os
import MetaTrader5 as mt5
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_groq import ChatGroq

load_dotenv()

@tool
def get_account_balance() -> str:
    """Returns the current account balance."""
    if not mt5.initialize():
        return "Failed to initialize MT5 connection"
    else:
        account = mt5.account_info()
        mt5.shutdown()
    if account:
        return f"Account balance: {account.balance} {account.currency}"
    else:
        return "Failed to fetch account info"
        
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY")
)

agent = create_agent(model=llm, tools=[get_account_balance])

result = agent.invoke({"messages": "What is my account balance?"})
print(result["messages"][-1].content)