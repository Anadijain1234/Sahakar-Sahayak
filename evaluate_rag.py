import json
import time
from backend.services.rag_service import get_answer
from backend.services.retriever import retrieve_documents  # Added FAISS import

# Load test cases
test_cases = [
    {
        "Test_ID": "T-01",
        "Scheme": "PMSKY",
        "Question": "What is the subsidy percentage for a small farmer installing micro irrigation",
        "Ground Truth": "55% of indicative unit cost (General states: 60:40",
        "Citation": "Pg 2 sec 3"
    },
    {
        "Test_ID": "T-02",
        "Scheme": "PMSKY",
        "Question": "What is the lock in period before the same land parcel can re apply for micro irrigation support",
        "Ground Truth": "Strictly once within a 7 year implementation period",
        "Citation": "Page 2, sec 3"
    },
    {
        "Test_ID": "T-03",
        "Scheme": "PMSKY",
        "Question": "What are the recorded cumulative farmers benefitted by PMSKY",
        "Ground Truth": "Over 27 million farmers",
        "Citation": "page 1, sec 1"
    },
    {
        "Test_ID": "T-04",
        "Scheme": "PMSKY",
        "Question": "What is the cost sharing pattern between the Central and state governments for NE and Himalayan states",
        "Ground Truth": "90:10 funding ratio between central government and state government",
        "Citation": "Para 3"
    },
    {
        "Test_ID": "T-05",
        "Scheme": "RWBCIS",
        "Question": "What government subsidy requirement must be met on the portal before an insurance",
        "Ground Truth": "For general weather condition claims, insurance companies must receive the tentative final share of",
        "Citation": None
    },
    {
        "Test_ID": "T-06",
        "Scheme": "RWBCIS",
        "Question": "What specific state government subsidy release condition is required for insurance companies",
        "Ground Truth": "Insurance companies must have received the 1st installment, which is 50% of the applicable State",
        "Citation": None
    },
    {
        "Test_ID": "T-07",
        "Scheme": "KCC",
        "Question": "What is the maximum collateral free loan limit under the KCC scheme",
        "Ground Truth": "₹2,00,000 for standard ag/allied loans(upto ₹3,00,000 for tie up arrangements)",
        "Citation": "Page 9, para 21&23"
    },
    {
        "Test_ID": "T-08",
        "Scheme": "KCC",
        "Question": "How are post harvest and asset maintenance expenses calculated in KCC crop limit",
        "Ground Truth": "10% of crop cost for post harvest +20% for asset maintenance",
        "Citation": "Page 5, Para 12(1)"
    },
    {
        "Test_ID": "T-09",
        "Scheme": "KCC",
        "Question": "What is the flexi credit limit range available for marginal farmers under KCC",
        "Ground Truth": "₹10,000 to ₹50,000 as flexi KCC without linking directly to land value",
        "Citation": "Page 6, Para 12(7)"
    },
    {
        "Test_ID": "T-10",
        "Scheme": "KCC",
        "Question": "What is the total tenure of the composite facility under the KCC scheme",
        "Ground Truth": "Six years",
        "Citation": None
    },
    {
        "Test_ID": "T-11",
        "Scheme": "KCC",
        "Question": "If a borrower avails a KCC loan for both crop cultivation and allied activities, how is the 10%",
        "Ground Truth": "The 10% consumption allowance is considered only once and is not calculated separately for each activity",
        "Citation": None
    },
    {
        "Test_ID": "T-12",
        "Scheme": "KCC",
        "Question": "How does the RBI KCC direction define \"Marginal Farmer\" vs \"Small Farmer\"",
        "Ground Truth": "Marginal Farmer: Landholding upto 1 hectare. Small Farmer: Landholding >1 hectare and upto 2 hectare",
        "Citation": None
    },
    {
        "Test_ID": "T-13",
        "Scheme": "PM-KISAN",
        "Question": "What is the annual financial benefit provided per eligible farmer's family under PM-KISAN",
        "Ground Truth": "₹6,000 per year released online directly into bank accounts via DBT in three equal installments of ₹2,000",
        "Citation": "Paras 2 and 10.1"
    },
    {
        "Test_ID": "T-14",
        "Scheme": "PM-KISAN",
        "Question": "Are retired government employees drawing a monthly pension eligible for PM-KISAN benefits",
        "Ground Truth": "No, retired pensioners whose monthly pension is ₹10,000 or more are excluded.However Multi-tasking staff/Group D",
        "Citation": "Para 4.1(b)(iv)"
    },
    {
        "Test_ID": "T-15",
        "Scheme": "PM-KISAN",
        "Question": "Is a person who purcahses cultivable land through a sale deed after 01.02.2019 eligible for PM_KISAN",
        "Ground Truth": "No, the transferee is not eligible because they were not landowner as of 01.02.2019",
        "Citation": "Para 5.3.3(ii)"
    },
    {
        "Test_ID": "T-16",
        "Scheme": "PMFBY",
        "Question": "What is the maximum claim payout limit and policy status when a farmer experiences prevented",
        "Ground Truth": "Up to a maximum of 25% of the sum insured, after which the crop innsurance policy cover stands terminated for that",
        "Citation": "Para 21.3.5"
    },
    {
        "Test_ID": "T-17",
        "Scheme": "PMFBY",
        "Question": "What is the eligible age range and benefit provided for personal accident coverage (sec 3) under UPIS",
        "Ground Truth": "Eligibility is 18 to 70 years. Provides ₹2 lakh for accidental death/permanent disability and ₹1 lakh for partial disability",
        "Citation": "UPIS Section 3"
    }
]

