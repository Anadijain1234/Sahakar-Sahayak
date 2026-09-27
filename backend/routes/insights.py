"""
Admin Insights page -- what farmers are asking.

  GET /insights?key=YOUR_KEY       -> dashboard page
  GET /insights.csv?key=YOUR_KEY   -> download all logged questions (CSV)
  GET /insights.json               -> the same numbers as JSON, for the website's /admin page
                                      (password in the X-Insights-Key header)

Protected by the INSIGHTS_KEY environment variable (set it in Render ->
Environment). Without the right key nothing is shown, because the page
contains what users asked.
"""

import os
import io
import csv
import html
import hmac
import datetime

from fastapi import APIRouter, Header
from fastapi.responses import HTMLResponse, Response, JSONResponse

from backend.services import analytics

router = APIRouter()

LANG_NAMES = {"en": "English", "hi": "Hindi", "kn": "Kannada", "ne": "Nepali", "ta": "Tamil", "te": "Telugu", "ml": "Malayalam"}
AI_NAMES = {"sarvam": "Sarvam AI", "groq": "Groq (backup)", "cloudflare": "Cloudflare (backup)",
            "search_only": "Search only (no AI)", "unknown": "Not recorded"}
TRUST_NAMES = {"verified": "🟢 Verified", "partial": "🟡 Partly verified", "general": "🔵 General guidance",
               "refused": "Refused (off-topic)", "error": "Error"}


def _authorised(key: str) -> bool:
    expected = os.getenv("INSIGHTS_KEY", "").strip()
    return bool(expected) and hmac.compare_digest((key or "").strip(), expected)


def _e(x):
    return html.escape(str(x)) if x is not None else "—"


def _bars(pairs, names=None):
    if not pairs:
        return '<p class="muted">No data yet.</p>'
    top = max(n for _, n in pairs) or 1
    rows = []
    for k, n in pairs:
        label = (names or {}).get(k, k or "—")
        rows.append(f'<div class="bar"><span class="bl">{_e(label)}</span>'
                    f'<span class="bt"><span style="width:{100 * n / top:.1f}%"></span></span>'
                    f'<span class="bn">{n}</span></div>')
    return "".join(rows)


