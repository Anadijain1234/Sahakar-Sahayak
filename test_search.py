"""
Quick check of the search. Run from the project folder:
    python3 test_search.py
It prints, for each question, the top 2 PDF pieces with:
  final | keyword | spelling | meaning | document | page
"""
from backend.services import retriever as r

QUESTIONS = [
    # exact wording from the PDFs
    "Within how many hours must a farmer report localized calamities under PMFBY?",
    "What is the maximum collateral free loan limit under KCC?",
    # same meaning, different words (meaning search should help here)
    "My crop got spoiled in heavy rain, whom should I inform and how fast?",
    "How much money does the government give farmers every year directly in bank?",
    # spelling mistakes
    "kishan samman nidhi eligibility for pensioners",
    # off-topic (should find nothing)
    "Who won the cricket world cup?",
    "Suggest a good Bollywood movie",
]

print("\nMeaning search is", "ON" if r._vectors is not None else "OFF", "\n")
for q in QUESTIONS:
    print("Q:", q)
    results, stats = r.search(q)
    if not results:
        print("   (nothing matched -> Sarvam general knowledge)")
    for x in results[:2]:
        m = f"{x['meaning_score'] * 100:.2f}%" if x['meaning_score'] is not None else "off"
        print(f"   final {x['final_score'] * 100:.2f}% | keyword {x['keyword_score'] * 100:.2f}% | "
              f"spelling {x['spelling_score'] * 100:.2f}% | meaning {m} | {x['document'][:40]} p.{x['page']}")
    print()