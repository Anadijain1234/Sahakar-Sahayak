import speech_recognition as sr
from gtts import gTTS
import os
import base64
import requests
from pydub import AudioSegment

print("Loading Multilingual Voice Engine (Bhashini Primary + Google Fallback)...")

BHASHINI_USER_ID = os.getenv("BHASHINI_USER_ID", "455ebbb51e-8be8-41c7-b1c4-97139e071887")
BHASHINI_API_KEY = os.getenv("BHASHINI_API_KEY", "GNSK-fU7d1X0zBT20yFRch9YBUCeZ93goVEcN1LcC1cWND_oI2FGQLqjpv6g0nEM")
BHASHINI_URL = "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"

def get_google_lang_code(lang_code):
    """Maps frontend dropdown codes to Google's exact STT regional codes."""
    mapping = {
        "en": "en-IN",
        "hi": "hi-IN",
        "kn": "kn-IN"
    }
    return mapping.get(lang_code, "en-IN")

def convert_audio_to_text(audio_file_path, lang_code="en"):
    """
    Takes audio, converts to text. 
    Automatically switches language dynamically based on the frontend dropdown.
    """
    recognizer = sr.Recognizer()
    wav_path = "temp_converted.wav"
    safe_lang = lang_code if lang_code in ["en", "hi", "kn"] else "en"
    google_lang = get_google_lang_code(safe_lang)
    
    try:
        audio = AudioSegment.from_file(audio_file_path)
        audio.export(wav_path, format="wav")
        
        # --- 1. ATTEMPT BHASHINI ASR FIRST ---
        try:
            with open(wav_path, "rb") as f:
                audio_base64 = base64.b64encode(f.read()).decode("utf-8")
            
            headers = {
                "Authorization": BHASHINI_API_KEY,
                "Content-Type": "application/json"
            }
            payload = {
                "pipelineTasks": [{"taskType": "asr", "config": {"language": {"sourceLanguage": safe_lang}}}],
                "inputData": {"audio": [{"audioContent": audio_base64}]}
            }
            
            response = requests.post(BHASHINI_URL, headers=headers, json=payload, timeout=8)
            if response.status_code == 200:
                data = response.json()
                bhashini_text = data["pipelineResponse"][0]["output"][0]["source"]
                if os.path.exists(wav_path): os.remove(wav_path)
                return bhashini_text, safe_lang
        except Exception as e:
            print("Bhashini ASR fallback triggered:", str(e))
            pass 
        
        # --- 2. GOOGLE FALLBACK (Dynamically matches language!) ---
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            
        # Dynamically passes en-IN, hi-IN, or kn-IN based on your UI selection
        text = recognizer.recognize_google(audio_data, language=google_lang)
        
        if os.path.exists(wav_path):
            os.remove(wav_path)
            
        return text.strip(), safe_lang
        
    except sr.UnknownValueError:
        if os.path.exists(wav_path): os.remove(wav_path)
        error_msg = {
            "en": "Sorry, I could not understand the audio.",
            "hi": "मुझे आपकी आवाज़ साफ़ सुनाई नहीं दी।",
            "kn": "ಕ್ಷಮಿಸಿ, ಆಡಿಯೋ ಅರ್ಥವಾಗಲಿಲ್ಲ."
        }
        return error_msg.get(safe_lang, "Audio unclear"), safe_lang
    except Exception as e:
        if os.path.exists(wav_path): os.remove(wav_path)
        return f"STT Error: {str(e)}", safe_lang


def convert_text_to_audio(text_string, lang_code="en"):
    """
    Converts LLM text back to spoken audio in the correct language.
    """
    try:
        safe_lang = lang_code if lang_code in ["en", "hi", "kn"] else "en"
        
        # --- 1. ATTEMPT BHASHINI TTS FIRST ---
        try:
            headers = {
                "Authorization": BHASHINI_API_KEY,
                "Content-Type": "application/json"
            }
            payload = {
                "pipelineTasks": [{"taskType": "tts", "config": {"language": {"sourceLanguage": safe_lang}}}],
                "inputData": {"input": [{"source": text_string}]}
            }
            
            response = requests.post(BHASHINI_URL, headers=headers, json=payload, timeout=8)
            if response.status_code == 200:
                data = response.json()
                bhashini_audio_base64 = data["pipelineResponse"][0]["audio"][0]["audioContent"]
                return bhashini_audio_base64
        except Exception as e:
            print("Bhashini TTS fallback triggered:", str(e))
            pass
        
        # --- 2. GOOGLE FALLBACK (Dynamically matches language!) ---
        tts = gTTS(text=text_string, lang=safe_lang, slow=False)
        temp_filename = "server_response.mp3"
        tts.save(temp_filename)
        
        with open(temp_filename, "rb") as audio_file:
            encoded_audio = base64.b64encode(audio_file.read()).decode('utf-8')
            
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
            
        return encoded_audio
        
    except Exception as e:
        print(f"TTS Error: {str(e)}")
        return None