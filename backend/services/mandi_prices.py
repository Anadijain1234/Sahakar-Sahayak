"""
Mandi prices -- the latest Karnataka crop prices, shown ONLY when someone asks for a price
("tomato bhav Kolar mandi?", "onion rate today?", "ಈರುಳ್ಳಿ ಬೆಲೆ ಎಷ್ಟು?").

Where the prices come from
  The prices are official AGMARKNET data (Ministry of Agriculture, Govt. of India, published on
  data.gov.in). The government site is slow, so we don't call it while a farmer waits. Instead we
  read a small file (live.json) that a free GitHub robot refreshes every hour:
      https://github.com/Sheethal00/karnataka-mandi-rates   (not a government project -- credited)
  Set MANDI_PRICES_URL in Render to use a different copy of that file. No API key is needed.

How it works
  1. Is this a price question?  A price word (price / rate / bhav / ಬೆಲೆ / दाम ...) + a crop or
     mandi word, and NOT about schemes, PM-Kisan, MSP, loans, interest, insurance, subsidy ...
     Every other question gets nothing from this file -- the answer works exactly as before.
  2. Read live.json (kept in memory for 30 minutes).
  3. Pick the crop's rows: the market / district the farmer named first, otherwise any Karnataka market.
  4. Prices older than 7 days are not shown -- only the official AGMARKNET link.

It never breaks an answer: file missing, internet down, unknown crop -> just the AGMARKNET link.
"""

import os
import re
import time
import threading
from datetime import datetime, timedelta, timezone

import requests

from backend.services.reqlog import log

DEFAULT_URLS = [
    "https://raw.githubusercontent.com/Sheethal00/karnataka-mandi-rates/main/data/live.json",
    "https://sheethal00.github.io/karnataka-mandi-rates/data/live.json",
]
AGMARKNET = {"label": "AGMARKNET (Govt. of India)", "url": "https://agmarknet.gov.in/"}
COLLECTED_BY = {"label": "GitHub: karnataka-mandi-rates", "url": "https://github.com/Sheethal00/karnataka-mandi-rates"}
TIMEOUT = 6                 # seconds to wait for the file
CACHE_SECONDS = 30 * 60     # read the file at most once every 30 minutes
MAX_AGE_DAYS = 7            # older prices are not shown
MAX_ROWS = 6
IST = timezone(timedelta(hours=5, minutes=30))

