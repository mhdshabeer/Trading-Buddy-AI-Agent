import os
from datetime import datetime
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_groq import ChatGroq

load_dotenv()

# Define a simple tool that returns the current time
@tool
def get_current_time() -> str:
    """Returns the current date and time."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Initialize the LLM
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY")
)

# Create agent with the time tool
agent = create_agent(model=llm, tools=[get_current_time])

# Ask a question that requires the tool
result = agent.invoke({"messages": "What time is it right now?"})

# Print the agent's response
print(result)