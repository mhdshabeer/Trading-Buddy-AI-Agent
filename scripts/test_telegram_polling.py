# scripts/test_telegram_polling.py
import asyncio
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
import httpx
from groq import Groq
import pytz
import re

load_dotenv()

# ---------- Robust UTC → IST converter (handles ISO and legacy formats) ----------
def utc_to_ist(time_str: str) -> str:
    """Convert various UTC datetime formats to IST time string (HH:MM AM/PM)."""
    if not time_str or time_str == "Time TBA":
        return "Time TBA"
    try:
        # Try ISO format with timezone (e.g., 2026-04-19T18:45:00-04:00)
        if 'T' in time_str and ('+' in time_str or '-' in time_str[10:]):
            dt_utc = datetime.fromisoformat(time_str)
            # Convert to UTC if it has offset
            dt_utc = dt_utc.astimezone(timezone.utc)
        # Try legacy format "YYYY-MM-DD HH:MM:SS"
        elif re.match(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', time_str):
            dt_utc = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            dt_utc = dt_utc.replace(tzinfo=timezone.utc)
        else:
            return "Time TBA"
        # Convert to IST
        ist = pytz.timezone('Asia/Kolkata')
        dt_ist = dt_utc.astimezone(ist)
        return dt_ist.strftime("%I:%M %p").lstrip('0')
    except Exception:
        return "Time TBA"

# ---------- Digest Generation ----------
async def generate_digest() -> str:
    today_date = datetime.now().strftime("%A, %B %d, %Y")
    today_str = datetime.now().strftime("%Y-%m-%d")

    eco_url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    high_impact_events = []
    all_events_summary = []
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(eco_url)
            data = resp.json()
            today_events = [e for e in data if e.get('date', '')[:10] == today_str]
            for event in today_events:
                country = event.get('country', '')
                title = event.get('title', '')
                impact = event.get('impact', '')
                # Use the full datetime from 'date' field (may be ISO)
                full_datetime = event.get('date', '')
                time_ist = utc_to_ist(full_datetime)
                if impact == 'High':
                    high_impact_events.append(f"{country} - {title} - {time_ist}")
                all_events_summary.append(f"{country} {title} ({impact} impact)")
    except Exception as e:
        high_impact_events = [f"Error fetching calendar: {e}"]
        all_events_summary = ["Economic data unavailable"]

    # Finnhub news
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

    # LLM prompt
    eco_summary = "\n".join(all_events_summary) if all_events_summary else "No economic events today."
    news_text = "\n".join(news_items) if news_items else "No news available."

    prompt = f"""You are a trading assistant. Based on the following economic events and market news, write ONE short paragraph (max 100 words) describing the current economic state and what traders should watch. Do NOT list the events again. End with a one-sentence actionable recommendation.

Economic events today:
{eco_summary}

Market news:
{news_text}
"""

    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        paragraph = completion.choices[0].message.content
    except Exception as e:
        paragraph = f"❌ LLM failed: {str(e)}"

    if high_impact_events:
        events_list = "\n".join(f"🔴 {line}" for line in high_impact_events)
        red_section = f"**Red‑folder news today (IST):**\n{events_list}"
    else:
        red_section = "No high‑impact economic events today."

    return f"📅 {today_date}\n\n{red_section}\n\n{paragraph}"

# ---------- Main Polling Loop ----------
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

    allowed_commands = {"digest", "/digest", "news", "/news"}
    print("Listening... Send 'digest' or 'news' (times in IST).\n")

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
            print(f"📩 {upd}")
            text = upd.get("text", "").strip().lower()
            if text in allowed_commands:
                print("   → Generating digest...")
                digest = await generate_digest()
                await send_tool.ainvoke({"text": digest})
                print("   → Digest sent.")

        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())