# Official AGMARKNET crop names -> words a farmer may use (English / Hindi / Kannada, any script)
COMMODITIES = {
    "Onion": ["onion", "onions", "pyaz", "pyaaz", "piyaz", "kanda", "eerulli", "erulli", "ಈರುಳ್ಳಿ", "प्याज", "प्याज़"],
    "Tomato": ["tomato", "tomatoes", "tamatar", "tamaatar", "ಟೊಮೆಟೊ", "ಟೊಮ್ಯಾಟೊ", "ಟೊಮೇಟೊ", "टमाटर"],
    "Potato": ["potato", "potatoes", "aloo", "aalu", "ಆಲೂಗಡ್ಡೆ", "आलू"],
    "Wheat": ["wheat", "gehu", "gehun", "gehoon", "ಗೋಧಿ", "गेहूं", "गेहूँ", "गेहू"],
    "Paddy(Common)": ["paddy", "dhaan", "bhatta", "ಭತ್ತ", "धान"],
    "Rice": ["rice", "chawal", "akki", "ಅಕ್ಕಿ", "चावल"],
    "Maize": ["maize", "corn", "makka", "makkai", "makai", "mekkejola", "ಮೆಕ್ಕೆಜೋಳ", "मक्का"],
    "Ragi(Finger Millet)": ["ragi", "nachni", "mandua", "ರಾಗಿ", "रागी"],
    "Jowar(Sorghum)": ["jowar", "jola", "sorghum", "ಜೋಳ", "ज्वार"],
    "Bajra(Pearl Millet/Cumbu)": ["bajra", "sajje", "pearl millet", "ಸಜ್ಜೆ", "बाजरा"],
    "Red gram/Arhar/Tur(whole)": ["tur", "toor", "arhar", "togari", "thogari", "red gram", "ತೊಗರಿ", "अरहर", "तुअर", "तूर"],
    "Bengal Gram(Gram)(Whole)": ["chana", "channa", "bengal gram", "kadale", "ಕಡಲೆ", "चना"],
    "Green Gram(Moong)(Whole)": ["moong", "mung", "green gram", "hesaru", "ಹೆಸರು", "मूंग"],
    "Black Gram(Urd Beans)(Whole)": ["urad", "urd", "black gram", "uddu", "ಉದ್ದು", "उड़द", "उडद"],
    "Cotton": ["cotton", "kapas", "hatti", "ಹತ್ತಿ", "कपास"],
    "Groundnut": ["groundnut", "peanut", "moongphali", "mungfali", "shenga", "kadalekayi", "ಶೇಂಗಾ", "ಕಡಲೆಕಾಯಿ", "मूंगफली"],
    "Soyabean": ["soybean", "soyabean", "soya", "ಸೋಯಾ", "सोयाबीन"],
    "Dry Chillies": ["dry chilli", "dry chillies", "red chilli", "chilli", "chillies", "chili", "mirchi", "menasinakayi", "ಮೆಣಸಿನಕಾಯಿ", "मिर्च"],
    "Green Chilli": ["green chilli", "hari mirch", "hasi menasinakayi"],
    "Banana": ["banana", "bananas", "kela", "bale hannu", "ಬಾಳೆ", "केला"],
    "Arecanut(Betelnut/Supari)": ["arecanut", "areca", "supari", "adike", "ಅಡಿಕೆ", "सुपारी"],
    "Coconut": ["coconut", "nariyal", "tengina kayi", "ತೆಂಗಿನಕಾಯಿ", "नारियल"],
    "Garlic": ["garlic", "lahsun", "lehsun", "bellulli", "ಬೆಳ್ಳುಳ್ಳಿ", "लहसुन"],
    "Turmeric": ["turmeric", "haldi", "arishina", "ಅರಿಶಿನ", "हल्दी"],
    "Ginger(Green)": ["ginger", "adrak", "shunti", "ಶುಂಠಿ", "अदरक"],
    "Brinjal": ["brinjal", "baingan", "eggplant", "badane", "ಬದನೆ", "बैंगन"],
    "Cabbage": ["cabbage", "patta gobhi", "patta gobi", "kosu", "ಎಲೆಕೋಸು", "पत्ता गोभी"],
    "Cauliflower": ["cauliflower", "phool gobhi", "phool gobi", "gobi", "ಹೂಕೋಸು", "फूलगोभी", "फूल गोभी"],
    "Beans": ["beans", "hurali", "ಬೀನ್ಸ್", "बीन्स"],
    "Carrot": ["carrot", "gajar", "ಕ್ಯಾರೆಟ್", "गाजर"],
    "Ladies Finger": ["ladies finger", "lady finger", "okra", "bhindi", "bende", "ಬೆಂಡೆ", "भिंडी"],
    "Mustard": ["mustard", "sarson", "sasive", "ಸಾಸಿವೆ", "सरसों"],
    "Sunflower/Sunflower Seed": ["sunflower", "surajmukhi", "suryakanti", "ಸೂರ್ಯಕಾಂತಿ", "सूरजमुखी"],
    "Pomegranate": ["pomegranate", "anar", "dalimbe", "ದಾಳಿಂಬೆ", "अनार"],
    "Grapes": ["grapes", "grape", "angoor", "angur", "drakshi", "ದ್ರಾಕ್ಷಿ", "अंगूर"],
    "Copra": ["copra", "kobbari", "ಕೊಬ್ಬರಿ", "खोपरा"],
}
# Other official names for the same crop (Karnataka markets use some of these)
ALTERNATE_NAMES = {
    "Paddy(Common)": ["Paddy(Dhan)(Common)"],
    "Red gram/Arhar/Tur(whole)": ["Arhar (Tur/Red Gram)(Whole)", "Red gram split/Arhar dal/Tur dal"],
    "Groundnut": ["Ground Nut Seed"],
    "Soyabean": ["Soybean"],
    "Bajra(Pearl Millet/Cumbu)": ["Sajje"],
    "Banana": ["Banana - Green"],
    "Beans": ["Bunch Beans"],
}
PLACE_ALIASES = {"bangalore": "bengaluru", "belgaum": "belagavi", "mysore": "mysuru", "gulbarga": "kalaburagi",
                 "hubli": "hubballi", "shimoga": "shivamogga", "bijapur": "vijayapura", "bellary": "ballari",
                 "tumkur": "tumakuru", "mangalore": "mangaluru", "chikmagalur": "chikkamagaluru"}

