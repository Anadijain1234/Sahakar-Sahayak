import speech_recognition as sr
from gtts import gTTS
import os
import base64
import requests
import uuid
from pydub import AudioSegment
import time  # (added) timings for the [VOICE-IN] / [VOICE-OUT] log lines

print("=======================================================")
print("🎙️ INITIATING TRIPLE-TIER VOICE ENGINE (SARVAM -> BHASHINI -> GOOGLE) 🎙️")
print("=======================================================")

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "").strip()
BHASHINI_USER_ID = os.getenv("BHASHINI_USER_ID", "455ebbb51e-8be8-41c7-b1c4-97139e071887")
BHASHINI_API_KEY = os.getenv("BHASHINI_API_KEY", "GNSK-fU7d1X0zBT20yFRch9YBUCeZ93goVEcN1LcC1cWND_oI2FGQLqjpv6g0nEM")
BHASHINI_URL = "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"

def get_google_lang_code(lang_code):
    """Maps frontend dropdown codes to Google's exact STT regional codes."""
    mapping = {"en": "en-IN", "hi": "hi-IN", "kn": "kn-IN"}
    return mapping.get(lang_code, "en-IN")


# ------------------------------------------------------------------------------
# (added) One-line voice logs. In Render -> Logs, search for:
#   VOICE-IN   who heard the user (speech -> text) and exactly what it heard
#   VOICE-OUT  who read the answer aloud (text -> speech)
#   VOICE      both
# Only these log lines were added; the engines, their order and the keys are unchanged.
# ------------------------------------------------------------------------------
def _vlog(tag, trace_id, message):
    print(f"[{tag} {trace_id}] {message}", flush=True)


def _short(text, limit=200):
    text = " ".join(str(text or "").split())
    return text if len(text) <= limit else text[:limit] + "..."