def run_benchmark():
    results = []
    passed_count = 0
    start_time = time.time()

    print(f"\n{'='*80}\nRUNNING BENCHMARK EVALUATION ({len(test_cases)} TEST CASES)\n{'='*80}")

    for case in test_cases:
        test_id = case["Test_ID"]
        scheme = case["Scheme"]
        query = case["Question"]
        ground_truth = case["Ground Truth"]

        # 1. Fetch relevant PDF paragraphs from FAISS database
        retrieved_docs = retrieve_documents(query, top_k=3)

        # 2. Pass those PDF paragraphs to Gemini to get the final answer
        rag_response = get_answer(query=query, retrieved_docs=retrieved_docs)
        
        confidence = rag_response.get("confidence", 0.0)
        sources = rag_response.get("sources", [])
        retrieved_text = rag_response.get("answer", "")

        # Retrieval check based on threshold
        hit = confidence >= 0.60
        if hit:
            passed_count += 1

        results.append({
            "Test_ID": test_id,
            "Scheme": scheme,
            "Query": query,
            "Confidence": confidence,
            "Hit": hit,
            "Source_Doc": sources[0]["document"] if sources else "None",
            "Source_Page": sources[0]["page"] if sources else "N/A",
            "Ground_Truth": ground_truth,
            "Retrieved_Answer": retrieved_text[:120] + "..." if len(retrieved_text) > 120 else retrieved_text
        })

        print(f"[{test_id}] Scheme: {scheme} | Confidence: {confidence:.2f} | Hit: {'✅' if hit else '❌'}")

    total_time = time.time() - start_time
    avg_confidence = sum(r["Confidence"] for r in results) / len(results)

    # Save detailed evaluation summary to JSON file
    with open("benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*80}")
    print(f"BENCHMARK COMPLETED IN {total_time:.2f}s")
    print(f"Total Test Cases : {len(test_cases)}")
    print(f"Successful Hits  : {passed_count}/{len(test_cases)} ({passed_count/len(test_cases)*100:.1f}%)")
    print(f"Avg Confidence   : {avg_confidence:.2f}")
    print(f"Detailed logs saved to: benchmark_results.json")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    run_benchmark()