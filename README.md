# 🚀 Trading Buddy AI

An AI-powered trading assistant that automatically journals trades using voice/text, extracts trading psychology with LLMs, and stores everything in a structured database for analysis.

Built with a modular **MCP (Model Context Protocol)** architecture, enabling real-time interaction between trading platforms, messaging interfaces, and AI systems.

---

## ✨ Key Features

### 📊 Automated Trade Journaling
- Detects closed trades from MetaTrader 5 (MT5) in real time  
- Prompts user on Telegram for psychology (voice or text)  
- Extracts structured insights using an LLM  
- Stores everything in PostgreSQL  

---

### 🎙️ Voice-Based Journaling (Local)
- Accepts Telegram voice messages  
- Transcribes locally using faster-whisper (no API calls)  
- Low latency and privacy-friendly  

---

### 🤖 AI-Powered Psychology Extraction
- Uses Groq LLM (LLaMA 3)  
- Extracts:
  - HTF bias  
  - Trade logic  
  - Confluences  
  - Psychology during & after  
  - Mistakes & learnings  

---

### ⚡ Real-Time System Design
- MT5 polling every 5 seconds  
- Queue-based processing (no overlapping trades)  
- `/skip` command to ignore trades  
- Persistent tracking to avoid duplicate journaling  

---

### 📰 On-Demand Market Digest
- `/news` or `/digest` command on Telegram  
- Fetches:
  - Economic calendar (Forex Factory)  
  - Forex news (Finnhub API)  
- Summarised into actionable insights via LLM  

---

## 🧠 Architecture (MCP-Based)

This project uses **Model Context Protocol (MCP)** to build a modular, production-style system.

### 🔌 MCP Servers

Each integration runs as an independent server:

- **MT5 MCP Server**
  - Fetch account balance, trades, positions  

- **Telegram MCP Server**
  - Send messages  
  - Poll updates  
  - Handle voice + text  

- **PostgreSQL MCP Server**
  - Insert structured trade data  

---

### ⚙️ Orchestrator

- Connects to all MCP servers using `MultiServerMCPClient`  
- Handles:
  - MT5 polling  
  - Telegram polling  
  - Trade queue  
  - LLM pipeline  

---

### 🔄 Why MCP?

- Modular design (each component independent)  
- Reusable integrations  
- Clean separation of concerns  
- Closer to real-world AI agent systems  

---

## 🛠️ Tech Stack

| Technology | Purpose |
|----------|--------|
| Python 3.13 | Core language |
| Groq LLM | Psychology extraction & summarisation |
| faster-whisper | Local voice transcription |
| MetaTrader 5 | Trading data source |
| PostgreSQL | Structured storage |
| MCP (SDK) | Modular tool-based architecture |
| LangChain | Agent + MCP client integration |
| Telegram Bot API | User interaction |
| asyncpg | Async DB operations |
| httpx | API calls |
| pytz | Timezone handling |

---

## 📂 Project Structure

```
trading-buddy-ai/
├── src/
│   └── mcp_servers/
│       ├── mt5_mcp.py
│       ├── telegram_mcp.py
│       └── postgresql_mcp.py
├── scripts/
│   └── test_telegram_polling.py   # Main orchestrator
├── processed_tickets.json        # Persistence
├── .env                          # Credentials
└── requirements.txt
```

---

## 🔄 System Flow

1. MT5 detects a closed trade  
2. Trade added to queue  
3. Telegram prompts user  
4. User responds (voice/text)  
5. Voice → transcribed locally  
6. LLM extracts structured fields  
7. Data merged with MT5 trade  
8. Stored in PostgreSQL  

---

## 🐛 Challenges & Learnings

- MT5 emits multiple deal events → filtered closing trades  
- Restart caused duplicate journaling → fixed with persistent ticket tracking  
- Schema mismatch (`buy/sell` vs `long/short`) → added mapping layer  
- LLM returning empty fields → sanitization layer  
- Telegram polling replay issues → persisted `last_update_id`  

---

## 🔜 Roadmap

- 📄 Notion integration (auto journal pages + charts)  
- 📊 Analytics queries (behavior vs performance)  
- 🐳 Docker containerization  
- ☁️ AWS deployment (EC2 + EventBridge)  
- 🌐 Optional web dashboard (Streamlit)  

---

## 🎯 Why This Project?

Most traders don’t journal consistently due to friction.

This system removes that friction completely by:
- Automating data capture  
- Using AI to extract insights  
- Structuring everything for analysis  

---

## 📌 Example Use Case

> Close trade → speak thoughts → everything is stored automatically  

No manual logging required.

---

## 📬 Contact / Opportunities

I’m currently exploring **AI / ML internship opportunities** and open to collaborating on real-world AI systems.

---

## ⭐ If you like this project

Give it a star ⭐ and feel free to reach out!