def _page(body: str) -> str:
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Sahakar Sahayak · Insights</title>
<style>
:root{{--bg:#f7f8f6;--card:#fff;--ink:#16211b;--muted:#5f6b64;--line:#e3e7e4;--brand:#15803d;--bar:#86c99c}}
@media (prefers-color-scheme:dark){{:root{{--bg:#0e1411;--card:#151d18;--ink:#e6ede8;--muted:#9aa8a0;--line:#26312b;--brand:#4ade80;--bar:#2f6b45}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}}
main{{max-width:1100px;margin:0 auto;padding:24px 16px 48px}}h1{{font-size:22px;margin:0 0 4px}}h2{{font-size:16px;margin:0 0 10px}}
.muted{{color:var(--muted)}}.small{{font-size:12px}}
.cards{{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:10px;margin:18px 0}}
.card,.panel{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px}}
.card .v{{font-size:22px;font-weight:700;font-family:ui-monospace,Menlo,Consolas,monospace}}.card .k{{font-size:12px;color:var(--muted)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px;margin-top:12px}}
.bar{{display:grid;grid-template-columns:130px 1fr 40px;gap:8px;align-items:center;font-size:13px;margin:5px 0}}
.bl{{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}.bn{{text-align:right;font-family:ui-monospace,Menlo,Consolas,monospace}}
.bt{{background:var(--line);border-radius:6px;height:10px;overflow:hidden}}.bt span{{display:block;height:100%;background:var(--bar)}}
.days{{display:flex;align-items:flex-end;gap:4px;height:90px}}.days div{{flex:1;background:var(--bar);border-radius:4px 4px 0 0;min-height:2px}}
table{{border-collapse:collapse;width:100%;font-size:13px}}th,td{{padding:7px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}}
th{{font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}}
a{{color:var(--brand)}}
</style></head><body><main>{body}</main></body></html>'''


@router.get("/insights", response_class=HTMLResponse, include_in_schema=False)
def insights_page(key: str = ""):
    if not os.getenv("INSIGHTS_KEY", "").strip():
        return HTMLResponse(_page('<h1>Insights</h1><p class="muted">Not set up yet: add <b>INSIGHTS_KEY</b> '
                                  '(any password you choose) in Render → Environment, then open '
                                  '<code>/insights?key=YOUR_PASSWORD</code>.</p>'))
    if not _authorised(key):
        return HTMLResponse(_page('<h1>Insights</h1><p class="muted">Wrong or missing key. Open '
                                  '<code>/insights?key=YOUR_PASSWORD</code>.</p>'), status_code=401)

    s = analytics.summary()
    since = datetime.datetime.fromtimestamp(s["since"]).strftime("%d %b %Y, %H:%M") if s["since"] else "—"
    cards = [
        ("Questions asked", s["total"]),
        ("In the last 7 days", s["last_7_days"]),
        ("Answered from official documents", f'{s["from_documents_pct"]:.2f}%'),
        ("🟢 Verified answers", f'{s["verified_pct"]:.2f}%'),
        ("🔵 General guidance", f'{s["general_pct"]:.2f}%'),
        ("Off-topic refused", f'{s["refused_pct"]:.2f}%'),
        ("Avg response time", f'{s["avg_response_s"]:.2f} s'),
    ]
    top_day = max((d["count"] for d in s["per_day"]), default=0) or 1
    days = "".join(f'<div title="{d["count"]} questions, {d["days_ago"]} days ago" '
                   f'style="height:{max(2, 90 * d["count"] / top_day):.0f}px"></div>' for d in s["per_day"])

    most = "".join(f'<tr><td>{_e(q["question"])}</td><td>{q["count"]}</td><td>{_e(TRUST_NAMES.get(q["trust_level"], q["trust_level"]))}</td></tr>'
                   for q in s["most_asked"]) or '<tr><td colspan="3" class="muted">No questions yet.</td></tr>'
    gaps = "".join(f'<tr><td>{_e(g["question"])}</td><td>{_e(LANG_NAMES.get(g["language"], g["language"]))}</td>'
                   f'<td>{_e(TRUST_NAMES.get(g["trust_level"], g["trust_level"]))}</td></tr>'
                   for g in s["gaps"]) or '<tr><td colspan="3" class="muted">None — every question was answered from the documents.</td></tr>'

    body = f'''
    <h1>📈 Sahakar Sahayak · Insights</h1>
    <div class="muted">What farmers and cooperative members are asking · logged since {since} ·
      <a href="/insights.csv?key={_e(key)}">download CSV</a></div>
    <section class="cards">{"".join(f'<div class="card"><div class="v">{v}</div><div class="k">{k}</div></div>' for k, v in cards)}</section>

    <div class="panel"><h2>Questions per day (last 14 days)</h2><div class="days">{days}</div>
      <div class="muted small" style="display:flex;justify-content:space-between"><span>14 days ago</span><span>today</span></div></div>

    <div class="grid">
      <div class="panel"><h2>Languages used</h2>{_bars(s["languages"], LANG_NAMES)}</div>
      <div class="panel"><h2>Schemes & laws asked about</h2>{_bars(s["topics"])}</div>
      <div class="panel"><h2>Type of question</h2>{_bars(s["intents"])}</div>
      <div class="panel"><h2>Which AI answered</h2>{_bars(s["answered_by"], AI_NAMES)}</div>
    </div>

    <div class="panel" style="margin-top:12px"><h2>Most asked questions</h2>
      <table><tr><th>Question</th><th>Times</th><th>Answer</th></tr>{most}</table></div>

    <div class="panel" style="margin-top:12px"><h2>⚠️ Knowledge gaps: not fully answered from official documents</h2>
      <p class="muted small">Add the missing official documents for these topics to backend/data/documents to improve answers.</p>
      <table><tr><th>Question</th><th>Language</th><th>Answer</th></tr>{gaps}</table></div>

    <p class="muted small" style="margin-top:16px">Phone numbers and e-mail addresses are removed from questions before they are stored.</p>'''
    return HTMLResponse(_page(body))


@router.get("/insights.json", include_in_schema=False)
def insights_json(key: str = "", x_insights_key: str = Header(default="")):
    """Data for the Admin page inside the website (/admin). Send the password in the
    X-Insights-Key header (or ?key=)."""
    if not os.getenv("INSIGHTS_KEY", "").strip():
        return JSONResponse({"error": "not_configured"}, status_code=503)
    if not _authorised(x_insights_key or key):
        return JSONResponse({"error": "wrong_key"}, status_code=401)
    return JSONResponse(analytics.summary())


@router.get("/insights.csv", include_in_schema=False)
def insights_csv(key: str = "", x_insights_key: str = Header(default="")):
    key = x_insights_key or key
    if not _authorised(key):
        return Response("Wrong or missing key.", status_code=401)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["time", "language", "question", "english_question", "intent", "trust_level",
                "answer_source", "top_document", "confidence", "response_ms", "topics", "answered_by"])
    for r in analytics.all_rows():
        w.writerow([datetime.datetime.fromtimestamp(r["ts"]).isoformat(timespec="seconds"), r["language"],
                    r["question"], r["english_question"], r["intent"], r["trust_level"], r["answer_source"],
                    r["top_document"], r["confidence"], r["response_ms"], r["topics"], r.get("answered_by")])
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=sahakar_questions.csv"})
