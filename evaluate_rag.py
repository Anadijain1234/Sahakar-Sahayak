"""
Sahakar Sahayak -- accuracy scoreboard.

Runs a fixed set of test questions (farmer schemes, cooperative law,
off-topic questions and mixed-language questions) through the real
search + answer pipeline and measures how well it does.

Every expected answer below was checked against the official PDFs in
backend/data/documents (document + page noted for each).

The full test (with Sarvam answers) is run ONCE by the team, and its result
file is pushed to GitHub. The live page https://sahakar-sahayak-4.onrender.com/scoreboard
then shows that saved result; visitors can only re-run the FREE search check,
so nobody can spend your Sarvam credits.

Keys are read from a .env file in the project folder (it is in .gitignore,
so it never goes to GitHub). No 'export' needed.

HOW TO RUN IN A TERMINAL (from the project folder)
    python3 evaluate_rag.py            -> search only (no API keys needed, ~1 second)
    python3 evaluate_rag.py --full     -> search + Sarvam answers (needs SARVAM_API_KEY,
                                          takes a few minutes; uses a few API calls)

Add CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN in the terminal too if you
want meaning search included (otherwise it runs word search only).

OUTPUT
    - a table in the terminal
    - benchmark_results.json  (every question, every score)
    - benchmark_report.md     (a clean summary you can paste in your PPT/README)

WHAT IS MEASURED
  Search (always):
    Hit@1   -- the correct document is the #1 result
    Hit@3   -- the correct document is in the top 3
    Hit@6   -- the correct document is anywhere in the 6 pieces sent to the AI
    MRR     -- mean reciprocal rank (1.0 = always first, 0.5 = usually second ...)
    Page@6  -- the exact expected page is among the 6 pieces
    Off-topic rejection -- off-topic questions return NO document
    Search time -- average / 95th percentile, in milliseconds
  Answers (--full only):
    Fact accuracy      -- the answer contains the key fact(s) (e.g. "72 hours", "6000")
    Source accuracy    -- the source shown to the user is the correct document
    Refusal accuracy   -- off-topic questions are politely refused
    Mixed-language     -- Kannada/Hindi + English questions are understood
    Response time      -- full question-to-answer time
"""

import os
import re
import sys
import json
import time
import statistics
from datetime import datetime

# Read keys from a .env file in the project folder (never committed to GitHub),
# so nothing has to be typed in the terminal.
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except Exception:
    pass

