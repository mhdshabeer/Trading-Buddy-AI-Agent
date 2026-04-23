# src/services/digest.py
import os
from datetime import datetime
import httpx
from groq import Groq
import pytz
import re

def utc_to_ist(time_str: str) -> str:
    """Convert UTC datetime (ISO or legacy) to IST time string."""
    if not time_str or time_str == "Time TBA":
        return "Time TBA"
    try:
        if 'T' in time_str and ('+' in time_str or '-' in time_str[10:]):
            dt_utc = datetime.fromisoformat(time_str).astimezone(pytz.UTC)
        elif re.match(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', time_str):
            dt_utc = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC)
        else:
            return "Time TBA"
        ist = pytz.timezone('Asia/Kolkata')
        return dt_utc.astimezone(ist).strftime("%I:%M %p").lstrip('0')
    except:
        return "Time TBA"

async def generate_digest() -> str:
    today_date = datetime.now().strftime("%A, %B %d, %Y")
    today_str = datetime.now().strftime("%Y-%m-%d")

    eco_url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    high_impact_events = []
    all_events_summary = []
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(eco_url)
        data = resp.json()
        today_events = [e for e in data if e.get('date', '')[:10] == today_str]
        for event in today_events:
            country = event.get('country', '')
            title = event.get('title', '')
            impact = event.get('impact', '')
            full_datetime = event.get('date', '')
            time_ist = utc_to_ist(full_datetime)
            if impact == 'High':
                high_impact_events.append(f"{country} - {title} - {time_ist}")
            all_events_summary.append(f"{country} {title} ({impact} impact)")

    finnhub_key = os.getenv("FINNHUB_API_KEY")
    news_items = []
    if finnhub_key:
        news_url = f"https://finnhub.io/api/v1/news?category=forex&token={finnhub_key}"
        resp = await client.get(news_url)
        articles = resp.json()
        for art in articles[:3]:
            news_items.append(f"- {art['headline']}")
    else:
        news_items = ["No Finnhub API key found."]

    eco_summary = "\n".join(all_events_summary) if all_events_summary else "No economic events today."
    news_text = "\n".join(news_items) if news_items else "No news available."

    prompt = f"""You are a trading assistant. Based on the following economic events and market news, write ONE short paragraph (max 100 words) describing the current economic state and what traders should watch. Do NOT list the events again. End with a one-sentence actionable recommendation.

Economic events today:
{eco_summary}

Market news:
{news_text}
"""

    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    completion = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    paragraph = completion.choices[0].message.content

    if high_impact_events:
        events_list = "\n".join(f"🔴 {line}" for line in high_impact_events)
        red_section = f"**Red‑folder news today (IST):**\n{events_list}"
    else:
        red_section = "No high‑impact economic events today."

    return f"📅 {today_date}\n\n{red_section}\n\n{paragraph}"