_PRICE_WORDS = re.compile(
    r"(\bprices?\b|\brates?\b|\bbhav\b|\bbhaav\b|\bdaam\b|\bkeemat\b|\bkimat\b|\bbele\b|\bdhara\b"
    r"|ಬೆಲೆ|ದರ|दाम|भाव|कीमत|रेट)", re.I)
_MARKET_WORDS = re.compile(r"(\bmandi\b|\bmarket\b|\bapmc\b|ಮಾರುಕಟ್ಟೆ|मंडी)", re.I)
# Scheme / MSP / money questions are NOT market-price questions -> nothing is added to them
_NOT_PRICE = re.compile(
    r"(\bmsp\b|support price|minimum support|pm[\s-]*kisan|kisan samman|yojana|scheme|premium|interest|insurance"
    r"|\bbima\b|\bbeema\b|\bvime\b|loan|subsidy|claim|\bkcc\b|credit card|byaj|pension|\bseeds?\b|fertili[sz]er"
    r"|\burea\b|\bdap\b|pesticide|tractor|stamp duty|\bfees?\b|\bshare\b"
    r"|समर्थन मूल्य|एमएसपी|योजना|ब्याज|बीमा|ऋण|सब्सिडी|किसान सम्मान"
    r"|ಬೆಂಬಲ ಬೆಲೆ|ಯೋಜನೆ|ವಿಮೆ|ಸಾಲ|ಬಡ್ಡಿ|ಸಬ್ಸಿಡಿ)", re.I)

_cache = {"at": 0.0, "records": None}
_lock = threading.Lock()


def _find_commodity(text):
    low = f" {text.lower()} "
    best = None
    for name, words in COMMODITIES.items():
        for w in words:
            wl = w.lower()
            hit = (wl in low) if not wl.isascii() else re.search(rf"(?<![a-z]){re.escape(wl)}(?![a-z])", low)
            if hit and (best is None or len(wl) > best[1]):
                best = (name, len(wl))          # longest match wins ("green chilli" over "chilli")
    return best[0] if best else None


def is_price_question(text):
    """True only when a price is really asked: a price word + a crop or mandi word,
    and nothing about schemes / MSP / loans / insurance / interest / subsidy."""
    if not text or not _PRICE_WORDS.search(text) or _NOT_PRICE.search(text):
        return False
    return bool(_find_commodity(text) or _MARKET_WORDS.search(text))


def _urls():
    own = os.getenv("MANDI_PRICES_URL", "").strip()
    return [own] if own else DEFAULT_URLS


def _load_records():
    """All rows of live.json, from memory if read in the last 30 minutes."""
    with _lock:
        if _cache["records"] is not None and time.time() - _cache["at"] < CACHE_SECONDS:
            return _cache["records"]
    last_error = None
    for url in _urls():
        try:
            resp = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "SahakarSahayak/1.0"})
            resp.raise_for_status()
            data = resp.json()
            records = data.get("records") if isinstance(data, dict) else data
            if not isinstance(records, list):
                raise ValueError("file has no 'records' list")
            with _lock:
                _cache.update(at=time.time(), records=records)
            return records
        except Exception as e:           # try the next copy of the file
            last_error = e
    with _lock:
        if _cache["records"] is not None:  # keep using the last good copy
            return _cache["records"]
    raise RuntimeError(f"price file not reachable ({str(last_error)[:120]})")


def _date(d):
    """'25/09/2026' -> date(2026, 9, 25); None if unreadable."""
    try:
        dd, mm, yy = str(d).split("/")
        return datetime(int(yy), int(mm), int(dd)).date()
    except (ValueError, TypeError):
        return None


