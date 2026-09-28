# Sahakar Sahayak (सहकार सहायक) 🇮🇳
### A multilingual, voice-enabled assistant for Indian cooperative societies and farmers

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React%2019%20%2B%20Vite-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![Sarvam AI](https://img.shields.io/badge/LLM-Sarvam%20AI-6C3BD1)](https://www.sarvam.ai)
[![Bhashini](https://img.shields.io/badge/Voice-Bhashini%20DPI-F97316)](https://bhashini.gov.in)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://python.org)

**Sahakar Sahayak** answers questions about **cooperative societies** (registration, bye-laws, audits, elections, PACS schemes) and **farmer welfare schemes** (PM-KISAN, PMFBY crop insurance, Kisan Credit Card, PMKSY irrigation) in **English, Hindi, Kannada and Nepali** — typed or spoken, even in mixed language like *"PM Kisan yojane alli varshakke eshtu duddu sigutte?"*.

Every answer tells the user **where it came from**: an official government PDF (with a clickable link to the exact page) or general guidance that should be confirmed with the cooperative office.

- 🌐 **Live app:** https://sahakar-sahayak-frontend.onrender.com
- 📊 **Accuracy test results:** https://sahakar-sahayak-4.onrender.com/scoreboard
- ⚙️ **API docs (Swagger):** https://sahakar-sahayak-4.onrender.com/docs

> Hosted on free servers — if the app has been idle, the first answer can take up to a minute while the server wakes up.

### 🏆 Results at a glance
- **Our document search more than doubles accuracy:** Sarvam answers **30.56%** correctly on its own and **72.78%** with Sahakar Sahayak's search.
- **Tested fairly:** 45 hard questions in 4 languages; three AIs from three companies (Sarvam, Groq, Cloudflare) grade **each other's** answers, never their own.
- **100%** of off-topic and trick questions refused · correct official PDF found for **86%** of questions · answers in about **1 second**.

### 🧭 Try it in 2 minutes
1. Open the live app → **Continue as Guest** → **Ask Sahayak**.
2. Ask in mixed language: *"PM Kisan yojane alli varshakke eshtu duddu sigutte?"* → a 🟢 **Verified** answer with a link to the exact PDF page.
3. Switch the language to **Hindi** and ask *"fasal bima claim kitne din me milta hai?"* → the answer comes in Hindi.
4. Ask *"Who won the IPL?"* → politely refused.
5. Ask something the PDFs only partly cover → a ☎️ **helpline** box appears so the farmer can talk to a person.
6. A few seconds after each answer, a line shows **⚖️ AI check: Good · 84/100** — other AIs graded it. Tap **Scorecard** to see their grades and reasons, the search scores, which AI answered and the request ID.
7. Ask *"Kolar mandi mein tamatar ka bhav?"* → the latest official mandi price, a small price table and a dated label (e.g. *📈 Official mandi prices (AGMARKNET) · 25 Sep, 3 days old*). Ask *"PM Kisan ka rate kitna hai?"* → no prices at all (it's a scheme question).
8. On the login page, tap **Forgot password?** → enter your email or mobile → get a 6-digit code → set a new password.
9. In the left menu (or the page footer), open **📊 Accuracy results** to see the full 45-question test: every question, every answer and every grade.

---

## ✨ What it does

| Feature | How it works |
|---|---|
| 🗣️ **Ask in your language** | Type or speak in English, Hindi, Kannada or Nepali — including mixed language, local dialect and spelling mistakes. Sarvam AI rewrites the question into clear English for searching, and answers back in the user's chosen language. |
| 🔎 **Finds the answer in official documents** | 11 official government PDFs are split into ~2,650 short passages. Each question is matched three ways: the **same words** (BM25), **similar spelling** (so *kisan ≈ kishan*) and the **same meaning** even with different words (Cloudflare `bge-m3`). If a question names a scheme or law (PM-KISAN, KCC, PMKSY, Karnataka Act…), that scheme's own PDF is preferred. |
| ✅ **Trust card on every answer** | 🟢 *Verified from official document* · 🟡 *Partly verified* · 🔵 *General guidance* — plus the exact PDF and page, one tap to open it. Price answers get a dated 📈 *Official mandi prices* label instead, and if the AI check scores an answer below 50 the card turns into ⚠️ *AI check found problems · please verify with the source* — so a wrong answer never looks verified. |
| ⚖️ **Live AI check (per answer)** | Seconds after an answer appears, **other AIs grade it** — never the AI that wrote it (Sarvam's answers are checked by Groq and Cloudflare). They score how faithful it is to the official passages and how well it answers the question, and whether it is in the right language. The verdict shows under the answer and is saved for the admin. A score below 50 replaces the green *Verified* badge with an amber warning. |
| 🧾 **Scorecard (per answer)** | Tap to see the real numbers behind an answer: the AI check with each judge's reason, keyword %, spelling %, meaning %, final confidence, passages searched, search time, total time, which AI answered and the request ID. |
| 🚫 **Stays on topic** | Questions about cricket, movies, politics etc. are politely refused — in the user's language — and tricks like *"ignore your instructions"* are ignored. |
| 🧐 **Corrects wrong ideas** | If a question assumes something false (*"KCC is only for land owners, right?"*), the answer politely corrects it using the official rule. |
| 🛡️ **Answer safeguards** | If an answer comes back in the wrong language, it is translated into the user's language before it is shown. If the AI wrongly refuses a real farming question (e.g. crop disease), it gets a second chance. A question that mixes a real request with an off-topic one (*"tell me about PM-KISAN and write a cricket poem"*) gets the real answer; only the off-topic part is declined. Weather: it says honestly that it has no live forecasts and points to IMD. When a question names a scheme, the AI always sees passages from that scheme's own PDF. |
| 🛟 **Never goes silent** | Triple AI fallback: **Sarvam → Groq → Cloudflare**. If all three are down, **search-only mode** shows the exact passage from the official PDF. Every step is logged with a request ID. |
| 🌾 **Mandi prices (only when asked)** | Ask *"tomato bhav Kolar mandi?"* or *"ಈರುಳ್ಳಿ ಬೆಲೆ ಎಷ್ಟು?"* and the answer gives the latest Karnataka mandi prices (min / usual / max, ₹ per quintal, with the date) plus a small price table and the official AGMARKNET link. The prices are official AGMARKNET data (Govt. of India), read from a file that the open-source [karnataka-mandi-rates](https://github.com/Sheethal00/karnataka-mandi-rates) project refreshes every hour — so the farmer never waits for the slow government site, and no API key is needed. Prices appear **only** for price questions: PM-Kisan, KCC, MSP, insurance or loan questions never get them, and every other question works exactly as before. Prices older than 7 days are not shown (only the AGMARKNET link). Every price answer is labelled with its date: 🟢 *today* / *yesterday*, or 🟠 *"25 Sep, 3 days old · prices may have changed"* — the app never calls old prices "today's". |
| ☎️ **Talk to a person** | Under answers that aren't fully verified (and under complaints), the app shows official helplines — Kisan Call Centre 1800-180-1551, crop-insurance helpline 14447, PM-KISAN helpdesk, the Registrar's office — tap to call. |
| 📈 **Admin insights** | A password-protected `/admin` page: every recent question with its **scorecard and AI-check score**, most asked questions, languages, schemes, which AI answered, and the **knowledge gaps** — questions the PDFs couldn't answer, i.e. which document to add next. Download everything as CSV. |
| 🔊 **Voice in, voice out** | Speak your question and hear the answer. Speech-to-text has its own 3-level fallback (**Sarvam → Bhashini → Google**), and read-aloud falls back from **Bhashini → Google** — so voice also never goes silent. (English, Hindi, Kannada; Nepali voice is planned.) |
| 📤 **Share the full answer** | One tap shares the question, full answer and source link to WhatsApp (or any app on a phone). |
| 🔐 **Secure sign-up** | Email **and** phone OTP verification, hashed OTPs, attempt limits, resend cooldown; the account is only created after both are verified. **Forgot password?** on the login page: enter your email or mobile, get a 6-digit code (email via Brevo, SMS via the gateway), then set a new password. |
| 🤖 **Telegram bot** | The same assistant on Telegram, with a language menu (Kannada / English / Hindi). |
| 👤 **Easy to use** | Guest mode (no sign-up needed), a **New chat** button, and you stay logged in when the page is refreshed. |
| 🗄️ **Nothing gets lost** | User accounts and the admin insights are stored in a free permanent database (Neon Postgres), so they survive server restarts. |
| 🏆 **Proven accuracy** | A public test page where three AIs grade each other on 45 hard questions — see [Accuracy benchmark](#-accuracy-benchmark-3-ais-grade-each-other). |

---

## 🧠 How an answer is produced

```mermaid
flowchart LR
    A["Farmer asks<br/>(text or voice, any mix of<br/>Kannada / Hindi / English)"] --> B["Speech-to-text<br/>Sarvam → Bhashini → Google"]
    A --> C
    B --> C["Sarvam AI rewrites it<br/>as one clear English question"]
    C --> D{"Hybrid search over<br/>~2,650 PDF passages"}
    D --> D1["Keyword match<br/>(BM25)"]
    D --> D2["Spelling-tolerant match<br/>(3-letter word parts)"]
    D --> D3["Meaning match<br/>(Cloudflare bge-m3)"]
    D1 & D2 & D3 --> E["Best 6 passages<br/>+ real scores"]
    C --> P{"Price question?<br/>(price / bhav / ಬೆಲೆ + a crop)"}
    P -- "yes (only then)" --> P1["Latest Karnataka mandi prices<br/>(AGMARKNET data via GitHub file)"]
    P1 --> F
    E --> F["Sarvam AI writes a short answer<br/>in the user's language<br/>(backups: Groq → Cloudflare → search-only)"]
    F --> G["Trust card + source link<br/>+ scorecard + share"]
    F --> J["Live AI check:<br/>other AIs grade the answer"]
    F --> H["Text-to-speech<br/>Bhashini → Google"]
```

**Scoring (per passage)**

| Signal | Meaning | Weight in final score |
|---|---|---|
| Keyword match | share of the question's important words found exactly | 35% |
| Spelling-tolerant match | share of the question's 3-letter word parts found | 15% |
| Meaning match | Cloudflare `bge-m3` similarity, scaled 0–100% | 50% |

A passage is only used if its keyword **or** meaning match is strong enough. If nothing qualifies, the answer is labelled *General guidance* and no source is shown — the app never pretends an answer came from a document when it didn't.

**Resilience — the triple fallback engine**

| Step | 1st choice | If it fails | If that fails | Last resort |
|---|---|---|---|---|
| Rewrite the question in English | Sarvam `sarvam-105b` | Groq `gpt-oss-120b` | Cloudflare Llama 3.3 70B | search with the original words |
| Write the answer | Sarvam | Groq | Cloudflare | **search-only mode**: the best PDF passage, word for word, with its source |
| Meaning search | Cloudflare `bge-m3` | — | — | keyword + spelling search |

An AI that fails (error, timeout, empty reply) is rested for 60 seconds so the next users don't wait for it. Every step is printed in the Render logs with the question's request ID, for example:

```
[REQ a3f9c2] [QUERY] 📩 new question | language=hi | 'fasal bima claim kitne din me'
[REQ a3f9c2] [LLM] ▶ sarvam (translate) model=sarvam-105b
[REQ a3f9c2] [LLM] ❌ sarvam failed translate after 0.41s: status_code: 429 ...  -> switching to groq
[REQ a3f9c2] [LLM] ✅ groq answered translate in 0.62s (61 chars, provider id=req_01k...)
[REQ a3f9c2] [SEARCH] 🔎 best 84.06% | keyword 66.67% | ... | doc1.pdf p.103 | 6 pieces | 150 ms
[REQ a3f9c2] [LLM] ⏭ skipping sarvam (answer): failed 1s ago, cooling down 60s -> groq
[REQ a3f9c2] [QUERY] 🏁 finished in 2.41s | translated by groq | answered by groq | trust=verified
```

The chat shows which AI answered (a small note appears when a backup was used), and the scorecard shows the request ID.

---

## 📊 Accuracy benchmark: 3 AIs grade each other

`benchmark_questions.json` holds **45 questions** in 7 groups, picked from a bank of 200 (`benchmark_questions_all.json`). Every document question has its PDF, page and an **exact quote from that page** (machine-checked), so anyone can verify the answer key. The app was never tuned on these questions.

| Group | Questions | What it tests |
|---|---|---|
| Facts from the PDFs | 14 | one fact, asked in farmer-style words (not the PDF's wording) |
| Several cases | 4 | e.g. premium for kharif vs rabi vs cash crops — every case must be given |
| Hindi / Kannada / Nepali / Hinglish / typos | 10 | real multilingual understanding |
| Reply in the chosen language | 3 | English question, answer must come in Hindi / Kannada / Nepali |
| Wrong assumption | 5 | *"KCC is only for land owners, right?"* — the app must correct it |
| On-topic, not in the PDFs | 4 | honest general guidance, no invented rules |
| Off-topic & tricks | 5 | cricket, recipes, *"ignore all previous instructions"* — must refuse |

**Results (28 Sep 2026, 45 questions, every answer graded by two rival AIs):**

| Contestant | Score | Fully correct |
|---|---|---|
| **Sarvam + our documents (the live app)** | **72.78%** | 60.00% |
| Groq gpt-oss-120b + our documents | 72.22% | 66.67% |
| Cloudflare Llama 3.3 70B + our documents | 62.22% | 51.11% |
| Sarvam alone (no documents) | 30.56% | — |

- **Our document search more than doubles accuracy:** Sarvam goes from ~31% to ~73%, and every AI we tested improves the same way.
- The two judges agree on **82.71%** of the answers they both graded.
- Off-topic questions and rule-breaking tricks refused: **100%**. Wrong assumptions corrected: **85%**. English questions answered in the chosen Hindi / Kannada / Nepali: **100%** (Sarvam + documents).
- Search: correct PDF found in the top 6 for **86.11%** of questions (ranked #1 for 77.78%).
- Weaker areas (next steps): Kannada and mixed-language questions (55% for Sarvam + documents vs 90% for Groq + documents), and answers with several cases (50%).

Full tables: [`benchmark_report.md`](benchmark_report.md) · every question, answer and grade: [accuracy test results page](https://sahakar-sahayak-4.onrender.com/scoreboard).

**Contestants.** Three AIs from three companies each answer every question **using our document search**: Sarvam (`sarvam-105b`), Groq (`gpt-oss-120b`) and Cloudflare (Llama 3.3 70B). A fourth contestant, **Sarvam alone** with the same instructions but no documents, shows what our search adds.

**Judges — nobody grades its own work.** Sarvam's answers are graded by Groq and Cloudflare, Groq's by Sarvam and Cloudflare, Cloudflare's by Sarvam and Groq (Sarvam-alone by Groq and Cloudflare). Judges see shuffled labels, so they don't know who wrote which answer. Grades: correct / partial / wrong against the answer key. Free automatic checks run too: key fact present, answer script matches the chosen language, off-topic refused, no wrong refusals, correct PDF shown, search rank.

**See it live:** **https://sahakar-sahayak-4.onrender.com/scoreboard** — every question, every answer and every grade. Visitors can only re-run the free search check, so nobody can spend the team's AI credits from that page. Latest numbers are also in [`benchmark_report.md`](benchmark_report.md).

Run it yourself (keys are read from a local `.env`, never committed):

```bash
python3 evaluate_rag.py --run      # 1) all contestants answer (~30-40 min)
python3 evaluate_rag.py --grade    # 2) the judges grade (~20-30 min)
python3 evaluate_rag.py --report   # rebuild the report from what is saved
python3 evaluate_rag.py            # free search-only check, no AI at all
```

Both steps save after every question and continue where they stopped. A budget guard keeps Groq and Cloudflare inside their free daily limits.

---

## 📚 Knowledge base (official documents)

Stored in `backend/data/documents/` and served at `/documents/<file>` so every source link opens the real PDF on the right page.

| Document | Topic |
|---|---|
| Karnataka Co-operative Societies Act, 1959 | State cooperative law |
| Multi-State Co-operative Societies (Amendment) Act, 2023 | Central cooperative law |
| Model Bye-laws for PACS (Ministry of Cooperation, 2023) | PACS membership, governance, audit |
| Ministry of Cooperation — Initiatives Booklet (2025) | PACS computerisation, Jan Aushadhi, CSCs, storage |
| RBI — Kisan Credit Card Directions for Rural Co-operative Banks (2026) | KCC limits, tenure, collateral |
| PMFBY Operational Guidelines 2023 | Crop insurance, claims, loss reporting |
| RWBCIS Revised Guidelines | Weather-based crop insurance |
| Unified Package Insurance Scheme (UPIS) | Farmer package insurance |
| PM-KISAN Revised Operational Guidelines | ₹6,000/year income support |
| PMKSY Operational Guidelines | Irrigation / Per Drop More Crop |
| New Schemes (summary) | Plain-language scheme summaries |

---

## 🏛️ Architecture

```mermaid
flowchart TD
    subgraph Client["Frontend — React 19 + Vite (Render static site)"]
        UI[Chat · Trust card · Scorecard · AI check · Share]
        Voice[Mic input / Read aloud]
        AuthUI[Sign-up with email + phone OTP]
    end

    subgraph Backend["Backend — FastAPI (Render web service)"]
        Q["/query"]
        V["/voice/transcribe · /voice/speak"]
        AU["/api/auth/*"]
        DOCS["/documents/* (PDFs)"]
        RET[Hybrid retriever<br/>BM25 + word parts + meaning]
        RAG[Answer service<br/>triple AI fallback]
    end

    subgraph External["External services"]
        SARVAM[Sarvam AI<br/>LLM + speech-to-text]
        GROQ[Groq<br/>backup LLM]
        CFL[Cloudflare Workers AI<br/>backup LLM]
        CF[Cloudflare Workers AI<br/>bge-m3 embeddings]
        BH[Bhashini DPI<br/>speech]
        GG[Google speech<br/>fallback]
        BREVO[Brevo email]
        SMS[SMS gateway app]
        DB[(Neon Postgres<br/>accounts + insights)]
    end

    UI --> Q --> RET --> CF
    Q --> RAG --> SARVAM
    RAG -.fallback.-> GROQ -.fallback.-> CFL
    Voice --> V --> SARVAM & BH & GG
    AuthUI --> AU --> DB
    AU --> BREVO & SMS
    UI --> DOCS
```

---

## 📡 API reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/query` | Ask a question. Body: `{"query": "...", "language": "en\|hi\|kn\|ne"}` |
| `POST` | `/voice/transcribe` | Audio file → text (Sarvam → Bhashini → Google) |
| `POST` | `/voice/speak` | Text → audio (Bhashini → Google) |
| `GET` | `/documents/{file}` | Opens an official PDF (add `#page=N`) |
| `GET` | `/health` | Health check (used by the uptime pinger) |
| `GET` | `/scoreboard` | Live accuracy scoreboard page (run tests from the browser) |
| `GET` | `/scoreboard.json` | Last scoreboard result as JSON |
| `POST` | `/judge` | Live AI check of one answer (body `{"request_id": "…"}`), called by the website after each answer |
| `GET` | `/insights?key=…` | Admin insights page (password = `INSIGHTS_KEY`) |
| `GET` | `/insights.json` · `/insights.csv` | Insights data / all logged questions (header `X-Insights-Key`) |
| `POST` | `/api/auth/register/initiate` | Start sign-up, sends email + phone OTP |
| `POST` | `/api/auth/register/verify-email` · `/verify-phone` | Verify each OTP |
| `POST` | `/api/auth/register/resend-otp` | Resend OTP (60 s cooldown) |
| `GET` | `/api/auth/register/status/{id}` | Verification progress |
| `POST` | `/api/auth/login` | Log in with email **or** phone + password |
| `GET` / `PUT` | `/api/auth/me` · `/api/auth/profile` | Profile (Bearer token) |
| `POST` | `/api/auth/password-reset/send-otp` · `/confirm` | Forgot password: send a code to the email / mobile, then set the new password |

**`/query` response (main fields)**

```json
{
  "answer": "Crop loss due to localized calamities must be reported within 72 hours ...",
  "language": "en",
  "trust_level": "verified",
  "answered_by": "sarvam",
  "helplines": [],
  "confidence": 0.8406,
  "sources": [{ "document": "doc1.pdf", "page": 103, "link": "https://.../documents/doc1.pdf#page=103", "score": 84.06 }],
  "search_report": {
    "final_confidence": 84.06, "keyword_score": 66.67, "spelling_score": 82.5, "meaning_score": 61.23,
    "pieces_searched": 2655, "pdfs_searched": 11, "candidates_compared": 36,
    "search_time_ms": 13.81, "total_time_ms": 3421.5, "top_sources": ["..."],
    "request_id": "a3f9c2", "translated_by": "sarvam", "answered_by": "sarvam"
  }
}
```

---

## ⚙️ Environment variables

Set these in Render → Environment (never commit real values). See `.env.example`.

| Variable | Used for |
|---|---|
| `SARVAM_API_KEY` | Sarvam AI (question rewriting, answers, speech-to-text) |
| `GROQ_API_KEY` | 1st backup AI (free key from console.groq.com) · optional `GROQ_MODEL` |
| `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN` | Meaning search + 2nd backup AI · optional `CLOUDFLARE_LLM_MODEL` |
| `INSIGHTS_KEY` | Password for the admin insights page (`/admin`) |
| `LIVE_JUDGE`, `LIVE_JUDGE_GROQ_DAILY`, `LIVE_JUDGE_CLOUDFLARE_DAILY`, `GROQ_JUDGE_MODEL` | Optional: live AI check on/off (default on) and its daily limits (120 Groq / 80 Cloudflare checks), so the backups' free quota is never used up |
| `LLM_ORDER`, `LLM_TIMEOUT`, `LLM_COOLDOWN` | Optional: AI order (default `sarvam,groq,cloudflare`), seconds per call (30), rest after a failure (60) |
| `BHASHINI_USER_ID`, `BHASHINI_API_KEY` | Bhashini speech |
| `JWT_SECRET` | Login tokens |
| `EMAIL_API_KEY`, `SENDER_EMAIL` | Email OTP (Brevo) |
| `GATEWAY_API_KEY` | Phone OTP (SMS gateway app) |
| `DATABASE_URL` | Permanent database for user accounts and admin insights — a free [Neon](https://neon.com) Postgres connection string. Without it, a SQLite file is used, which Render's free plan wipes on every redeploy |
| `MANDI_PRICES_URL` | Optional: a different copy of the mandi price file (`live.json`). Default: the karnataka-mandi-rates GitHub file. No key needed |
| `PUBLIC_BACKEND_URL` | Public backend address used in PDF links |
| `TELEGRAM_BOT_TOKEN`, `API_URL` | Telegram bot |
| `VITE_API_URL` (frontend) | Backend address for the React app |

When email/SMS keys are missing (local development), OTPs are printed to the backend console instead.

---

## 🚀 Run locally

```bash
# Backend
pip install -r requirements.txt
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
#   → http://127.0.0.1:8000/docs

# Frontend (second terminal)
npm install
npm run dev
#   → http://localhost:5173

# Telegram bot (optional, third terminal)
python backend/telegram_bot.py
```

The search index (`backend/data/chunks_cache.json`) is rebuilt automatically whenever PDFs are added or removed.

---

## 🧪 Tests

```bash
python3 backend/test_auth.py     # 16 sign-up / OTP / login security tests
python3 test_search.py           # quick look at search scores for sample questions
python3 evaluate_rag.py          # free search check (full benchmark: see above)
npm run build                    # frontend build check
```

**Stress tests (live app, 28 Sep 2026):** 10 tricky questions in 3 languages — price questions, look-alike traps (*"PM Kisan ka rate"*, *"PMFBY premium rate"*, MSP), a wrong premise, a Karnataka Act question and a prompt-injection. The price box appeared **only** for the 4 price questions and never for the 6 others; average AI-check score **88/100**. The one wrong answer (a reversed proviso in the Karnataka Act) was caught by the live AI check at **28/100** — which is why low scores now switch the badge to a warning.

---

## 📁 Project structure

```
backend/
  main.py                  FastAPI app, voice endpoints, PDF serving
  routes/query.py          /query pipeline
  routes/auth.py           sign-up, OTP, login, forgot password
  routes/scoreboard.py     live /scoreboard page
  routes/insights.py       admin insights (/insights, /insights.json, /insights.csv)
  services/rag_service.py  question rewriting, answer, trust level, scorecard numbers, search-only mode
  services/live_judge.py   live AI check: other AIs grade every answer (free daily limits built in)
  services/llm_chain.py    triple AI fallback: Sarvam -> Groq -> Cloudflare, with logs
  services/reqlog.py       request IDs for the logs
  services/help_contacts.py official helplines ("talk to a person")
  services/mandi_prices.py latest Karnataka mandi prices, only for price questions
  services/analytics.py    question log for admin insights, saved in the database (phone numbers / emails removed)
  models/database.py       database connection (Neon Postgres, or SQLite locally)
  services/retriever.py    hybrid search (BM25 + word parts + Cloudflare meaning)
  services/nlp_service.py  cleaning, language check, intent
  services/auth_service.py passwords, OTPs, JWT, email/SMS dispatch
  data/documents/          official PDFs
  telegram_bot.py          Telegram bot
anadi_voice_engine.py      speech-to-text / text-to-speech with fallbacks
src/
  pages/Chat.jsx           chat screen
  pages/Admin.jsx          admin insights (/admin)
  pages/Login.jsx          login + forgot password
  components/chat/AnswerFooter.jsx  trust card, AI check, mandi price table, helplines, share, scorecard
evaluate_rag.py            benchmark: 3 AIs answer, the other AIs judge
benchmark_questions.json   the 45 test questions with answer keys and PDF quotes
benchmark_questions_all.json  bank of 200 questions
test_search.py             search smoke test
```

---

## 🛣️ Limitations & next steps

- Knowledge base covers Karnataka + central cooperative law; other states' Acts can be added by dropping PDFs into `backend/data/documents/`.
- Scanned (image-only) PDFs can't be read yet — OCR is a planned addition.
- Planned: state selection for state-specific rules and more states' Acts.
- Each question is answered on its own: a follow-up like *"and what documents for that?"* doesn't remember the previous question yet (conversation memory is planned).
- Schemes whose official PDF isn't in the knowledge base (e.g. PM Kisan **Maandhan** pension) get 🔵 general guidance, and similar-sounding names can pull passages from the wrong PDF. Adding that scheme's PDF fixes it.
- Mandi prices cover **Karnataka markets only**, and are only as fresh as the government's AGMARKNET feed (the date is always shown). Other states: the answer links to AGMARKNET.
- A 🟢 *Verified* badge means the search found the right official passage; it does not prove the AI read it correctly. The live AI check is the second safeguard (below 50 → warning badge). Legal provisos ("shall not … where there is no …") are the hardest case.
- Calculations (e.g. working out a KCC limit from the scale of finance) are done by the AI and are less reliable than looking up a fact.
- The page-level search is the weakest link: the right PDF is usually found, but not always the exact page.

---

## 🙏 Acknowledgements

Built for the **Smart India Hackathon (SIH)**. Uses India's **Bhashini** language platform and **Sarvam AI**. Official documents from the Ministry of Cooperation, Ministry of Agriculture & Farmers Welfare, the Reserve Bank of India, and the Government of Karnataka.
