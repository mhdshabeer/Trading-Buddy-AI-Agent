# scripts/test_telegram_polling.py
import asyncio
import json
import os
import sys
import re
from datetime import datetime, timezone
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
import httpx
from groq import Groq
from faster_whisper import WhisperModel
import pytz

load_dotenv()

# ---------- Whisper model (local) ----------
WHISPER_MODEL_SIZE = "base"
model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")

# ---------- State ----------
awaiting_psychology = False
pending_trade = None   # MT5 trade data (auto fields)

# ---------- Voice helpers (same as before) ----------
async def download_voice_file(bot_token: str, file_id: str) -> bytes:
    async with httpx.AsyncClient() as client:
        get_file = await client.get(
            f"https://api.telegram.org/bot{bot_token}/getFile",
            params={"file_id": file_id}
        )
        file_data = get_file.json()
        if not file_data.get("ok"):
            raise Exception(f"Failed to get file: {file_data}")
        file_path = file_data["result"]["file_path"]
        download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
        resp = await client.get(download_url)
        return resp.content

async def transcribe_voice(bot_token: str, file_id: str) -> str:
    ogg_bytes = await download_voice_file(bot_token, file_id)
    temp_path = f"temp_voice_{file_id}.ogg"
    try:
        with open(temp_path, "wb") as f:
            f.write(ogg_bytes)
        segments, _ = model.transcribe(temp_path, language="en", beam_size=3)
        text = " ".join(segment.text for segment in segments)
        return text if text.strip() else "(no speech detected)"
    except Exception as e:
        return f"Transcription error: {e}"
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)

# ---------- Extract only user psychology fields ----------
async def extract_trade_psychology(text: str) -> dict:
    prompt = f"""You are a trading journal assistant. Extract ONLY the following fields from the user's text. Return ONLY valid JSON, no extra text.

Fields:
- htf_bias (string, "bullish", "bearish", or "neutral")
- trade_logic (string, short sentence explaining why you took the trade)
- confluences (string, comma-separated, e.g., "FVG, OB, IFVG")
- psychology_during (string, how you felt while trade was open)
- psychology_after (string, how you felt after closing)
- mistake (string, e.g., "early/rushed entry", "held too long", "greedy", "early sell")
- learning (string, what to improve next time)

User text: {text}

JSON:
"""
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    completion = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        response_format={"type": "json_object"}
    )
    content = completion.choices[0].message.content
    try:
        return json.loads(content)
    except Exception as e:
        return {"error": "Failed to parse LLM output", "raw": content, "exception": str(e)}

# ---------- Digest generation (unchanged) ----------
def utc_to_ist(time_str: str) -> str:
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
        async with httpx.AsyncClient() as client:
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

# ---------- Main polling loop ----------
async def main():
    global awaiting_psychology, pending_trade

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

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    allowed_commands = {"digest", "/digest", "news", "/news", "simulate", "/simulate"}

    print("Listening for messages... Commands: /digest, /simulate (to test journaling)\n")

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
            msg_type = upd.get("type")
            print(f"📩 Received: {upd}")

            if msg_type == "text":
                text = upd.get("text", "").strip().lower()
                # Simulate trade (replace with real MT5 polling later)
                if text in ["simulate", "/simulate"]:
                    # Simulated MT5 trade data (auto fields)
                    pending_trade = {
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "asset": "EURUSD",
                        "lot_size": 0.1,
                        "entry_price": 1.0850,
                        "exit_price": 1.0875,
                        "direction": "long",
                        "profit_loss": 120.50
                    }
                    awaiting_psychology = True
                    await send_tool.ainvoke({"text": "📊 *Trade closed:* EURUSD +$120.50\nPlease explain your HTF bias, trade logic, confluences, psychology, mistake, and learning (voice or text)."})
                    print("   → Simulated trade, awaiting psychology...")
                    continue
                # Digest command
                if text in allowed_commands and text not in ["simulate", "/simulate"]:
                    print("   → Generating digest...")
                    digest = await generate_digest()
                    await send_tool.ainvoke({"text": digest})
                    print("   → Digest sent.")
                    continue
                # Awaiting psychology
                if awaiting_psychology:
                    print("   → Processing as psychology entry (text)...")
                    extracted = await extract_trade_psychology(text)
                    # Merge MT5 data with user fields
                    complete_entry = {**pending_trade, **extracted} if pending_trade else extracted
                    print(f"   → Complete entry: {json.dumps(complete_entry, indent=2)}")
                    # TODO: Save to PostgreSQL + Notion
                    await send_tool.ainvoke({"text": f"✅ Journal saved. Merged entry:\n```json\n{json.dumps(complete_entry, indent=2)}\n```"})
                    awaiting_psychology = False
                    pending_trade = None
                    continue
                print(f"   → Text (not a command): {text}")

            elif msg_type == "voice":
                file_id = upd.get("file_id")
                print("   → Voice message detected, transcribing...")
                transcript = await transcribe_voice(bot_token, file_id)
                print(f"   → Transcription: {transcript}")
                if awaiting_psychology:
                    print("   → Processing as psychology entry (voice)...")
                    extracted = await extract_trade_psychology(transcript)
                    complete_entry = {**pending_trade, **extracted} if pending_trade else extracted
                    print(f"   → Complete entry: {json.dumps(complete_entry, indent=2)}")
                    await send_tool.ainvoke({"text": f"✅ Journal saved. Merged entry:\n```json\n{json.dumps(complete_entry, indent=2)}\n```"})
                    awaiting_psychology = False
                    pending_trade = None
                else:
                    await send_tool.ainvoke({"text": f"📝 Transcription:\n{transcript}"})
            else:
                print(f"   → Unhandled type: {msg_type}")

        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())