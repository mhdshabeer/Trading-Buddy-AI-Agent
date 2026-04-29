# scripts/test_telegram_polling.py (with Notion mirror)
import asyncio
import json
import os
import sys
import re
import uuid
from collections import deque
from datetime import datetime, timezone
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
import httpx
from groq import Groq
from faster_whisper import WhisperModel
import pytz

load_dotenv()

# ---------- Persistence for processed tickets ----------
PROCESSED_TICKETS_FILE = "processed_tickets.json"

def load_processed_tickets() -> set:
    """Load the set of processed ticket IDs from a JSON file."""
    if os.path.exists(PROCESSED_TICKETS_FILE):
        try:
            with open(PROCESSED_TICKETS_FILE, "r") as f:
                data = json.load(f)
                return set(data)
        except:
            return set()
    return set()

def save_processed_tickets(tickets: set):
    """Save the set of processed ticket IDs to a JSON file."""
    with open(PROCESSED_TICKETS_FILE, "w") as f:
        json.dump(list(tickets), f)

# ---------- Global state ----------
trade_queue = deque()
current_trade = None
awaiting_psychology = False
processing_lock = asyncio.Lock()
last_processed_tickets = load_processed_tickets()   # loaded from file

# ---------- Whisper model ----------
WHISPER_MODEL_SIZE = "base"
model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")

# ---------- Helper: clean empty strings ----------
def clean_extracted(data: dict) -> dict:
    optional_fields = ["htf_bias", "trade_logic", "confluences", "psychology_during", "psychology_after", "mistake", "learning"]
    for field in optional_fields:
        if field in data and data[field] == "":
            data[field] = None
    return data

# ---------- Voice helpers ----------
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

