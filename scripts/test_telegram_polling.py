# scripts/test_telegram_polling.py (fixed – unwraps MCP TextContent)
import asyncio
import json
import os
import sys
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
import httpx
from groq import Groq

load_dotenv()

# ---------- Digest Generation ----------
async def generate_digest() -> str:
    """Fetch economic calendar + news and return LLM-generated summary."""
    eco_url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    eco_events = []
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(eco_url)
            data = resp.json()
            for event in data[:5]:
                country = event.get('country', '')
                title = event.get('title', '')
                impact = event.get('impact', '')
                eco_events.append(f"{country}: {title} - Impact: {impact}")
    except Exception as e:
        eco_events = [f"Error fetching economic calendar: {e}"]

    finnhub_key = os.getenv("FINNHUB_API_KEY")
    news_items = []
    if finnhub_key:
        news_url = f"https://finnhub.io/api/v1/news?category=forex&token={finnhub_key}"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(news_url)
                articles = resp.json()
                for art in articles[:3]:
                    news_items.append(f"- {art['headline']}")
        except Exception as e:
            news_items = [f"Error fetching news: {e}"]
    else:
        news_items = ["No Finnhub API key found. Skipping news."]

    eco_text = "\n".join(eco_events) if eco_events else "No economic events today."
    news_text = "\n".join(news_items) if news_items else "No news available."

    prompt = f"""You are a trading assistant. Create a very short morning market digest (max 150 words) based on:
Economic events today:
{eco_text}

Market news:
{news_text}

Highlight high-impact events. Be concise and actionable for a trader. End with a one-sentence recommendation.
"""

    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"❌ LLM failed: {str(e)}"

# ---------- Main Polling Loop (with correct unwrapping) ----------
async def main():
    client = MultiServerMCPClient({
        "telegram": {
            "command": sys.executable,
            "args": ["src/mcp_servers/telegram_mcp.py"],
            "transport": "stdio"
        }
    })

    tools = await client.get_tools()
    poll_tool = next((t for t in tools if t.name == "poll_updates"), None)
    send_tool = next((t for t in tools if t.name == "send_message"), None)

    if not poll_tool or not send_tool:
        print("❌ Required tools not found")
        return

    print("Listening for messages... Send /digest for market briefing.\n")

    while True:
        result = await poll_tool.ainvoke({})
        # result is a list of ToolMessage/TextContent objects
        content = result.content if hasattr(result, 'content') else result

        # Unwrap MCP response: content may be a list of dicts with 'text' field
        updates_raw = []
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    # item["text"] is the JSON string from poll_updates
                    try:
                        parsed = json.loads(item["text"])
                        if isinstance(parsed, list):
                            updates_raw.extend(parsed)
                    except:
                        pass
        elif isinstance(content, str):
            try:
                parsed = json.loads(content)
                if isinstance(parsed, list):
                    updates_raw = parsed
            except:
                pass

        # Now updates_raw is a list of actual Telegram update objects
        for upd in updates_raw:
            print(f"📩 Received: {upd}")
            text = upd.get("text")
            if text == "/digest":
                print("   → Generating digest...")
                digest = await generate_digest()
                await send_tool.ainvoke({"text": digest})
                print("   → Digest sent.")

        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())