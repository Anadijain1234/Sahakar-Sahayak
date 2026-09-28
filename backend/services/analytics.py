"""
Question log for the admin Insights page (/admin in the website, /insights on the backend).

Every question asked through /query is saved as one row in the app's database
(the same one as user accounts -- see backend/models/database.py):
  - DATABASE_URL set (free Neon Postgres) -> permanent, survives redeploys
  - not set -> a SQLite file, which Render's free plan wipes on every redeploy

Privacy: phone numbers, Aadhaar-like numbers and e-mail addresses are removed
from the text before it is stored. Answers and names are never stored.
"""

import re
import json
import threading
import time
from collections import Counter

from sqlalchemy import text

from backend.models.database import engine, IS_PERMANENT

TABLE = "insights_log"
_lock = threading.Lock()
_ready = False

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_LONG_NUMBER = re.compile(r"(?<!\d)(?:\+?\d[\d\s-]{8,}\d)(?!\d)")   # phone / Aadhaar / account-like numbers

_COLUMNS = ["ts", "language", "question", "english_question", "intent", "trust_level", "answer_source",
            "top_document", "confidence", "response_ms", "topics", "answered_by",
            # the answer's scorecard (same numbers the user sees under "Search report")
            "request_id", "translated_by", "top_page", "final_score", "keyword_score", "spelling_score",
            "meaning_score", "search_ms", "pieces_used",
            # the live AI check (other AIs grading the answer) -- filled in a few seconds later
            "judges", "judge_score"]
_NUMERIC = {"ts", "confidence", "response_ms", "top_page", "final_score", "keyword_score", "spelling_score",
            "meaning_score", "search_ms", "pieces_used", "judge_score"}
_ADDED_LATER = ["request_id", "translated_by", "top_page", "final_score", "keyword_score", "spelling_score",
                "meaning_score", "search_ms", "pieces_used", "judges", "judge_score"]


def _mask(value: str) -> str:
    value = _EMAIL.sub("[email]", value or "")
    return _LONG_NUMBER.sub("[number]", value)[:500]


def _ensure_table():
    """Create the table once (works for both SQLite and Postgres)."""
    global _ready
    if _ready:
        return
    pg = engine.dialect.name == "postgresql"
    id_col = "id SERIAL PRIMARY KEY" if pg else "id INTEGER PRIMARY KEY AUTOINCREMENT"
    num = "DOUBLE PRECISION" if pg else "REAL"
    cols = ", ".join(f"{c} {num if c in _NUMERIC else 'TEXT'}" for c in _COLUMNS)
    with engine.begin() as conn:
        conn.execute(text(f"CREATE TABLE IF NOT EXISTS {TABLE} ({id_col}, {cols})"))
    # Tables made by an older version lack the scorecard columns: add them.
    for c in _ADDED_LATER:
        kind = num if c in _NUMERIC else "TEXT"
        try:
            with engine.begin() as conn:
                if pg:
                    conn.execute(text(f"ALTER TABLE {TABLE} ADD COLUMN IF NOT EXISTS {c} {kind}"))
                else:
                    conn.execute(text(f"ALTER TABLE {TABLE} ADD COLUMN {c} {kind}"))
        except Exception:
            pass        # SQLite: column already exists
    _ready = True


def _num(x):
    try:
        return None if x is None else float(x)
    except (TypeError, ValueError):
        return None


def log_query(question, english_question, language, intent, trust_level, answer_source,
              top_document, confidence, response_ms, topics, answered_by=None, report=None, top_page=None):
    """Save one question. Never raises -- logging must not break answering."""
    try:
        with _lock:
            _ensure_table()
            row = {"ts": time.time(), "language": language, "question": _mask(question),
                   "english_question": _mask(english_question), "intent": intent, "trust_level": trust_level,
                   "answer_source": answer_source, "top_document": top_document,
                   "confidence": float(confidence or 0), "response_ms": float(response_ms or 0),
                   "topics": ",".join(topics or []), "answered_by": answered_by}
            r = report or {}
            row.update({"request_id": r.get("request_id"), "translated_by": r.get("translated_by"),
                        "top_page": _num(top_page), "final_score": _num(r.get("final_confidence")),
                        "keyword_score": _num(r.get("keyword_score")), "spelling_score": _num(r.get("spelling_score")),
                        "meaning_score": _num(r.get("meaning_score")), "search_ms": _num(r.get("search_time_ms")),
                        "pieces_used": _num(r.get("pieces_used")),
                        "judges": None, "judge_score": None})      # filled in later by save_judgement()
            with engine.begin() as conn:
                conn.execute(text(f"INSERT INTO {TABLE} ({', '.join(_COLUMNS)}) "
                                  f"VALUES ({', '.join(':' + c for c in _COLUMNS)})"), row)
    except Exception as e:
        print(f"[ANALYTICS] could not log question: {e}")


def save_judgement(request_id, judges, score):
    """Add the live AI check to the question's row (it runs a few seconds after the answer)."""
    try:
        compact = [{k: j.get(k) for k in ("judge", "grade", "faithful", "helpful", "language_ok", "reason", "status")}
                   for j in judges]
        with _lock:
            _ensure_table()
            with engine.begin() as conn:
                conn.execute(text(f"UPDATE {TABLE} SET judges = :j, judge_score = :s "
                                  f"WHERE request_id = :rid AND ts > :since"),
                             {"j": json.dumps(compact, ensure_ascii=False), "s": float(score) if score is not None else None,
                              "rid": request_id, "since": time.time() - 7200})
    except Exception as e:
        print(f"[ANALYTICS] could not save the AI check: {e}")


def all_rows(limit: int = 5000) -> list:
    try:
        with _lock:
            _ensure_table()
            with engine.connect() as conn:
                result = conn.execute(text(f"SELECT * FROM {TABLE} ORDER BY ts DESC LIMIT :n"), {"n": int(limit)})
                return [dict(r) for r in result.mappings()]
    except Exception as e:
        print(f"[ANALYTICS] could not read the log: {e}")
        return []


def _loads(x):
    try:
        return json.loads(x) if x else None
    except Exception:
        return None


def summary() -> dict:
    rows = all_rows()
    judged = [float(r["judge_score"]) for r in rows if r.get("judge_score") is not None]
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
        "recent": [{**{k: r.get(k) for k in ("ts", "question", "english_question", "language", "trust_level",
                                              "answered_by", "top_document", "top_page", "final_score", "keyword_score",
                                              "spelling_score", "meaning_score", "response_ms", "request_id",
                                              "judge_score")},
                    "judges": _loads(r.get("judges"))}
                   for r in rows[:30]],
        "judged": len(judged),
        "avg_judge_score": round(sum(judged) / len(judged), 2) if judged else None,
        "per_day": per_day,
        "since": min((r["ts"] for r in rows), default=None),
        "permanent": IS_PERMANENT,
    }
