from calendar import c
import os
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_groq import ChatGroq

load_dotenv()

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY")
)

agent = create_agent(model=llm, tools=[])

result = agent.invoke({"messages": "What is your purpose?"})
print(result["messages"][-1].content)