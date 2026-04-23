# scripts/test_telegram_polling.py
import asyncio
import json
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
import httpx
from groq import Groq

load_dotenv()

# ---------- Digest Generation (today's events only, sorted by impact) ----------
async def generate_digest() -> str:
    """Fetch economic calendar + news, prepend current date, return LLM summary.
    Filters only today's events and prioritises high-impact (red folder) news.
    """
    today_date = datetime.now().strftime("%A, %B %d, %Y")
    today_str = datetime.now().strftime("%Y-%m-%d")  # format used in JSON

    # 1. Economic calendar (Forex Factory)
    eco_url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    eco_events = []
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(eco_url)
            data = resp.json()
            # Filter for today's events
            today_events = []
            for event in data:
                event_date = event.get('date', '')[:10]
                if event_date == today_str:
                    today_events.append(event)
            # Sort by impact (High > Medium > Low)
            impact_order = {'High': 0, 'Medium': 1, 'Low': 2, '': 3}
            today_events.sort(key=lambda x: impact_order.get(x.get('impact', ''), 3))
            # Build formatted list
            for event in today_events[:10]:
                country = event.get('country', '')
                title = event.get('title', '')
                impact = event.get('impact', '')
                if impact == 'High':
                    impact_display = '🔴 High'
                elif impact == 'Medium':
                    impact_display = '🟠 Medium'
                else:
                    impact_display = '🟡 Low'
                eco_events.append(f"{country}: {title} - {impact_display}")
    except Exception as e:
        eco_events = [f"Error fetching economic calendar: {e}"]

    # 2. Market news (Finnhub)
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

    # 3. Build prompt for LLM
    if eco_events:
        eco_text = "\n".join(eco_events)
    else:
        eco_text = "No high‑impact economic events scheduled for today."

    news_text = "\n".join(news_items) if news_items else "No news available."

    prompt = f"""You are a trading assistant. Create a very short morning market digest (max 150 words) based on:

Today's economic events (priority sorted by impact):
{eco_text}

Market news:
{news_text}

Highlight the most impactful events. Be concise and actionable for a trader. End with a one-sentence recommendation.
"""

    # 4. Call Groq
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        digest_body = completion.choices[0].message.content
        return f"📅 {today_date}\n\n{digest_body}"
    except Exception as e:
        return f"❌ LLM failed: {str(e)}"

# ---------- Main Polling Loop (simplified commands: digest, /digest, news, /news) ----------
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

    # Allowed commands (case‑insensitive)
    allowed_commands = {"digest", "/digest", "news", "/news"}

    print("Listening for messages... Send 'digest' or 'news' to get market briefing.\n")

    while True:
        result = await poll_tool.ainvoke({})
        content = result.content if hasattr(result, 'content') else result

        updates_raw = []
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and "text" in item:
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

        for upd in updates_raw:
            print(f"📩 Received: {upd}")
            text = upd.get("text", "").strip().lower()
            if text in allowed_commands:
                print("   → Generating digest...")
                digest = await generate_digest()
                await send_tool.ainvoke({"text": digest})
                print("   → Digest sent.")

        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())