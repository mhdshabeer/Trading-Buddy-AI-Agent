# Trading Buddy AI

An AI-powered trading assistant that journals trades via voice, provides on‑demand market digests, and answers analytics queries. Built with Groq LLM, LangChain, MCP (Model Context Protocol), MT5, PostgreSQL, Notion, and Telegram.

---

## 🚀 Current Status (End of Day 2)

| Component | Status |
|-----------|--------|
| Groq LLM (direct call) | ✅ |
| LangChain agent (no tools) | ✅ |
| Agent with fake tool | ✅ |
| MT5 direct connection | ✅ |
| MT5 as LangChain tool | ✅ |
| MT5 as MCP server | ✅ |
| Telegram MCP – `send_message` | ✅ |
| Telegram MCP – `poll_updates` | ✅ |
| File‑based memory for Telegram | ✅ |
| Polling client (no LLM, stable) | ✅ |

**Next up (Day 3):**  
- Add `/digest` command handler (economic calendar + news → LLM summary)
- Voice memo handling (download audio → Whisper transcription)

---

## 📁 Project Structure
trading-buddy-ai/
├── src/
│ ├── mcp_servers/
│ │ ├── mt5_mcp.py # MT5 server (get_account_balance)
│ │ └── telegram_mcp.py # Telegram server (send, poll)
│ └── ... (agent, services later)
├── scripts/
│ ├── 01_llm_only.py
│ ├── 02_agent_no_tools.py
│ ├── 03_agent_fake_tool.py
│ ├── 04_mt5_direct.py
│ ├── 05_agent_mt5_tool.py
│ ├── 06_mcp_client.py
│ └── test_telegram_polling.py # Stable polling client
├── .env
├── .gitignore
├── requirements.txt
└── README.md


---

## 🧪 How to Run the Telegram Polling Client

1. Make sure `.env` contains:
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_numeric_chat_id
GROQ_API_KEY=your_groq_key


2. Install dependencies:
```bash
pip install -r requirements.txt 
```

3. Run the polling client:
python scripts/test_telegram_polling.py

4. Send a message to your bot. You'll see it printed in the terminal – once, with no repeats.

🧠 Key Technical Decisions
Telegram polling uses file‑based memory (last_update_id.txt) to avoid re‑processing old messages, even after server restarts.

No LLM in the polling loop – direct tool invocation prevents unwanted replies and infinite loops.

MCP servers run as subprocesses – clean separation of concerns.

📌 Notes
MT5 must be open and logged in on your Windows PC for MT5 tools to work.

The Telegram bot must have started a conversation with you (send /start once).

All components run locally for now. Docker + AWS come later (v2).

📅 Next Milestones
/digest command – fetch economic calendar + news → LLM summary → send to Telegram

Voice memo handling – download audio → Whisper → LLM extract trade psychology

PostgreSQL MCP server – store trades for analytics

Notion MCP server – mirror journal for readability

MT5 polling loop – detect new closed trades automatically

🏆 Resume Bullet Points (Current)
*"Built modular MCP servers for MT5 and Telegram, enabling an AI agent to fetch trading data and interact via voice/text – with stable long‑polling and file‑based state persistence."*

"Implemented direct tool invocation pattern to avoid LLM hallucinations in polling loops, ensuring deterministic message processing."

🛠️ Built With
Groq – Llama 3.3 70B, Whisper

LangChain + langchain-mcp-adapters

MCP (Model Context Protocol)

MetaTrader 5

Telegram Bot API

Python 3.13, httpx, python-dotenv