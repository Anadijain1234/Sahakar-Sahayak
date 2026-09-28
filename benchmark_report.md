# Sahakar Sahayak — Accuracy Test Results (3 AIs grade each other)

Generated 2026-09-28 08:33 · 45 questions · each answer graded by the AIs that did NOT write it · two judges agree on 84.27% of 178 double-graded answers

## Headline

| | Sarvam + docs | Groq + docs | Cloudflare + docs | Sarvam alone |
|---|---|---|---|---|
| **Score** | **72.78%** | **72.22%** | **62.22%** | **30.56%** |
| Fully correct answers | 60.00% | 66.67% | 51.11% | 22.22% |
| Judged by | Groq · gpt-oss-20b + Cloudflare · Llama 3.3 70B | Sarvam · sarvam-105b + Cloudflare · Llama 3.3 70B | Sarvam · sarvam-105b + Groq · gpt-oss-20b | Groq · gpt-oss-20b + Cloudflare · Llama 3.3 70B |
| Answered / graded | 45 / 45 | 45 / 45 | 45 / 45 | 45 / 45 |
| Score from Sarvam · sarvam-105b | — | 70.45% | 60.23% | — |
| Score from Groq · gpt-oss-20b | 76.67% | — | 63.33% | 30.00% |
| Score from Cloudflare · Llama 3.3 70B | 68.89% | 73.33% | — | 31.11% |

## In plain words

- With our document search, Sarvam's answers were 73% correct; the same Sarvam without our search managed only 31%.
- Our search helps every AI we tried: Groq 72%, Cloudflare 62%, all far above Sarvam alone (31%).
- The app is strongest at reply in the chosen language and off-topic & rule-breaking tricks (100%), and weakest at answers with several cases (50%) -- our next thing to improve.
- Our search found the correct official PDF for 86% of the document questions.
- Two different judges gave the same grade 84% of the time, so the grading is consistent.

**What our document search adds to Sarvam:** 30.00% → 76.67% (**+46.67 points**, same judge: Groq · gpt-oss-20b)

## By question type

| | Sarvam + docs | Groq + docs | Cloudflare + docs | Sarvam alone |
|---|---|---|---|---|
| Facts from the PDFs | 75.00% | 58.93% | 57.14% | 23.21% |
| Answers with several cases | 50.00% | 62.50% | 62.50% | 0.00% |
| Hindi / Kannada / Nepali / Hinglish / typos | 55.00% | 90.00% | 62.50% | 15.00% |
| Reply in the chosen language | 100.00% | 91.67% | 66.67% | 0.00% |
| Wrong assumption must be corrected | 85.00% | 60.00% | 45.00% | 15.00% |
| On-topic but not in the PDFs | 62.50% | 50.00% | 50.00% | 81.25% |
| Off-topic & rule-breaking tricks | 100.00% | 100.00% | 100.00% | 100.00% |

## By language

| | Sarvam + docs | Groq + docs | Cloudflare + docs | Sarvam alone |
|---|---|---|---|---|
| English | 75.00% | 66.96% | 62.50% | 31.25% |
| Hindi | 66.67% | 77.78% | 66.67% | 47.22% |
| Kannada | 55.00% | 80.00% | 60.00% | 15.00% |
| Nepali | 100.00% | 91.67% | 50.00% | 0.00% |

## Automatic checks (no AI judge)

| | Sarvam + docs | Groq + docs | Cloudflare + docs | Sarvam alone |
|---|---|---|---|---|
| Key fact present (numbers / English facts) | 76.47% | 67.65% | 64.71% | 17.65% |
| Answer in the chosen language's script | 95.56% | 100.00% | 100.00% | 97.78% |
| Off-topic questions refused | 100.00% | 100.00% | 80.00% | 100.00% |
| On-topic questions wrongly refused (lower is better) | 2.50% | 2.50% | 0.00% | 10.00% |
| Correct official PDF shown as source | 77.78% | 83.33% | 77.78% | — |
| Response time avg / p95 | 1.11 s / 1.67 s | 1.25 s / 2.06 s | 4.63 s / 10.13 s | 0.65 s / 1.19 s |

## Our document search (live app)

| Metric | Result |
|---|---|
| Correct PDF ranked #1 / top 3 / top 6 | 77.78% / 83.33% / 86.11% |
| Mean reciprocal rank | 0.8102 |
| Exact page among the 6 passages | 69.44% |
| Document answers marked 🟢 Verified | 33.33% |
| 'Not in the PDFs' questions NOT falsely marked Verified | 100.00% |

## How this test works

- 45 questions in 7 groups, picked from a bank of 200; every document answer key has an exact quote from the PDF page (machine-checked). The app was never tuned on them.
- Three AIs from three companies each answer using our document search; each answer is graded by the other AIs, never by itself, without knowing who wrote it.
- Sarvam alone (same instructions, no documents) shows what our search adds.
- Reproduce: `python3 evaluate_rag.py --run` then `python3 evaluate_rag.py --grade`.
