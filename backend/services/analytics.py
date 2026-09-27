"""
Question log for the admin Insights page (/insights).

Every question asked through /query is saved to a small SQLite file
(backend/data/analytics.db -- *.db is in .gitignore, so it never goes to GitHub).

Privacy: phone numbers, Aadhaar-like numbers and e-mail addresses are removed
from the text before it is stored.

Note: on Render's free plan the disk is temporary, so the log starts empty again
after a redeploy. That is fine for a pilot/demo; a real deployment would point
this at a permanent database.
"""

import os
import re
import sqlite3
import threading
import time
from collections import Counter

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "analytics.db")
_lock = threading.Lock()

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_LONG_NUMBER = re.compile(r"(?<!\d)(?:\+?\d[\d\s-]{8,}\d)(?!\d)")   # phone / Aadhaar / account-like numbers


def _mask(text: str) -> str:
    text = _EMAIL.sub("[email]", text or "")
    return _LONG_NUMBER.sub("[number]", text)[:500]


def _connect():
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.execute("""CREATE TABLE IF NOT EXISTS queries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts REAL, language TEXT, question TEXT, english_question TEXT,
        intent TEXT, trust_level TEXT, answer_source TEXT, top_document TEXT,
        confidence REAL, response_ms REAL, topics TEXT)""")
    cols = {r[1] for r in conn.execute("PRAGMA table_info(queries)")}
    if "answered_by" not in cols:          # added later -- upgrade old files
        conn.execute("ALTER TABLE queries ADD COLUMN answered_by TEXT")
    return conn


def log_query(question, english_question, language, intent, trust_level, answer_source,
              top_document, confidence, response_ms, topics, answered_by=None):
    """Save one question. Never raises -- logging must not break answering."""
    try:
        with _lock:
            conn = _connect()
            conn.execute(
                "INSERT INTO queries (ts, language, question, english_question, intent, trust_level, "
                "answer_source, top_document, confidence, response_ms, topics, answered_by) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (time.time(), language, _mask(question), _mask(english_question), intent, trust_level,
                 answer_source, top_document, float(confidence or 0), float(response_ms or 0),
                 ",".join(topics or []), answered_by))
            conn.commit()
            conn.close()
    except Exception as e:
        print(f"[ANALYTICS] could not log question: {e}")


def all_rows(limit: int = 5000) -> list:
    try:
        with _lock:
            conn = _connect()
            conn.row_factory = sqlite3.Row
            rows = [dict(r) for r in conn.execute("SELECT * FROM queries ORDER BY ts DESC LIMIT ?", (limit,))]
            conn.close()
        return rows
    except Exception:
        return []


def summary() -> dict:
    rows = all_rows()
    total = len(rows)
    now = time.time()
    day = 86400

    def share(pred):
        return round(100.0 * sum(1 for r in rows if pred(r)) / total, 2) if total else 0.0

    in_scope = [r for r in rows if r["trust_level"] not in ("refused", "error")]
    times = [r["response_ms"] for r in rows if r["response_ms"]]

    # most asked: group by the clean English question (falls back to the original)
    def key(r):
        q = (r["english_question"] or r["question"] or "").lower()
        return re.sub(r"[^\w\s]", "", q).strip()[:160]
    counts = Counter(key(r) for r in in_scope if key(r))
    example = {}
    for r in in_scope:
        example.setdefault(key(r), r)
    most_asked = [{"question": example[k]["english_question"] or example[k]["question"], "count": n,
                   "trust_level": example[k]["trust_level"]} for k, n in counts.most_common(15)]

    gaps = [{"question": r["english_question"] or r["question"], "language": r["language"],
             "trust_level": r["trust_level"], "ts": r["ts"]}
            for r in in_scope if r["trust_level"] in ("general", "partial")][:25]

    per_day = []
    for d in range(13, -1, -1):
        start = now - (d + 1) * day
        end = now - d * day
        per_day.append({"days_ago": d, "count": sum(1 for r in rows if start <= r["ts"] < end)})

    topics = Counter()
    for r in rows:
        for t in (r["topics"] or "").split(","):
            if t:
                topics[t] += 1

    return {
        "total": total,
        "last_7_days": sum(1 for r in rows if r["ts"] >= now - 7 * day),
        "from_documents_pct": share(lambda r: r["answer_source"] == "documents"),
        "verified_pct": share(lambda r: r["trust_level"] == "verified"),
        "general_pct": share(lambda r: r["trust_level"] == "general"),
        "refused_pct": share(lambda r: r["trust_level"] == "refused"),
        "avg_response_s": round(sum(times) / len(times) / 1000, 2) if times else 0.0,
        "languages": Counter(r["language"] for r in rows).most_common(),
        "intents": Counter(r["intent"] for r in rows).most_common(8),
        "answered_by": Counter(r.get("answered_by") or "unknown" for r in rows).most_common(),
        "topics": topics.most_common(10),
        "most_asked": most_asked,
        "gaps": gaps,
        "per_day": per_day,
        "since": min((r["ts"] for r in rows), default=None),
    }
