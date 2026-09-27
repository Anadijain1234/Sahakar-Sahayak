import re

from langdetect import detect, LangDetectException


SUPPORTED_LANGUAGES = {
    "en",
    "hi",
    "kn",
    "ne",
    "ta",
    "te",
    "ml"
}


def preprocess_query(query: str) -> str:
    """
    Clean and normalize the user's query
    without changing its language.
    """

    query = query.strip()

    # Remove extra spaces
    query = re.sub(r"\s+", " ", query)

    # Remove unnecessary punctuation at the end
    query = query.rstrip("?!.,").strip()

    return query


def validate_language(language: str) -> str:
    """
    Validate the language supplied by the client.
    """

    language = language.lower().strip()

    if language not in SUPPORTED_LANGUAGES:
        return "en"

    return language


def detect_intent(query: str, language: str = "en") -> str:
    """Rough topic of the (English) question, shown in logs and returned by /query."""
    q = query.lower()

    rules = [
        ("eligibility", ["eligible", "eligibility", "who can", "can i get", "qualify", "entitled"]),
        ("documents_required", ["document", "papers", "certificate", "proof", "aadhaar", "form"]),
        ("deadline", ["deadline", "last date", "within how many", "how many days", "how many hours", "cut-off", "cut off"]),
        ("amount_or_benefit", ["how much", "amount", "subsidy", "benefit", "installment", "instalment", "premium", "limit", "interest"]),
        ("registration", ["register", "registration", "form a society", "start a society", "new society"]),
        ("governance", ["election", "board", "committee", "general body", "meeting", "audit", "bye-law", "byelaw", "dividend"]),
        ("complaint_or_dispute", ["complaint", "dispute", "grievance", "fraud", "not received", "rejected"]),
        ("procedure", ["how to", "how do", "how can", "process", "procedure", "steps", "apply"]),
    ]
    for intent, words in rules:
        if any(w in q for w in words):
            return intent
    return "general"


def detect_language(query: str) -> str:

    try:
        return detect(query)

    except LangDetectException:
        return "unknown"


if __name__ == "__main__":

    test_queries = [
        "How do I register a new cooperative society?",
        "Am I eligible for PM-KISAN if I am a retired pensioner?",
        "Within how many hours must I report crop loss under PMFBY?",
        "How much subsidy is given for drip irrigation?",
    ]

    for query in test_queries:
        cleaned = preprocess_query(query)
        language = validate_language(detect_language(cleaned))
        print("Query    :", query)
        print("Language :", language)
        print("Intent   :", detect_intent(cleaned, language))
        print()
