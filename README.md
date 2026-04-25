# Trading Buddy AI

An AI-powered trading assistant that journals trades via voice, provides on‑demand market digests, and answers analytics queries. Built with Groq LLM, LangChain, MCP (Model Context Protocol), MT5, PostgreSQL, Notion, & Telegram.

---

## 🚀 Current Status 

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
| On‑demand digest (`/digest`) with IST timezone | ✅ |
| Local voice transcription (faster-whisper) | ✅ |
| Psychology extraction (LLM) | 🔜 Next |
| PostgreSQL & Notion storage | ⏳ Planned |

**Next up (Day 5):**  
- Add psychology extraction from voice/text using Groq LLM.  
- State management for pending trade journaling.  
- (Optional) Simulate trade detection for testing.

---

## 🧠 Key Technical Decisions

- Telegram polling uses file‑based memory (`last_update_id.txt`) to avoid re‑processing old messages, even after server restarts.  
- **No LLM in the polling loop** – direct tool invocation prevents unwanted replies and infinite loops.  
- MCP servers run as subprocesses – clean separation of concerns.  
- Voice transcription runs **locally** with `faster-whisper` (no API calls, no `pydub`/`ffmpeg`).  
- Digest times are converted from UTC to IST using `pytz` and the Forex Factory API’s datetime field.

---

## 📌 Notes

- MT5 must be **open and logged in** on your Windows PC for MT5 tools to work.  
- The Telegram bot must have **started a conversation** with you (send `/start` once).  
- All components run **locally** for now. Docker + AWS come later (v2).

---

## 📅 Next Milestones

- [ ] Psychology extraction from voice/text  
- [ ] MT5 polling loop to auto‑detect closed trades  
- [ ] PostgreSQL MCP server (primary analytics DB)  
- [ ] Notion MCP server (readable mirror)  
- [ ] Docker + AWS deployment (v2)

---

## 🛠️ Built With

- [Groq](https://groq.com) – Llama 3.3 70B, Whisper  
- [faster-whisper](https://github.com/guillaumekln/faster-whisper) – local voice transcription  
- [LangChain](https://langchain.com) + `langchain-mcp-adapters`  
- [MCP (Model Context Protocol)](https://modelcontextprotocol.io)  
- [MetaTrader 5](https://www.metatrader5.com)  
- [Telegram Bot API](https://core.telegram.org/bots)  
- Python 3.13, `httpx`, `pytz`, `pydantic`
