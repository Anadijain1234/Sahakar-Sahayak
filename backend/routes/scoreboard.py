"""
Live accuracy scoreboard -- open /scoreboard in a browser.

What it shows
  1. The OFFICIAL result saved in the repo (benchmark_results.json). The team
     runs the full test with Sarvam answers ONCE (python3 evaluate_rag.py --full)
     and pushes that file, so the page always shows the full result.
  2. A "Re-check search now" button for visitors. It runs ONLY the free search
     test (no Sarvam calls at all), so nobody -- including judges -- can spend
     your Sarvam credits from this page.

  GET  /scoreboard         -> the page
  POST /scoreboard/run     -> free search re-check (max once every 10 s)
  GET  /scoreboard.json    -> official saved result as JSON
"""

import os
import sys
import json
import html
import time
import threading

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

router = APIRouter()

SEARCH_COOLDOWN_S = 10

_lock = threading.Lock()
_state = {"running": False, "done": 0, "total": 0, "last_run": 0.0, "error": None, "live": None}


def _load_official():
    try:
        with open(os.path.join(ROOT, "benchmark_results.json"), "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "summary" in data:
            return data
    except Exception:
        pass
    return None


def _worker():
    try:
        import evaluate_rag

        def progress(done, total):
            _state["done"], _state["total"] = done, total

        # full=False -> search only, never calls Sarvam
        _state["live"] = evaluate_rag.run_benchmark(full=False, log=lambda *_: None, progress=progress)
        _state["error"] = None
    except Exception as e:
        _state["error"] = str(e)
    finally:
        _state["running"] = False


@router.post("/scoreboard/run", include_in_schema=False)
def run_search_check():
    with _lock:
        now = time.time()
        if _state["running"] or now - _state["last_run"] < SEARCH_COOLDOWN_S:
            return RedirectResponse("/scoreboard", status_code=303)
        _state.update({"running": True, "done": 0, "total": 0, "last_run": now, "error": None})
    threading.Thread(target=_worker, daemon=True).start()
    return RedirectResponse("/scoreboard", status_code=303)


@router.get("/scoreboard.json", include_in_schema=False)
def scoreboard_json():
    return JSONResponse(_load_official() or {})


# ---------------------------------------------------------------------------
def _e(x):
    return html.escape(str(x)) if x is not None else "—"


def _pct(x):
    return f"{x:.2f}%" if isinstance(x, (int, float)) else "—"


def _tick(v):
    if v is None:
        return '<span class="muted">—</span>'
    return '<span class="ok">✓</span>' if v else '<span class="bad">✗</span>'


def _official_section(result):
    s = result["summary"]
    full = s.get("mode") == "search+answers"
    o, sr = s["overall"], s["search"]
    out = [f'''
    <section class="hero">
      <div class="big">{o["passed"]}<span>/{o["total"]}</span></div>
      <div>
        <div class="score">{_pct(o["score"])} passed</div>
        <div class="muted">{"Full test: search + AI answers" if full else "Search test"} ·
          meaning search {"on" if s.get("meaning_search") else "off"} ·
          {s.get("pieces_indexed", 0):,} passages from {s.get("pdfs_indexed", 0)} official PDFs ·
          run {_e(s.get("generated_at"))}</div>
      </div>
    </section>''']

    cards = []
    if full and "answers" in s:
        a = s["answers"]
        cards += [
            ("Answer contains the correct fact", _pct(a["fact_accuracy"])),
            ("Correct official source shown", _pct(a["source_accuracy"])),
            ("Off-topic questions refused", _pct(a["refusal_accuracy"])),
            ("Answers marked 'Verified'", _pct(a["verified_share"])),
            ("Avg response time", f'{a["avg_response_s"]:.2f} s'),
        ]
    cards += [
        ("Correct PDF ranked #1", _pct(sr["hit_at_1"])),
        ("Correct PDF in top 3", _pct(sr["hit_at_3"])),
        ("Correct PDF sent to AI (top 6)", _pct(sr["hit_at_6"])),
        ("Exact page found", _pct(sr["page_at_6"])),
        ("Avg search time", f'{sr["avg_search_ms"]:.2f} ms'),
    ]
    out.append('<section class="cards">' + "".join(
        f'<div class="card"><div class="v">{v}</div><div class="k">{k}</div></div>' for k, v in cards) + "</section>")

    head = "<tr><th>#</th><th>Topic</th><th>Question</th><th>Answer key (from PDF)</th><th>Rank</th>"
    head += "<th>Fact</th><th>Source</th><th>AI answer</th>" if full else "<th>Best match</th>"
    head += "<th>Result</th></tr>"
    body = []
    for r in result["questions"]:
        best = r["top_results"][0]["final"] if r.get("top_results") else None
        key = _e(r["expected_doc"]) if r["expected_doc"] else "must be refused"
        if r.get("expected_facts"):
            key += f'<div class="muted small">key fact: {_e(", ".join(r["expected_facts"]))}</div>'
        row = (f'<tr><td class="mono">{_e(r["id"])}</td><td>{_e(r["topic"])}</td>'
               f'<td class="q">{_e(r["question"])}</td><td>{key}</td>'
               f'<td class="mono">{_e(r.get("rank")) if r["expected_doc"] else "—"}</td>')
        if full:
            fact = r.get("fact_ok") if r["expected_doc"] else r.get("refused_ok")
            src = r.get("source_ok") if r["expected_doc"] else None
            ans = r.get("answer") or ""
            row += (f'<td>{_tick(fact)}</td><td>{_tick(src)}</td>'
                    f'<td class="small">{_e(ans[:220])}{"…" if len(ans) > 220 else ""}</td>')
        else:
            row += f'<td class="mono">{_pct(best)}</td>'
        row += f'<td>{_tick(r.get("passed"))}</td></tr>'
        body.append(row)
    out.append(f'<h2>Every question</h2><div class="tablewrap"><table>{head}{"".join(body)}</table></div>')
    return "".join(out)


def _live_section():
    running, live = _state["running"], _state["live"]
    disabled = "disabled" if running else ""
    out = ['<h2>Re-check search now</h2>']
    if running:
        out.append(f'<div class="banner run">⏳ Checking… {_state["done"]} / {_state["total"] or "…"} questions. '
                   f'This page refreshes by itself.</div>')
    elif _state["error"]:
        out.append(f'<div class="banner warn">Check failed: {_e(_state["error"])}</div>')
    elif live:
        s = live["summary"]
        out.append(f'<div class="banner ok-bg">Live search check just now: <b>{s["overall"]["passed"]}/{s["overall"]["total"]}</b> '
                   f'({_pct(s["overall"]["score"])}) · correct PDF in top 6: {_pct(s["search"]["hit_at_6"])} · '
                   f'avg search {s["search"]["avg_search_ms"]:.2f} ms · run {_e(s["generated_at"])}</div>')
    out.append(f'''
    <form method="post" action="/scoreboard/run" class="actions">
      <button class="primary" {disabled}>Re-check search now <span>~2 seconds · free, no AI credits used</span></button>
    </form>
    <p class="muted small">Every question has an answer key taken from the official PDFs (document, page and key fact,
    e.g. “72 hours”). The official result above was produced by running all questions through the full
    pipeline, including the AI's written answers. The button here re-runs only the search part live, for free.</p>''')
    return "".join(out)


@router.get("/scoreboard", response_class=HTMLResponse, include_in_schema=False)
def scoreboard_page():
    official = _load_official()
    main = _official_section(official) if official else '<p class="muted">No saved result yet.</p>'
    refresh = '<meta http-equiv="refresh" content="4">' if _state["running"] else ""
    return HTMLResponse(f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">{refresh}
<title>Sahakar Sahayak · Accuracy Scoreboard</title>
<style>
:root{{--bg:#f7f8f6;--card:#fff;--ink:#16211b;--muted:#5f6b64;--line:#e3e7e4;--brand:#15803d;--ok:#15803d;--bad:#b91c1c;--run:#e0f2fe;--warn:#fef3c7;--okbg:#dcfce7}}
@media (prefers-color-scheme:dark){{:root{{--bg:#0e1411;--card:#151d18;--ink:#e6ede8;--muted:#9aa8a0;--line:#26312b;--brand:#4ade80;--ok:#4ade80;--bad:#f87171;--run:#0c2a3a;--warn:#3a2f0c;--okbg:#0f2e1b}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}}
main{{max-width:1100px;margin:0 auto;padding:24px 16px 48px}}
h1{{font-size:22px;margin:0 0 4px}}h2{{font-size:16px;margin:28px 0 10px}}
.muted{{color:var(--muted)}}.small{{font-size:12px}}.mono{{font-family:ui-monospace,Menlo,Consolas,monospace}}
.hero{{display:flex;gap:18px;align-items:center;background:var(--card);border:1px solid var(--line);border-radius:16px;padding:18px 20px;margin-top:18px}}
.big{{font-size:44px;font-weight:800;color:var(--brand);line-height:1}}.big span{{font-size:22px;color:var(--muted)}}
.score{{font-size:20px;font-weight:700}}
.cards{{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:10px;margin-top:12px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px}}
.card .v{{font-size:20px;font-weight:700;font-family:ui-monospace,Menlo,Consolas,monospace}}.card .k{{font-size:12px;color:var(--muted)}}
.tablewrap{{overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:12px}}
table{{border-collapse:collapse;width:100%;font-size:13px}}th,td{{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}}
th{{font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}}td.q{{min-width:220px}}
.ok{{color:var(--ok);font-weight:700}}.bad{{color:var(--bad);font-weight:700}}
.banner{{border-radius:12px;padding:10px 14px;margin:10px 0}}.run{{background:var(--run)}}.warn{{background:var(--warn)}}.ok-bg{{background:var(--okbg)}}
.actions{{margin:10px 0 8px}}
button{{font:inherit;cursor:pointer;border-radius:12px;border:1px solid var(--brand);background:var(--card);color:var(--ink);padding:10px 14px;text-align:left}}
button span{{display:block;font-size:12px;color:var(--muted)}}button:disabled{{opacity:.5;cursor:not-allowed}}
a{{color:var(--brand)}}
</style></head><body><main>
<h1>🌾 Sahakar Sahayak · Accuracy Scoreboard</h1>
<div class="muted">The assistant tested against answer keys taken from official government PDFs ·
<a href="/scoreboard.json">raw JSON</a></div>
{main}
{_live_section()}
</main></body></html>''')
