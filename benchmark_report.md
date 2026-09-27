# Sahakar Sahayak — Accuracy Scoreboard

Generated 2026-09-27 21:38 · mode **search+answers** · meaning search **on** · 2,655 passages from 11 official PDFs · 26 test questions

**Overall: 25/26 passed (96.15%)**

## Search quality

| Metric | Result |
|---|---|
| Correct document ranked #1 (Hit@1) | 100.00% |
| Correct document in top 3 (Hit@3) | 100.00% |
| Correct document in the 6 passages sent to the AI (Hit@6) | 100.00% |
| Mean reciprocal rank (MRR) | 1.0000 |
| Exact page found (Page@6) | 80.00% |
| Off-topic questions rejected by search | 66.67% |
| Search time (avg / p95) | 194.80 ms / 409.22 ms |

## Answer quality

| Metric | Result |
|---|---|
| Answer contains the correct fact | 95.65% |
| Correct official source shown | 100.00% |
| Off-topic questions politely refused | 100.00% |
| Answers marked 'Verified' | 56.52% |
| Response time (avg / p95) | 1.82 s / 2.24 s |

## By category

| Category | Questions | Correct document found | Facts correct |
|---|---|---|---|
| scheme | 13 | 100.00% | 92.31% |
| cooperative | 8 | 100.00% | 100.00% |
| mixed | 2 | 100.00% | 100.00% |

## Every question

| ID | Topic | Question | Result |
|---|---|---|---|
| S01 | PM-KISAN | How much money does a farmer get every year under PM-KISAN? | rank 1 · fact ✓ · source ✓ |
| S02 | PM-KISAN | In how many installments is the PM-KISAN benefit paid and how much is each installment? | rank 1 · fact ✓ · source ✓ |
| S03 | PM-KISAN | Are retired pensioners eligible for PM-KISAN benefits? | rank 1 · fact ✓ · source ✓ |
| S04 | PM-KISAN | What is the cut-off date for land ownership eligibility under PM-KISAN? | rank 1 · fact ✓ · source ✓ |
| S05 | PMFBY | Within how many hours must a farmer report crop loss due to localized calamities under PMFBY? | rank 1 · fact ✓ · source ✓ |
| S06 | PMFBY | How can a farmer intimate crop loss under PMFBY, through which app or helpline? | rank 1 · fact ✓ · source ✓ |
| S07 | KCC | Up to what amount are Kisan Credit Card loans given without collateral security? | rank 1 · fact ✓ · source ✓ |
| S08 | KCC | What is the tenure of the KCC composite credit facility? | rank 1 · fact ✓ · source ✓ |
| S09 | KCC | Who is a marginal farmer as per the RBI Kisan Credit Card directions? | rank 1 · fact ✗ · source ✓ |
| S10 | KCC | What is the flexi KCC credit limit for marginal farmers? | rank 1 · fact ✓ · source ✓ |
| S11 | UPIS | What is the age limit for farmers to join the Unified Package Insurance Scheme? | rank 1 · fact ✓ · source ✓ |
| S12 | PMKSY | What subsidy do small and marginal farmers get for micro irrigation under PMKSY? | rank 1 · fact ✓ · source ✓ |
| S13 | PMKSY | What is the central and state funding ratio for North Eastern and Himalayan states under PMKSY? | rank 1 · fact ✓ · source ✓ |
| C01 | Karnataka Act | How often must a cooperative society in Karnataka get its accounts audited? | rank 1 · fact ✓ · source ✓ |
| C02 | MSCS Amendment 2023 | Which authority conducts elections of multi-state cooperative societies after the 2023 amendment? | rank 1 · fact ✓ · source ✓ |
| C03 | MSCS Amendment 2023 | Which fund was created for the revival of sick multi-state cooperative societies under the 2023 amendment? | rank 1 · fact ✓ · source ✓ |
| C04 | Model Bye-laws | What percentage of net profit must a PACS transfer to its reserve fund every year under the model bye-laws? | rank 1 · fact ✓ · source ✓ |
| C05 | Model Bye-laws | What is the maximum borrowing limit of a PACS compared to its paid-up share capital and reserves? | rank 1 · fact ✓ · source ✓ |
| C06 | Model Bye-laws | Who decides the rate of dividend in a PACS? | rank 1 · fact ✓ · source ✓ |
| C07 | PACS initiatives | What is the total financial outlay for the computerisation of PACS? | rank 1 · fact ✓ · source ✓ |
| C08 | PACS initiatives | Can PACS run Jan Aushadhi Kendras to sell generic medicines? | rank 1 · fact ✓ · source ✓ |
| M01 | PM-KISAN | PM Kisan yojane alli varshakke eshtu duddu sigutte? | rank 1 · fact ✓ · source ✓ |
| M02 | PMFBY | fasal bima mein nuksan hone par kitne ghante mein batana padta hai? | rank 1 · fact ✓ · source ✓ |
| O01 | Cricket | Who won the cricket world cup? | rejected ✓ · refused ✓ |
| O02 | Movies | Suggest a good Bollywood movie to watch tonight | rejected ✓ · refused ✓ |
| O03 | Politics | Which party will win the next general election? | rejected ✗ · refused ✓ |

_Expected answers were checked by hand against the official PDFs. Run `python3 evaluate_rag.py --full` to reproduce._
