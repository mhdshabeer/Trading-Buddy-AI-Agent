# Trading Buddy AI

An AI-powered trading assistant that journals trades via voice, provides on-demand market digests, and answers analytics queries. Built with Groq LLM, LangChain, MCP (Model Context Protocol), MT5, PostgreSQL, Notion, and Telegram.

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
| File-based memory for Telegram | ✅ |
| Polling client (no LLM, stable) | ✅ |

Next up (Day 3):
- Add /digest command handler (economic calendar + news → LLM summary)
- Voice memo handling (download audio → Whisper transcription)

---

## 🧠 Key Technical Decisions

- Telegram polling uses file-based memory (last_update_id.txt) to avoid re-processing old messages.
- No LLM in the polling loop – direct tool invocation prevents unwanted replies and infinite loops.
- MCP servers run as subprocesses – clean separation of concerns.

---

## 📌 Notes

- MT5 must be open and logged in on your Windows PC for MT5 tools to work.
- The Telegram bot must have started a conversation with you (send /start once).
- All components run locally for now. Docker + AWS come later (v2).

---

## 📅 Next Milestones

- /digest command – fetch economic calendar + news → LLM summary → send to Telegram
- Voice memo handling – download audio → Whisper → LLM extract trade psychology
- PostgreSQL MCP server – store trades for analytics
- Notion MCP server – mirror journal for readability
- MT5 polling loop – detect new closed trades automatically

---

## 🛠️ Built With

- Groq – Llama 3.3 70B, Whisper
- LangChain + langchain-mcp-adapters
- MCP (Model Context Protocol)
- MetaTrader 5
- Telegram Bot API
- Python 3.13, httpx, python-dotenv