# ---------------------------------------------------------------------------
# Test set
#   doc       : part of the expected PDF file name (None = no document expected)
#   pages     : expected page(s) in that PDF (optional)
#   facts     : list of groups; EVERY group must match, ANY word inside a group counts
#   kind      : scheme | cooperative | offtopic | mixed
#   needs_ai  : question only makes sense after Sarvam translates it (--full only)
# ---------------------------------------------------------------------------
TEST_CASES = [
    # ---- Farmer schemes -----------------------------------------------------
    {"id": "S01", "kind": "scheme", "topic": "PM-KISAN",
     "q": "How much money does a farmer get every year under PM-KISAN?",
     "doc": "PM-KISAN", "pages": [2, 10], "facts": [["6000", "6,000"]]},
    {"id": "S02", "kind": "scheme", "topic": "PM-KISAN",
     "q": "In how many installments is the PM-KISAN benefit paid and how much is each installment?",
     "doc": "PM-KISAN", "pages": [10], "facts": [["2000", "2,000"], ["three", "3"]]},
    {"id": "S03", "kind": "scheme", "topic": "PM-KISAN",
     "q": "Are retired pensioners eligible for PM-KISAN benefits?",
     "doc": "PM-KISAN", "pages": [3], "facts": [["10,000", "10000"]]},
    {"id": "S04", "kind": "scheme", "topic": "PM-KISAN",
     "q": "What is the cut-off date for land ownership eligibility under PM-KISAN?",
     "doc": "PM-KISAN", "pages": [3], "facts": [["01.02.2019", "1.2.2019", "february 2019", "1st february", "01/02/2019", "2019"]]},
    {"id": "S05", "kind": "scheme", "topic": "PMFBY",
     "q": "Within how many hours must a farmer report crop loss due to localized calamities under PMFBY?",
     "doc": "doc1", "pages": [103], "facts": [["72"]]},
    {"id": "S06", "kind": "scheme", "topic": "PMFBY",
     "q": "How can a farmer intimate crop loss under PMFBY, through which app or helpline?",
     "doc": "doc1", "pages": [103], "facts": [["crop insurance app", "toll-free", "toll free", "helpline", "krishi rakshak", "14447"]]},
    {"id": "S07", "kind": "scheme", "topic": "KCC",
     "q": "Up to what amount are Kisan Credit Card loans given without collateral security?",
     "doc": "405MDD58", "pages": [9], "facts": [["2 lakh", "2,00,000", "200000", "two lakh"]]},
    {"id": "S08", "kind": "scheme", "topic": "KCC",
     "q": "What is the tenure of the KCC composite credit facility?",
     "doc": "405MDD58", "pages": [4], "facts": [["six years", "6 years", "6-year", "six-year", "6 year"]]},
    {"id": "S09", "kind": "scheme", "topic": "KCC",
     "q": "Who is a marginal farmer as per the RBI Kisan Credit Card directions?",
     "doc": "405MDD58", "pages": [3], "facts": [["one hectare", "1 hectare"]]},
    {"id": "S10", "kind": "scheme", "topic": "KCC",
     "q": "What is the flexi KCC credit limit for marginal farmers?",
     "doc": "405MDD58", "pages": [6], "facts": [["10,000", "10000"], ["50,000", "50000"]]},
    {"id": "S11", "kind": "scheme", "topic": "UPIS",
     "q": "What is the age limit for farmers to join the Unified Package Insurance Scheme?",
     "doc": "UPIS", "pages": [3], "facts": [["18"], ["70"]]},
    {"id": "S12", "kind": "scheme", "topic": "PMKSY",
     "q": "What subsidy do small and marginal farmers get for micro irrigation under PMKSY?",
     "doc": "PMKSY", "pages": [2], "facts": [["55"]]},
    {"id": "S13", "kind": "scheme", "topic": "PMKSY",
     "q": "What is the central and state funding ratio for North Eastern and Himalayan states under PMKSY?",
     "doc": "PMKSY", "pages": [2], "facts": [["90:10", "90 : 10", "90/10", "90 percent", "90%", "90 per"]]},

    # ---- Cooperative law & PACS ---------------------------------------------
    {"id": "C01", "kind": "cooperative", "topic": "Karnataka Act",
     "q": "How often must a cooperative society in Karnataka get its accounts audited?",
     "doc": "11of1959", "pages": None, "facts": [["every year", "annual", "once a year", "each year", "yearly", "every co-operative year", "every financial year"]]},
    {"id": "C02", "kind": "cooperative", "topic": "MSCS Amendment 2023",
     "q": "Which authority conducts elections of multi-state cooperative societies after the 2023 amendment?",
     "doc": "247816", "pages": None, "facts": [["election authority"]]},
    {"id": "C03", "kind": "cooperative", "topic": "MSCS Amendment 2023",
     "q": "Which fund was created for the revival of sick multi-state cooperative societies under the 2023 amendment?",
     "doc": "247816", "pages": None, "facts": [["rehabilitation"]]},
    {"id": "C04", "kind": "cooperative", "topic": "Model Bye-laws",
     "q": "What percentage of net profit must a PACS transfer to its reserve fund every year under the model bye-laws?",
     "doc": "Model Byelaws", "pages": [17], "facts": [["25"]]},
    {"id": "C05", "kind": "cooperative", "topic": "Model Bye-laws",
     "q": "What is the maximum borrowing limit of a PACS compared to its paid-up share capital and reserves?",
     "doc": "Model Byelaws", "pages": [17], "facts": [["25 times", "25-times", "twenty five times", "twenty-five times"]]},
    {"id": "C06", "kind": "cooperative", "topic": "Model Bye-laws",
     "q": "Who decides the rate of dividend in a PACS?",
     "doc": "Model Byelaws", "pages": [13], "facts": [["general body", "general meeting"]]},
    {"id": "C07", "kind": "cooperative", "topic": "PACS initiatives",
     "q": "What is the total financial outlay for the computerisation of PACS?",
     "doc": "Initiatives", "pages": [1], "facts": [["2925", "2,925"]]},
    {"id": "C08", "kind": "cooperative", "topic": "PACS initiatives",
     "q": "Can PACS run Jan Aushadhi Kendras to sell generic medicines?",
     "doc": "Initiatives", "pages": [4], "facts": [["jan aushadhi"]]},

    # ---- Mixed language (needs Sarvam to translate first) --------------------
    {"id": "M01", "kind": "mixed", "topic": "PM-KISAN", "needs_ai": True,
     "q": "PM Kisan yojane alli varshakke eshtu duddu sigutte?",
     "doc": "PM-KISAN", "pages": [2, 10], "facts": [["6000", "6,000", "6,000", "೬೦೦೦"]]},
    {"id": "M02", "kind": "mixed", "topic": "PMFBY", "needs_ai": True,
     "q": "fasal bima mein nuksan hone par kitne ghante mein batana padta hai?",
     "doc": "doc1", "pages": [103], "facts": [["72", "७२"]]},

    # ---- Off-topic (must be refused, no document) ----------------------------
    {"id": "O01", "kind": "offtopic", "topic": "Cricket",
     "q": "Who won the cricket world cup?", "doc": None, "pages": None, "facts": []},
    {"id": "O02", "kind": "offtopic", "topic": "Movies",
     "q": "Suggest a good Bollywood movie to watch tonight", "doc": None, "pages": None, "facts": []},
    {"id": "O03", "kind": "offtopic", "topic": "Politics",
     "q": "Which party will win the next general election?", "doc": None, "pages": None, "facts": []},
]


