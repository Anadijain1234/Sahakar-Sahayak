"""
"Talk to a person" -- official helplines shown under answers that are not
fully verified (and under complaints / disputes), so a farmer always has a
human to turn to.

Only verified numbers are used:
  - 14447         Krishi Rakshak Portal & Helpline (crop insurance) -- written in the
                  PMFBY Operational Guidelines 2023, para 21.5.5.4 (our doc1.pdf, page 103)
  - 1800-180-1551 Kisan Call Centre, toll-free -- Ministry of Agriculture (manage.gov.in/kcc)
"""

import re

KISAN_CALL_CENTRE = {
    "id": "kcc",
    "label": "Kisan Call Centre",
    "phone": "18001801551",
    "display": "1800-180-1551",
    "note": "Toll-free · farming, schemes and loans",
}
KRISHI_RAKSHAK = {
    "id": "krishi_rakshak",
    "label": "Crop insurance helpline (Krishi Rakshak)",
    "phone": "14447",
    "display": "14447",
    "note": "Report crop loss within 72 hours · PMFBY / weather insurance",
}
PM_KISAN_HELPDESK = {
    "id": "pmkisan",
    "label": "PM-KISAN helpdesk",
    "url": "https://pmkisan.gov.in/",
    "display": "pmkisan.gov.in",
    "note": "Payment status, eKYC and complaints",
}
COOP_REGISTRAR = {
    "id": "registrar",
    "label": "Office of the Registrar of Co-operative Societies",
    "display": "Your district office",
    "note": "Society registration, audits, elections and disputes",
}

_INSURANCE = re.compile(r"\b(pmfby|fasal|bima|crop insurance|insurance|claim|crop loss|calamit|rwbcis|weather[-\s]based|upis|premium)\b", re.I)
_PMKISAN = re.compile(r"\b(pm[-\s]?kisan|kisan samman|samman nidhi|installment|instalment|ekyc|e-kyc)\b", re.I)
_COOP = re.compile(r"\b(co-?operative|cooperative|society|societies|pacs|bye-?laws?|byelaws?|registrar|audit|election|member|dividend|sahakar|samiti)\b", re.I)


def helplines_for(question: str, trust_level: str, intent: str = "general", routed_docs=None) -> list:
    """Helplines to show under an answer. Empty for verified answers and refusals,
    unless the question is a complaint / dispute."""
    if trust_level in ("refused", "error", None):
        return []
    complaint = intent == "complaint_or_dispute"
    if trust_level == "verified" and not complaint:
        return []

    text = f"{question or ''} {' '.join(routed_docs or [])}"
    out = []
    if _INSURANCE.search(text) or any(d in ("doc1", "RWBCIS", "UPIS") for d in (routed_docs or [])):
        out.append(KRISHI_RAKSHAK)
    if _PMKISAN.search(text) or "PM-KISAN" in (routed_docs or []):
        out.append(PM_KISAN_HELPDESK)
    if _COOP.search(text) or any(d in ("11of1959", "247816", "Model Byelaws", "Initiatives") for d in (routed_docs or [])):
        out.append(COOP_REGISTRAR)
    out.append(KISAN_CALL_CENTRE)   # always available as a general fallback
    return out
