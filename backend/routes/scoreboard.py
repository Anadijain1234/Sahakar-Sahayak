"""
Live accuracy scoreboard -- open /scoreboard in a browser.

What it shows
  1. The OFFICIAL result saved in the repo (benchmark_results.json). The team
     runs the benchmark ONCE (python3 evaluate_rag.py --run, then --grade)
     and pushes that file, so the page always shows the full result.
  2. A "Re-check search now" button for visitors. It runs ONLY the free search
     test (no AI answers at all), so nobody -- including judges -- can spend
     your Sarvam / Groq / Cloudflare credits from this page.

  GET  /scoreboard         -> the page
  POST /scoreboard/run     -> free search re-check (max once a minute)
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

SEARCH_COOLDOWN_S = 60

_lock = threading.Lock()
_state = {"running": False, "done": 0, "total": 0, "last_run": 0.0, "error": None, "live": None}


def _load_official():
    try:
        with open(os.path.join(ROOT, "benchmark_results.json"), "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and ("summary" in data or data.get("version") in (2, 3)):
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


ORDER = ["sarvam", "groq", "cloudflare", "sarvam_plain"]
GROUPS = {
    "fact": "Facts from the PDFs", "multi_case": "Answers with several cases",
    "language": "Hindi / Kannada / Nepali / Hinglish / typos", "reply_language": "Reply in the chosen language",
    "false_premise": "Wrong assumption corrected", "not_in_docs": "On-topic, not in the PDFs",
    "off_topic": "Off-topic & rule-breaking tricks",
}
LANGS = {"en": "English", "hi": "Hindi", "kn": "Kannada", "ne": "Nepali"}
GRADE_CLASS = {"correct": "ok", "partial": "mid", "wrong": "bad"}
JUDGE_SHORT = {"sarvam": "Sarvam", "groq": "Groq", "cloudflare": "Cloudflare"}


def _grade_chip(g):
    if not g:
        return '<span class="muted">—</span>'
    return f'<span class="chip {GRADE_CLASS.get(g["grade"], "")}" title="{_e(g.get("reason"))}">{_e(g["grade"])}</span>'


def _official_section(result):
    s = result.get("summary") or {}
    C = s.get("contestants") or {}
    present = [c for c in ORDER if c in C]
    if not present:
        return '<p class="muted">The benchmark has not been run yet.</p>'
    J = s.get("judges") or {}
    out = [f'''<p class="muted">{s.get("questions", 0)} questions · three AIs from three companies answer using our
      document search, and <b>every answer is graded by the other AIs, never by the one that wrote it</b> ·
      two judges agree on {_pct(J.get("agreement"))} of double-graded answers · run {_e(s.get("generated_at"))}</p>''']

    hero = []
    for c in present:
        b = C[c]
        hero.append(f'''<div class="card hero-card {'main' if c == 'sarvam' else ''}">
          <div class="k">{_e(b["short"])}</div><div class="big">{_pct(b.get("score"))}</div>
          <div class="muted small">judged by {_e(" + ".join(b.get("judged_by", [])))} ·
          {b["graded"]} of {b["answered"]} graded</div></div>''')
    out.append(f'<section class="cards three">{"".join(hero)}</section>')
    d = s.get("documents_add")
    if d:
        out.append(f'''<div class="banner ok-bg">📚 <b>What our document search adds to Sarvam:</b>
          {d["without"]:.2f}% → {d["with"]:.2f}% (<b>{d["points"]:+.2f} points</b>, same judge: {_e(d["judge"])})</div>''')

    def table(title, rows):
        head = "<tr><th></th>" + "".join(f"<th>{_e(C[c]['short'])}</th>" for c in present) + "</tr>"
        body = "".join(f"<tr><td>{_e(label)}</td>" + "".join(f'<td class="mono">{fn(C[c])}</td>' for c in present) + "</tr>"
                       for label, fn in rows)
        return f'<h2>{title}</h2><div class="tablewrap"><table>{head}{body}</table></div>'

    names = J.get("names") or {}
    out.append(table("Score by question type", [
        (name, (lambda b, k=k: _pct((b["by_group"].get(k) or {}).get("score")))) for k, name in GROUPS.items()] + [
        (f"Score from {names.get(j, j)}", (lambda b, j=j: _pct((b["by_judge"].get(j) or {}).get("score"))))
        for j in ("sarvam", "groq", "cloudflare")]))
    out.append(table("Score by language", [
        (name, (lambda b, k=k: _pct((b["by_language"].get(k) or {}).get("score")))) for k, name in LANGS.items()]))
    out.append(table("Automatic checks (no AI judge)", [
        ("Key fact present", lambda b: _pct(b["auto"]["key_fact_found"])),
        ("Answer in the chosen language's script", lambda b: _pct(b["auto"]["right_language"])),
        ("Off-topic questions refused", lambda b: _pct(b["auto"]["offtopic_refused"])),
        ("On-topic wrongly refused (lower is better)", lambda b: _pct(b["auto"]["wrongly_refused"])),
        ("Correct official PDF shown", lambda b: _pct(b["auto"]["correct_source_shown"])),
        ("Avg response time", lambda b: f'{b["auto"]["avg_time_s"]:.2f} s' if b["auto"].get("avg_time_s") is not None else "—"),
    ]))
    if "sarvam" in C and C["sarvam"].get("search"):
        sr = C["sarvam"]["search"]
        cards = [("Correct PDF ranked #1", _pct(sr["hit_at_1"])), ("Correct PDF in top 3", _pct(sr["hit_at_3"])),
                 ("Correct PDF sent to AI (top 6)", _pct(sr["hit_at_6"])), ("Exact page found", _pct(sr["page_at_6"])),
                 ("'Not in PDFs' not falsely Verified", _pct(sr["not_in_docs_honest"]))]
        out.append("<h2>Our document search</h2><section class='cards'>" + "".join(
            f'<div class="card"><div class="v">{v}</div><div class="k">{k}</div></div>' for k, v in cards) + "</section>")

    items = []
    for r in result.get("questions", []):
        runs = r.get("runs") or {}
        grades = r.get("grades") or {}
        key = _e(r.get("reference"))
        if r.get("doc"):
            key += f' <span class="muted small">({_e(r["doc"])}, page {_e(", ".join(map(str, r.get("pages") or [])))})</span>'
        blocks = []
        for c in present:
            run = runs.get(c)
            if not run:
                continue
            if run.get("error"):
                blocks.append(f'<div class="ans"><b>{_e(C[c]["short"])}</b> <span class="bad">no answer</span></div>')
                continue
            ans = run.get("answer") or ""
            auto = run.get("auto") or {}
            chips = " · ".join(f'{JUDGE_SHORT[j]} {_grade_chip((grades.get(j) or {}).get(c))}'
                               for j in ("sarvam", "groq", "cloudflare") if c in (grades.get(j) or {}))
            blocks.append(f'''<div class="ans"><div><b>{_e(C[c]["short"])}</b>
              <span class="muted small">{run.get("time_s", 0):.1f}s</span> · {chips or '<span class="muted">not graded</span>'}
              <span class="small muted">· fact {_tick(auto.get("fact_ok"))} · language {_tick(auto.get("lang_ok"))}
              {"· source " + _tick(auto.get("source_ok")) if "source_ok" in auto else ""}</span></div>
              <div class="small">{_e(ans[:600])}{"…" if len(ans) > 600 else ""}</div></div>''')
        items.append(f'''<details><summary><span class="mono">{_e(r["id"])}</span>
          <span class="tag">{_e(GROUPS.get(r["group"], r["group"]))}</span>
          <span class="tag">{_e(LANGS.get(r["language"], r["language"]))}</span> {_e(r["q"])}</summary>
          <div class="key"><b>Answer key:</b> {key}</div>{"".join(blocks)}</details>''')
    out.append(f'<h2>Every question ({len(items)})</h2><p class="muted small">Click a question to see every answer '
               f'and its grades (hover a grade for the judge\'s reason).</p>{"".join(items)}')
    return "".join(out)


def _live_section():
    running, live = _state["running"], _state["live"]
    disabled = "disabled" if running else ""
    out = ['<h2>Re-check our search now</h2>']
    if running:
        out.append(f'<div class="banner run">⏳ Checking… {_state["done"]} / {_state["total"] or "…"} questions. '
                   f'This page refreshes by itself.</div>')
    elif _state["error"]:
        out.append(f'<div class="banner warn">Check failed: {_e(_state["error"])}</div>')
    elif live:
        s = live["summary"]
        out.append(f'<div class="banner ok-bg">Live search check on {s["questions"]} English document questions: '
                   f'correct PDF #1 <b>{_pct(s["hit_at_1"])}</b> · in top 6 <b>{_pct(s["hit_at_6"])}</b> · '
                   f'exact page {_pct(s["page_at_6"])} · avg search {s["avg_search_ms"]:.2f} ms · '
                   f'meaning search {"on" if s.get("meaning_search") else "off"} · run {_e(s["generated_at"])}</div>')
    out.append(f'''
    <form method="post" action="/scoreboard/run" class="actions">
      <button class="primary" {disabled}>Re-check search now <span>about a minute · free, no AI answers are generated</span></button>
    </form>
    <p class="muted small">This button re-runs only the document search part, live, for free. The full result above was
    produced once by the team, because writing and grading the AI answers uses the team's credits.</p>''')
    return "".join(out)


@router.get("/scoreboard", response_class=HTMLResponse, include_in_schema=False)
def scoreboard_page():
    official = _load_official()
    if official and official.get("version") == 3:
        main = _official_section(official)
    elif official:
        o = (official.get("summary") or {}).get("overall") or {}
        main = (f'<p class="muted">The new 3-AI benchmark has not been run yet. Previous 26-question check: '
                f'{o.get("passed", "—")}/{o.get("total", "—")} passed.</p>')
    else:
        main = '<p class="muted">No saved result yet.</p>'
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
.three{{grid-template-columns:repeat(auto-fit,minmax(220px,1fr))}}.hero-card .big{{font-size:34px;font-weight:800;line-height:1.1;font-family:ui-monospace,Menlo,Consolas,monospace}}
.hero-card.main{{border:2px solid var(--brand)}}.hero-card .k{{font-weight:700;color:var(--ink);font-size:14px}}
details{{background:var(--card);border:1px solid var(--line);border-radius:10px;margin:6px 0;padding:8px 12px}}
summary{{cursor:pointer;font-size:13px}}.tag{{display:inline-block;font-size:11px;border:1px solid var(--line);border-radius:999px;padding:0 7px;margin-right:4px;color:var(--muted)}}
.tag.hid{{border-color:var(--brand);color:var(--brand)}}.key{{font-size:13px;margin:8px 0;padding:8px;border-radius:8px;background:var(--bg)}}
.ans{{border-top:1px solid var(--line);padding:8px 0;font-size:13px}}.chip{{font-size:11px;font-weight:700;border-radius:6px;padding:1px 6px;cursor:help}}
.chip.ok{{background:var(--okbg);color:var(--ok)}}.chip.mid{{background:var(--warn)}}.chip.bad{{color:var(--bad);border:1px solid var(--bad)}}
</style></head><body><main>
<h1>🌾 Sahakar Sahayak · Accuracy Scoreboard</h1>
<div class="muted">Sarvam, Groq and Cloudflare answer questions with keys from official government PDFs, and grade
each other · <a href="/scoreboard.json">raw JSON</a></div>
{main}
{_live_section()}
</main></body></html>''')