# ==============================================================================
# SPEECH-TO-TEXT (LISTENING): TRIPLE TIER FALLBACK
# ==============================================================================
def convert_audio_to_text(audio_file_path, lang_code="en"):
    trace_id = str(uuid.uuid4())[:8].upper()
    safe_lang = lang_code if lang_code in ["en", "hi", "kn"] else "en"
    google_lang = get_google_lang_code(safe_lang)
    wav_path = f"temp_stt_{trace_id}.wav"
    
    print(f"\n==================================================================")
    print(f"🎙️ STT INITIATED | Trace ID: {trace_id} | Target Lang: {safe_lang}")
    print(f"==================================================================")
    _t0 = time.perf_counter()
    try:
        _size_kb = round(os.path.getsize(audio_file_path) / 1024)
    except Exception:
        _size_kb = "?"
    _vlog("VOICE-IN", trace_id, f"🎙️ listening started | website language: {lang_code} | audio {_size_kb} KB | order: SARVAM -> BHASHINI -> GOOGLE")

    try:
        audio = AudioSegment.from_file(audio_file_path)
        audio.export(wav_path, format="wav")
    except Exception as e:
        print(f"[SYSTEM] ❌ FATAL ERROR processing audio file: {e}")
        _vlog("VOICE-IN", trace_id, f"💥 could not read the recording ({type(e).__name__}) -- nothing was sent to Sarvam / Bhashini / Google")
        return "", lang_code

    # ----------------------------------------------------------------------
    # TIER 1: SARVAM (Saaras v4 - Handles mixed Hindi+Kannada Native)
    # ----------------------------------------------------------------------
    print(f"\n▶️ [TIER 1] EXECUTING SARVAM STT (Model: saaras:v4 | Auto-Detect)")
    _t = time.perf_counter()
    try:
        url = "https://api.sarvam.ai/speech-to-text"
        headers = {"api-subscription-key": SARVAM_API_KEY}
        with open(wav_path, "rb") as f:
            files = {'file': ('audio.wav', f, 'audio/wav')}
            # 'unknown' forces Sarvam to auto-detect mixed languages mid-sentence
            data = {'model': 'saaras:v4', 'language_code': 'unknown'}
            response = requests.post(url, headers=headers, files=files, data=data, timeout=12)
            
        if response.status_code == 200:
            result = response.json()
            transcript = result.get("transcript", "").strip()
            detected_lang = result.get("language_code", "unknown")
            print(f"✅ [TIER 1 SUCCESS] Request {trace_id} processed.")
            print(f"🎯 RESOLVED BY: SARVAM AI | Detected Lang: {detected_lang} | Text: '{transcript}'")
            _vlog("VOICE-IN", trace_id, f"✅ heard by SARVAM in {time.perf_counter() - _t:.1f}s (total {time.perf_counter() - _t0:.1f}s) | detected: {detected_lang} | text: '{_short(transcript)}'" + ("" if transcript else " | ⚠️ Sarvam heard no words"))
            if os.path.exists(wav_path): os.remove(wav_path)
            return transcript, lang_code
        else:
            print(f"❌ [TIER 1 FAILED] Sarvam Rejected. HTTP {response.status_code}: {response.text}")
            _vlog("VOICE-IN", trace_id, f"❌ SARVAM failed in {time.perf_counter() - _t:.1f}s (HTTP {response.status_code}) -> trying BHASHINI")
    except Exception as e:
        print(f"❌ [TIER 1 FAILED] Sarvam connection error: {e}")
        _vlog("VOICE-IN", trace_id, f"❌ SARVAM failed in {time.perf_counter() - _t:.1f}s ({type(e).__name__}) -> trying BHASHINI")

    # ----------------------------------------------------------------------
    # TIER 2: BHASHINI (Government DPI Fallback)
    # ----------------------------------------------------------------------
    print(f"\n▶️ [TIER 2] EXECUTING BHASHINI STT (Dhruva ASR | Lang: {safe_lang})")
    _t = time.perf_counter()
    try:
        headers = {
            "Authorization": BHASHINI_API_KEY,
            "userID": BHASHINI_USER_ID,
            "Content-Type": "application/json"
        }
        with open(wav_path, "rb") as f:
            audio_base64 = base64.b64encode(f.read()).decode("utf-8")
        payload = {
            "pipelineTasks": [{"taskType": "asr", "config": {"language": {"sourceLanguage": safe_lang}}}],
            "inputData": {"audio": [{"audioContent": audio_base64}]}
        }
        response = requests.post(BHASHINI_URL, headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            bhashini_text = response.json()["pipelineResponse"][0]["output"][0]["source"].strip()
            print(f"✅ [TIER 2 SUCCESS] Request {trace_id} processed.")
            print(f"🎯 RESOLVED BY: BHASHINI DHRUVA | Text: '{bhashini_text}'")
            _vlog("VOICE-IN", trace_id, f"✅ heard by BHASHINI in {time.perf_counter() - _t:.1f}s (total {time.perf_counter() - _t0:.1f}s) | language: {safe_lang} | text: '{_short(bhashini_text)}'")
            if os.path.exists(wav_path): os.remove(wav_path)
            return bhashini_text, safe_lang
        else:
            print(f"❌ [TIER 2 FAILED] Bhashini Rejected. HTTP {response.status_code}: {response.text}")
            _vlog("VOICE-IN", trace_id, f"❌ BHASHINI failed in {time.perf_counter() - _t:.1f}s (HTTP {response.status_code}) -> trying GOOGLE")
    except Exception as e:
        print(f"❌ [TIER 2 FAILED] Bhashini connection error: {e}")
        _vlog("VOICE-IN", trace_id, f"❌ BHASHINI failed in {time.perf_counter() - _t:.1f}s ({type(e).__name__}) -> trying GOOGLE")

    # ----------------------------------------------------------------------
    # TIER 3: GOOGLE (Unbreakable Final Fallback)
    # ----------------------------------------------------------------------
    print(f"\n▶️ [TIER 3] EXECUTING GOOGLE STT (Google Cloud | Lang: {google_lang})")
    _t = time.perf_counter()
    try:
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
        text = recognizer.recognize_google(audio_data, language=google_lang).strip()
        print(f"✅ [TIER 3 SUCCESS] Request {trace_id} processed.")
        print(f"🎯 RESOLVED BY: GOOGLE CLOUD | Text: '{text}'")
        _vlog("VOICE-IN", trace_id, f"✅ heard by GOOGLE in {time.perf_counter() - _t:.1f}s (total {time.perf_counter() - _t0:.1f}s) | language: {google_lang} | text: '{_short(text)}'")
        if os.path.exists(wav_path): os.remove(wav_path)
        return text, safe_lang
    except sr.UnknownValueError:
        print(f"❌ [TIER 3 FAILED] Google could not understand audio noise.")
        _vlog("VOICE-IN", trace_id, f"❌ GOOGLE could not make out any words ({time.perf_counter() - _t:.1f}s)")
    except Exception as e:
        print(f"❌ [TIER 3 FAILED] Google connection error: {e}")
        _vlog("VOICE-IN", trace_id, f"❌ GOOGLE failed in {time.perf_counter() - _t:.1f}s ({type(e).__name__})")

    # ----------------------------------------------------------------------
    # TOTAL FAILURE STATE
    # ----------------------------------------------------------------------
    if os.path.exists(wav_path): os.remove(wav_path)
    print(f"\n💥 [CRITICAL] ALL STT TIERS FAILED FOR REQUEST {trace_id}")
    _vlog("VOICE-IN", trace_id, f"💥 nobody could hear it -- Sarvam, Bhashini and Google all failed (total {time.perf_counter() - _t0:.1f}s); the user gets an empty result")
    return "", safe_lang


# ==============================================================================
# TEXT-TO-SPEECH (SPEAKING): DOUBLE TIER FALLBACK
# ==============================================================================
def convert_text_to_audio(text_string, lang_code="en"):
    trace_id = str(uuid.uuid4())[:8].upper()
    safe_lang = lang_code if lang_code in ["en", "hi", "kn"] else "en"
    
    print(f"\n==================================================================")
    print(f"🗣️ TTS INITIATED | Trace ID: {trace_id} | Target Lang: {safe_lang}")
    print(f"==================================================================")
    _t0 = time.perf_counter()
    _vlog("VOICE-OUT", trace_id, f"🔊 speaking started | language: {safe_lang} | {len(text_string or '')} characters | order: BHASHINI -> GOOGLE")

    # ----------------------------------------------------------------------
    # TIER 1: BHASHINI (Primary - Free & High Quality Native Voice)
    # ----------------------------------------------------------------------
    print(f"\n▶️ [TIER 1] EXECUTING BHASHINI TTS (Dhruva TTS | Lang: {safe_lang})")
    _t = time.perf_counter()
    try:
        headers = {
            "Authorization": BHASHINI_API_KEY,
            "userID": BHASHINI_USER_ID,
            "Content-Type": "application/json"
        }
        # Added explicit 'gender': 'female' parameter for persona consistency
        payload = {
            "pipelineTasks": [{"taskType": "tts", "config": {"language": {"sourceLanguage": safe_lang}, "gender": "female"}}],
            "inputData": {"input": [{"source": text_string}]}
        }
        response = requests.post(BHASHINI_URL, headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            bhashini_audio_base64 = response.json()["pipelineResponse"][0]["audio"][0]["audioContent"]
            print(f"✅ [TIER 1 SUCCESS] Request {trace_id} processed.")
            print(f"🎯 RESOLVED BY: BHASHINI DHRUVA TTS")
            _vlog("VOICE-OUT", trace_id, f"✅ spoken by BHASHINI in {time.perf_counter() - _t:.1f}s")
            return bhashini_audio_base64
        else:
            print(f"❌ [TIER 1 FAILED] Bhashini Rejected. HTTP {response.status_code}: {response.text}")
            _vlog("VOICE-OUT", trace_id, f"❌ BHASHINI failed in {time.perf_counter() - _t:.1f}s (HTTP {response.status_code}) -> trying GOOGLE")
    except Exception as e:
        print(f"❌ [TIER 1 FAILED] Bhashini connection error: {e}")
        _vlog("VOICE-OUT", trace_id, f"❌ BHASHINI failed in {time.perf_counter() - _t:.1f}s ({type(e).__name__}) -> trying GOOGLE")

    # ----------------------------------------------------------------------
    # TIER 2: GOOGLE (Unbreakable Final Fallback)
    # ----------------------------------------------------------------------
    print(f"\n▶️ [TIER 2] EXECUTING GOOGLE TTS (gTTS Fallback | Lang: {safe_lang})")
    _t = time.perf_counter()
    temp_filename = f"temp_tts_{trace_id}.mp3"
    try:
        tts = gTTS(text=text_string, lang=safe_lang, slow=False)
        tts.save(temp_filename)
        with open(temp_filename, "rb") as audio_file:
            encoded_audio = base64.b64encode(audio_file.read()).decode('utf-8')
        if os.path.exists(temp_filename): os.remove(temp_filename)
            
        print(f"✅ [TIER 2 SUCCESS] Request {trace_id} processed.")
        print(f"🎯 RESOLVED BY: GOOGLE gTTS")
        _vlog("VOICE-OUT", trace_id, f"✅ spoken by GOOGLE in {time.perf_counter() - _t:.1f}s (total {time.perf_counter() - _t0:.1f}s)")
        return encoded_audio
    except Exception as e:
        print(f"❌ [TIER 2 FAILED] Google TTS error: {e}")
        _vlog("VOICE-OUT", trace_id, f"❌ GOOGLE failed in {time.perf_counter() - _t:.1f}s ({type(e).__name__})")
        if os.path.exists(temp_filename): os.remove(temp_filename)
        
        print(f"\n💥 [CRITICAL] ALL TTS TIERS FAILED FOR REQUEST {trace_id}")
        _vlog("VOICE-OUT", trace_id, "💥 nobody could read it aloud -- Bhashini and Google both failed; no audio is played")
        return None