def _num(x):
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _pick(records, text):
    """Markets the farmer named first; otherwise all markets (alphabetical)."""
    low = text.lower()
    for a, b in PLACE_ALIASES.items():
        low = low.replace(a, b)

    def named(r):
        for field in ("market", "district"):
            v = str(r.get(field, "")).lower().replace(" apmc", "").replace("apmc ", "").strip()
            if len(v) > 3 and v in low:
                return 2 if field == "market" else 1
        return 0
    scored = sorted(records, key=lambda r: (-named(r), str(r.get("market", ""))))
    matched = bool(scored) and named(scored[0]) > 0
    rows = [r for r in scored if named(r)] if matched else scored
    return rows[:MAX_ROWS], matched


def lookup(original_question, english_question=""):
    """None for every non-price question (nothing is added to the answer).
    For price questions: {"commodity", "records", "date", "place_matched", "status", "source_url", "via_url", "links"}.
    status: ok | too_old | no_data | unknown_crop | unavailable"""
    text = f"{original_question or ''} {english_question or ''}"
    if not is_price_question(text):
        return None
    commodity = _find_commodity(text)
    out = {"commodity": commodity, "records": [], "date": None, "place_matched": False, "status": "no_data",
           "source_url": AGMARKNET["url"], "via_url": COLLECTED_BY["url"], "links": [AGMARKNET]}
    if not commodity:
        out["status"] = "unknown_crop"
        log("PRICES", "📈 price question, but no crop name recognised -- showing the AGMARKNET link")
        return out
    t0 = time.perf_counter()
    try:
        records = _load_records()
    except Exception as e:
        out["status"] = "unavailable"
        log("PRICES", f"⚠️ {e} -- showing the AGMARKNET link")
        return out
    names = {commodity.lower()} | {n.lower() for n in ALTERNATE_NAMES.get(commodity, [])}
    crop_rows = [r for r in records if str(r.get("commodity", "")).strip().lower() in names]
    today = datetime.now(IST).date()
    fresh = [r for r in crop_rows if _date(r.get("arrival_date")) and (today - _date(r["arrival_date"])).days <= MAX_AGE_DAYS]
    if crop_rows and not fresh:
        out["status"] = "too_old"
        log("PRICES", f"📈 {commodity}: prices are older than {MAX_AGE_DAYS} days -- showing the AGMARKNET link")
        return out
    rows, matched = _pick(fresh, text)
    out["records"] = [{
        "market": r.get("market"), "district": r.get("district"), "state": r.get("state"),
        "variety": r.get("variety"), "min_price": _num(r.get("min_price")),
        "max_price": _num(r.get("max_price")), "modal_price": _num(r.get("modal_price")),
        "date": r.get("arrival_date"),
    } for r in rows]
    dates = [_date(r["date"]) for r in out["records"] if _date(r["date"])]
    out["date"] = max(dates).strftime("%d/%m/%Y") if dates else None
    out["place_matched"] = matched
    out["status"] = "ok" if out["records"] else "no_data"
    log("PRICES", f"📈 {commodity}: {len(fresh)} Karnataka markets, showing {len(out['records'])} "
                  f"({'named place' if matched else 'no place named'}), latest {out['date']}, "
                  f"in {time.perf_counter() - t0:.2f}s")
    return out


def as_context(prices):
    """The extra note the AI reads -- only for price questions (None otherwise)."""
    if not prices:
        return None
    if prices.get("status") != "ok":
        return ("[Mandi prices: not available for this question right now. Say you do not have the latest price "
                "and ask the farmer to check AGMARKNET (agmarknet.gov.in) or the local APMC mandi.]")
    lines = [f"[Mandi prices for {prices['commodity']} -- official AGMARKNET data (Govt. of India), "
             f"latest available date {prices.get('date')}, in rupees per quintal (100 kg), Karnataka markets only"
             + ("" if prices.get("place_matched") else "; if the farmer named a market or district that is not "
                "listed here, say there is no data for it and that these are other Karnataka markets") + "]"]
    for r in prices["records"]:
        if None in (r["min_price"], r["max_price"], r["modal_price"]):
            lines.append(f"- {r['market']} ({r['district']}): price not reported")
        else:
            lines.append(f"- {r['market']} ({r['district']}), {r.get('variety') or ''}, {r.get('date')}: "
                         f"min {r['min_price']:.0f}, max {r['max_price']:.0f}, most common (modal) {r['modal_price']:.0f}")
    lines.append("Give these prices with their date and say that mandi prices change daily.")
    return "\n".join(lines)