# ---------------------------------------------------------------------------
def _pct(n, d):
    return round(100.0 * n / d, 2) if d else 0.0


def _p95(values):
    if not values:
        return 0.0
    s = sorted(values)
    return round(s[min(len(s) - 1, int(round(0.95 * (len(s) - 1))))], 2)


def _norm(text: str) -> str:
    return " ".join((text or "").lower().replace("₹", " ").replace("rs.", " ").split())


def _facts_found(answer: str, groups) -> bool:
    a = _norm(answer)
    a_nocomma = a.replace(",", "")
    for group in groups:
        if not any(_norm(w) in a or _norm(w).replace(",", "") in a_nocomma for w in group):
            return False
    return True


def _rank_of(results, doc_part):
    for i, r in enumerate(results, start=1):
        if doc_part.lower() in r["document"].lower():
            return i
    return None


def run_benchmark(full: bool = False, log=print, progress=None) -> dict:
    """Run the scoreboard and return {"summary": ..., "questions": [...]}.
    Used by the terminal (python3 evaluate_rag.py) AND by the live /scoreboard page.
    `progress(done, total)` is called after each question (optional)."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from backend.services import retriever
    from backend.services.retriever import search
    from backend.services import rag_service as rag   # (no Sarvam call unless full=True)

    if full and rag.client is None:
        log("⚠️  Full test needs SARVAM_API_KEY. Running search-only instead.")
        full = False

    meaning_on = retriever._vectors is not None
    cases = [c for c in TEST_CASES if full or not c.get("needs_ai")]
    log("=" * 96)
    log(f" SAHAKAR SAHAYAK SCOREBOARD   mode: {'SEARCH + ANSWERS' if full else 'SEARCH ONLY'}   "
        f"meaning search: {'ON' if meaning_on else 'OFF'}   pieces: {len(retriever.chunks)}")
    log("=" * 96)

    rows = []
    for n, case in enumerate(cases, start=1):
        row = {"id": case["id"], "kind": case["kind"], "topic": case["topic"], "question": case["q"],
               "expected_doc": case["doc"], "expected_pages": case["pages"],
               "expected_facts": [g[0] for g in case["facts"]]}
        started = time.perf_counter()

        query = case["q"]
        if full:
            query = rag.normalize_query_to_english(case["q"])
            row["english_question"] = query
        boost = rag.lexicon_terms(f"{case['q']} {query}")   # same as the live app
        results, stats = search(query, boost_terms=boost)
        row["search_time_ms"] = stats.get("search_time_ms", 0.0)
        row["pieces_returned"] = len(results)
        row["top_results"] = [
            {"document": r["document"], "page": r["page"], "final": round(r["final_score"] * 100, 2),
             "keyword": round(r["keyword_score"] * 100, 2),
             "meaning": round(r["meaning_score"] * 100, 2) if r["meaning_score"] is not None else None}
            for r in results
        ]

        if case["doc"]:
            rank = _rank_of(results, case["doc"])
            row["rank"] = rank
            row["hit1"] = rank == 1
            row["hit3"] = rank is not None and rank <= 3
            row["hit6"] = rank is not None
            row["rr"] = (1.0 / rank) if rank else 0.0
            if case["pages"]:
                row["page_hit"] = any(case["doc"].lower() in r["document"].lower() and r["page"] in case["pages"]
                                      for r in results)
        else:
            row["rejected"] = len(results) == 0

        if full:
            try:
                out = rag.get_answer(query, "en", "general", results, stats)
            except Exception as e:  # never let one bad question stop the whole test
                out = {"answer": f"(error: {e})", "trust_level": "error", "sources": []}
            answer = out.get("answer", "")
            row["answer"] = answer
            row["trust_level"] = out.get("trust_level")
            row["shown_source"] = out["sources"][0]["document"] if out.get("sources") else None
            if case["doc"]:
                row["fact_ok"] = _facts_found(answer, case["facts"])
                row["source_ok"] = bool(row["shown_source"] and case["doc"].lower() in row["shown_source"].lower())
            else:
                row["refused_ok"] = out.get("trust_level") == "refused"
            time.sleep(1.0)  # be gentle with the Sarvam API

        row["total_time_ms"] = round((time.perf_counter() - started) * 1000, 2)
        if case["doc"]:
            row["passed"] = (row["fact_ok"] and row["source_ok"]) if full else row["hit6"]
        else:
            row["passed"] = row["refused_ok"] if full else row["rejected"]
        rows.append(row)

        if case["doc"]:
            status = f"rank {row['rank'] or '-':>2}  page {'✓' if row.get('page_hit') else ('-' if not case['pages'] else '✗')}"
            if full:
                status += f"  fact {'✓' if row['fact_ok'] else '✗'}  source {'✓' if row['source_ok'] else '✗'}  {row['trust_level']}"
        else:
            status = f"rejected {'✓' if row['rejected'] else '✗'}"
            if full:
                status += f"  refused {'✓' if row['refused_ok'] else '✗'}"
        best = row["top_results"][0]["final"] if row["top_results"] else 0.0
        log(f" {row['id']}  {row['topic'][:18]:<18} best {best:6.2f}%  {status}")
        if progress:
            progress(n, len(cases))

    # ---------------- summary ----------------
    in_domain = [r for r in rows if r["expected_doc"]]
    offtopic = [r for r in rows if not r["expected_doc"]]
    with_pages = [r for r in in_domain if r.get("expected_pages")]
    search_times = [r["search_time_ms"] for r in rows]

    summary = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "mode": "search+answers" if full else "search-only",
        "meaning_search": meaning_on,
        "pieces_indexed": len(retriever.chunks),
        "pdfs_indexed": len(set(c["document"] for c in retriever.chunks)),
        "questions": len(rows),
        "search": {
            "hit_at_1": _pct(sum(r["hit1"] for r in in_domain), len(in_domain)),
            "hit_at_3": _pct(sum(r["hit3"] for r in in_domain), len(in_domain)),
            "hit_at_6": _pct(sum(r["hit6"] for r in in_domain), len(in_domain)),
            "mrr": round(sum(r["rr"] for r in in_domain) / len(in_domain), 4) if in_domain else 0.0,
            "page_at_6": _pct(sum(bool(r.get("page_hit")) for r in with_pages), len(with_pages)),
            "offtopic_rejection": _pct(sum(r["rejected"] for r in offtopic), len(offtopic)),
            "avg_search_ms": round(statistics.mean(search_times), 2) if search_times else 0.0,
            "p95_search_ms": _p95(search_times),
        },
        "by_kind": {},
    }
    for kind in ["scheme", "cooperative", "mixed"]:
        group = [r for r in in_domain if r["kind"] == kind]
        if group:
            summary["by_kind"][kind] = {
                "questions": len(group),
                "hit_at_6": _pct(sum(r["hit6"] for r in group), len(group)),
                **({"fact_accuracy": _pct(sum(r["fact_ok"] for r in group), len(group))} if full else {}),
            }

    if full:
        totals = [r["total_time_ms"] for r in rows]
        summary["answers"] = {
            "fact_accuracy": _pct(sum(r["fact_ok"] for r in in_domain), len(in_domain)),
            "source_accuracy": _pct(sum(r["source_ok"] for r in in_domain), len(in_domain)),
            "refusal_accuracy": _pct(sum(r["refused_ok"] for r in offtopic), len(offtopic)),
            "verified_share": _pct(sum(r.get("trust_level") == "verified" for r in in_domain), len(in_domain)),
            "avg_response_s": round(statistics.mean(totals) / 1000, 2) if totals else 0.0,
            "p95_response_s": round(_p95(totals) / 1000, 2),
        }
    passed = sum(r["passed"] for r in rows)
    summary["overall"] = {"passed": passed, "total": len(rows), "score": _pct(passed, len(rows))}

    s = summary["search"]
    log("-" * 96)
    log(f" SEARCH   Hit@1 {s['hit_at_1']:.2f}%   Hit@3 {s['hit_at_3']:.2f}%   Hit@6 {s['hit_at_6']:.2f}%   "
        f"MRR {s['mrr']:.4f}   Page@6 {s['page_at_6']:.2f}%   Off-topic rejected {s['offtopic_rejection']:.2f}%")
    log(f"          avg search {s['avg_search_ms']:.2f} ms   p95 {s['p95_search_ms']:.2f} ms")
    if full:
        a = summary["answers"]
        log(f" ANSWERS  Facts correct {a['fact_accuracy']:.2f}%   Source correct {a['source_accuracy']:.2f}%   "
            f"Off-topic refused {a['refusal_accuracy']:.2f}%   Verified {a['verified_share']:.2f}%")
        log(f"          avg response {a['avg_response_s']:.2f} s   p95 {a['p95_response_s']:.2f} s")
    o = summary["overall"]
    log(f" OVERALL  {o['passed']}/{o['total']} passed  ({o['score']:.2f}%)")
    log("=" * 96)
    return {"summary": summary, "questions": rows}


def save_results(result: dict, base: str = None) -> None:
    """Write benchmark_results.json and benchmark_report.md next to this file."""
    base = base or os.path.dirname(os.path.abspath(__file__))
    full = result["summary"]["mode"] == "search+answers"
    with open(os.path.join(base, "benchmark_results.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    with open(os.path.join(base, "benchmark_report.md"), "w", encoding="utf-8") as f:
        f.write(_markdown(result["summary"], result["questions"], full))


def main():
    full = "--full" in sys.argv
    print(f"\n Keys found:  Sarvam {'yes' if os.getenv('SARVAM_API_KEY') else 'NO'}   "
          f"Cloudflare {'yes' if os.getenv('CLOUDFLARE_API_TOKEN') and os.getenv('CLOUDFLARE_ACCOUNT_ID') else 'NO'}\n")
    result = run_benchmark(full=full)
    save_results(result)
    print("\n Saved: benchmark_results.json and benchmark_report.md\n")


def _markdown(summary, rows, full):
    s = summary["search"]
    lines = [
        "# Sahakar Sahayak — Accuracy Scoreboard",
        "",
        f"Generated {summary['generated_at']} · mode **{summary['mode']}** · meaning search "
        f"**{'on' if summary['meaning_search'] else 'off'}** · {summary['pieces_indexed']:,} passages from "
        f"{summary['pdfs_indexed']} official PDFs · {summary['questions']} test questions",
        "",
        f"**Overall: {summary['overall']['passed']}/{summary['overall']['total']} passed "
        f"({summary['overall']['score']:.2f}%)**",
        "",
        "## Search quality",
        "",
        "| Metric | Result |",
        "|---|---|",
        f"| Correct document ranked #1 (Hit@1) | {s['hit_at_1']:.2f}% |",
        f"| Correct document in top 3 (Hit@3) | {s['hit_at_3']:.2f}% |",
        f"| Correct document in the 6 passages sent to the AI (Hit@6) | {s['hit_at_6']:.2f}% |",
        f"| Mean reciprocal rank (MRR) | {s['mrr']:.4f} |",
        f"| Exact page found (Page@6) | {s['page_at_6']:.2f}% |",
        f"| Off-topic questions rejected by search | {s['offtopic_rejection']:.2f}% |",
        f"| Search time (avg / p95) | {s['avg_search_ms']:.2f} ms / {s['p95_search_ms']:.2f} ms |",
        "",
    ]
    if full:
        a = summary["answers"]
        lines += [
            "## Answer quality",
            "",
            "| Metric | Result |",
            "|---|---|",
            f"| Answer contains the correct fact | {a['fact_accuracy']:.2f}% |",
            f"| Correct official source shown | {a['source_accuracy']:.2f}% |",
            f"| Off-topic questions politely refused | {a['refusal_accuracy']:.2f}% |",
            f"| Answers marked 'Verified' | {a['verified_share']:.2f}% |",
            f"| Response time (avg / p95) | {a['avg_response_s']:.2f} s / {a['p95_response_s']:.2f} s |",
            "",
        ]
    lines += ["## By category", "", "| Category | Questions | Correct document found |" + (" Facts correct |" if full else ""),
              "|---|---|---|" + ("---|" if full else "")]
    for kind, v in summary["by_kind"].items():
        lines.append(f"| {kind} | {v['questions']} | {v['hit_at_6']:.2f}% |" + (f" {v['fact_accuracy']:.2f}% |" if full else ""))
    lines += ["", "## Every question", "",
              "| ID | Topic | Question | Result |", "|---|---|---|---|"]
    for r in rows:
        if r["expected_doc"]:
            res = f"rank {r['rank'] or '—'}"
            if full:
                res += f" · fact {'✓' if r['fact_ok'] else '✗'} · source {'✓' if r['source_ok'] else '✗'}"
        else:
            res = f"rejected {'✓' if r['rejected'] else '✗'}" + (f" · refused {'✓' if r['refused_ok'] else '✗'}" if full else "")
        lines.append(f"| {r['id']} | {r['topic']} | {r['question']} | {res} |")
    lines += ["", "_Expected answers were checked by hand against the official PDFs. "
              "Run `python3 evaluate_rag.py --full` to reproduce._", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