# ---------- Extract psychology ----------
async def extract_trade_psychology(text: str) -> dict:
    prompt = f"""You are a trading journal assistant. Extract ONLY the following fields from the user's text. Return ONLY valid JSON, no extra text.

Fields:
- htf_bias (string, "bullish", "bearish", or "neutral", if not mentioned use null)
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

# ---------- Digest generation ----------
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

# ---------- MT5 polling (with persistence) ----------
async def mt5_polling_task(mt5_client_tools, send_tool):
    global trade_queue, last_processed_tickets
    get_trades_tool = next((t for t in mt5_client_tools if t.name == "get_closed_trades"), None)
    if not get_trades_tool:
        print("❌ MT5 polling: get_closed_trades tool not found")
        return

    print("MT5 polling started (every 5 seconds)...")
    while True:
        try:
            result = await get_trades_tool.ainvoke({"days_back": 1})
            content = result.content if hasattr(result, 'content') else result
            trades = []
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and "text" in item:
                        try:
                            parsed = json.loads(item["text"])
                            if isinstance(parsed, list):
                                trades.extend(parsed)
                        except:
                            pass
            elif isinstance(content, str):
                try:
                    parsed = json.loads(content)
                    if isinstance(parsed, list):
                        trades = parsed
                except:
                    pass
            for trade in trades:
                profit = trade.get("profit", 0.0)
                if profit == 0.0:
                    continue
                ticket = trade.get("ticket")
                pos_id = trade.get("position_id", ticket)
                if pos_id and pos_id not in last_processed_tickets:
                    last_processed_tickets.add(pos_id)
                    save_processed_tickets(last_processed_tickets)   # persist immediately
                    symbol = trade.get("symbol", "UNKNOWN")
                    action = trade.get("action", "buy")
                    direction = "long" if action == "buy" else "short"
                    volume = trade.get("volume", 0.0)
                    exit_price = trade.get("price", 0.0)
                    trade_date = datetime.now().strftime("%Y-%m-%d")
                    pending = {
                        "trade_date": trade_date,
                        "asset": symbol,
                        "lot_size": volume,
                        "entry_price": exit_price,
                        "exit_price": exit_price,
                        "direction": direction,
                        "profit_loss": profit,
                        "ticket": ticket
                    }
                    trade_queue.append(pending)
                    print(f"   → Trade {pos_id} (profit: {profit}) added to queue (size: {len(trade_queue)})")
        except Exception as e:
            print(f"⚠️ MT5 polling error: {e}")
        await asyncio.sleep(5)

# ---------- Queue worker (accepts notion_tool) ----------
async def queue_worker(send_tool, insert_tool, notion_tool):
    global trade_queue, current_trade, awaiting_psychology
    while True:
        if not trade_queue:
            await asyncio.sleep(1)
            continue
        async with processing_lock:
            if current_trade is not None:
                await asyncio.sleep(1)
                continue
            current_trade = trade_queue.popleft()
        profit = current_trade.get("profit_loss", 0.0)
        symbol = current_trade.get("asset", "UNKNOWN")
        profit_str = f"+${profit:.2f}" if profit >= 0 else f"-${abs(profit):.2f}"
        await send_tool.ainvoke({"text": f"📊 *Trade closed:* {symbol} {profit_str}\nPlease explain your HTF bias, trade logic, confluences, psychology, mistake, and learning.\nType /skip to skip this trade."})
        awaiting_psychology = True
        while awaiting_psychology:
            await asyncio.sleep(1)

# ---------- Main ----------
async def main():
    global awaiting_psychology, current_trade, trade_queue

    client = MultiServerMCPClient({
        "telegram": {
            "command": sys.executable,
            "args": ["src/mcp_servers/telegram_mcp.py"],
            "transport": "stdio"
        },
        "postgresql": {
            "command": sys.executable,
            "args": ["src/mcp_servers/postgresql_mcp.py"],
            "transport": "stdio"
        },
        "mt5": {
            "command": sys.executable,
            "args": ["src/mcp_servers/mt5_mcp.py"],
            "transport": "stdio"
        },
        "notion": {
            "command": sys.executable,
            "args": ["src/mcp_servers/notion_mcp.py"],
            "transport": "stdio"
        }
    })

    tools = await client.get_tools()
    poll_tool = next((t for t in tools if t.name == "poll_updates"), None)
    send_tool = next((t for t in tools if t.name == "send_message"), None)
    insert_tool = next((t for t in tools if t.name == "insert_trade"), None)
    notion_tool = next((t for t in tools if t.name == "create_journal_page"), None)

    if not poll_tool or not send_tool or not insert_tool:
        print("❌ Required tools not found (telegram poll/send, postgres insert)")
        return

    if not notion_tool:
        print("⚠️ Notion tool not found – Notion mirror disabled.")
    else:
        print("✅ Notion tool found – journal pages will be mirrored to Notion.")

    mt5_tools = [t for t in tools if t.name == "get_closed_trades"]
    if not mt5_tools:
        print("⚠️ MT5 tools not found, MT5 polling disabled.")
    else:
        print("✅ MT5 tools found. Starting MT5 polling and queue worker.")

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    allowed_commands = {"digest", "/digest", "news", "/news", "skip", "/skip"}

    print("Listening for messages... Commands: /digest, /news, /skip")
    print("MT5 polling active. New closed trades will be added to queue and processed one by one.\n")

    mt5_task = asyncio.create_task(mt5_polling_task(mt5_tools, send_tool))
    queue_task = asyncio.create_task(queue_worker(send_tool, insert_tool, notion_tool))

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
                if text in ["skip", "/skip"]:
                    if awaiting_psychology and current_trade is not None:
                        print("   → Skipping current trade")
                        await send_tool.ainvoke({"text": f"⏭️ Skipped trade {current_trade.get('asset', 'UNKNOWN')}. Moving to next."})
                        awaiting_psychology = False
                        current_trade = None
                    else:
                        await send_tool.ainvoke({"text": "ℹ️ No pending trade to skip."})
                    continue
                if text in ["digest", "/digest", "news", "/news"]:
                    print("   → Generating digest...")
                    digest = await generate_digest()
                    await send_tool.ainvoke({"text": digest})
                    print("   → Digest sent.")
                    continue
                if awaiting_psychology and current_trade is not None:
                    print("   → Processing as psychology entry (text)...")
                    extracted = await extract_trade_psychology(text)
                    extracted = clean_extracted(extracted)
                    complete_entry = {**current_trade, **extracted}
                    # Generate a unique trade_id
                    complete_entry["trade_id"] = f"{complete_entry['trade_date']}_{complete_entry['asset']}_{uuid.uuid4().hex[:6]}"
                    print(f"   → Complete entry: {json.dumps(complete_entry, indent=2)}")
                    # Save to PostgreSQL
                    db_result = await insert_tool.ainvoke({"trade_data": complete_entry})
                    print(f"   → DB result: {db_result}")
                    # Save to Notion
                    notion_msg = ""
                    if notion_tool:
                        notion_result = await notion_tool.ainvoke({"trade_data": complete_entry})
                        print(f"   → Notion result: {notion_result}")
                        notion_msg = f"\nNotion: {notion_result}"
                    else:
                        notion_msg = "\nNotion: disabled"
                    await send_tool.ainvoke({"text": f"✅ Journal saved for {current_trade.get('asset')}.\nDB: {db_result}{notion_msg}"})
                    awaiting_psychology = False
                    current_trade = None
                    continue
                print(f"   → Text (not a command): {text}")

            elif msg_type == "voice":
                file_id = upd.get("file_id")
                print("   → Voice message detected, transcribing...")
                transcript = await transcribe_voice(bot_token, file_id)
                print(f"   → Transcription: {transcript}")
                if awaiting_psychology and current_trade is not None:
                    print("   → Processing as psychology entry (voice)...")
                    extracted = await extract_trade_psychology(transcript)
                    extracted = clean_extracted(extracted)
                    complete_entry = {**current_trade, **extracted}
                    complete_entry["trade_id"] = f"{complete_entry['trade_date']}_{complete_entry['asset']}_{uuid.uuid4().hex[:6]}"
                    print(f"   → Complete entry: {json.dumps(complete_entry, indent=2)}")
                    db_result = await insert_tool.ainvoke({"trade_data": complete_entry})
                    print(f"   → DB result: {db_result}")
                    notion_msg = ""
                    if notion_tool:
                        notion_result = await notion_tool.ainvoke({"trade_data": complete_entry})
                        print(f"   → Notion result: {notion_result}")
                        notion_msg = f"\nNotion: {notion_result}"
                    else:
                        notion_msg = "\nNotion: disabled"
                    await send_tool.ainvoke({"text": f"✅ Journal saved for {current_trade.get('asset')}.\nDB: {db_result}{notion_msg}"})
                    awaiting_psychology = False
                    current_trade = None
                else:
                    await send_tool.ainvoke({"text": f"📝 Transcription:\n{transcript}"})
            else:
                print(f"   → Unhandled type: {msg_type}")

        await asyncio.sleep(2)

    await asyncio.gather(mt5_task, queue_task)

if __name__ == "__main__":
    asyncio.run(main())