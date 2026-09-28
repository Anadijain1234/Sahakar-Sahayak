from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pydantic import BaseModel  # ADDED: For strict TTS payload validation

import tempfile
import os
from dotenv import load_dotenv

# Load local .env files if present (safely ignored on Render)
load_dotenv()

# STRICT IMPORT: Pointing exactly to the root file shown in your file explorer
from anadi_voice_engine import convert_audio_to_text, convert_text_to_audio

from backend.models.database import init_db
from backend.routes.auth import router as auth_router

try:
    from backend.routes.query import router as query_router
except ImportError:
    query_router = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables and migrations on startup. If the database can't be
    # reached (e.g. Neon waking up), retry; never stop the whole app from starting --
    # chat and search don't need the database.
    import time as _time
    for _attempt in range(3):
        try:
            init_db()
            print("🗄️ Database tables ready.")
            break
        except Exception as e:
            print(f"⚠️ Database not ready (attempt {_attempt + 1}/3): {e}")
            _time.sleep(3)
    yield


app = FastAPI(lifespan=lifespan)

# Allow requests from the React/Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MOUNT DOCUMENTS FOLDER SO PDF CITATION LINKS ACTUALLY OPEN
try:
    os.makedirs("backend/data/documents", exist_ok=True)
    app.mount("/documents", StaticFiles(directory="backend/data/documents"), name="documents")
except Exception as e:
    print(f"Could not mount documents directory: {e}")


@app.get("/")
def home():
    return {"message": "SAHAKAAR KIOSK backend is running"}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "SAHAKAAR KIOSK backend"
    }


# ----------------------------------------------------
# Authentication Routes
# ----------------------------------------------------
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(auth_router, prefix="/auth", tags=["Authentication (Alias)"])


# ----------------------------------------------------
# Voice Endpoints
# ----------------------------------------------------
@app.post("/voice/transcribe")
async def transcribe_voice(file: UploadFile = File(...), language: str = Form("en")):
    if convert_audio_to_text is None:
        raise HTTPException(
            status_code=503,
            detail="Voice transcription engine is not installed or available on this host."
        )

    temp_path = None
    try:
        suffix = os.path.splitext(file.filename or ".webm")[1]

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix
        ) as temp_file:
            temp_file.write(await file.read())
            temp_path = temp_file.name

        # Pass the dynamic language from the frontend into the Voice Engine
        text, detected_language = convert_audio_to_text(temp_path, language)

        return {
            "text": text,
            "language": detected_language
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Voice transcription failed: {str(e)}"
        )

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


# ADDED: Pydantic Model to perfectly catch the React JSON payload
class TTSRequest(BaseModel):
    text: str
    language: str = "en"

@app.post("/voice/speak")
async def speak_voice(request: TTSRequest):
    if convert_text_to_audio is None:
        raise HTTPException(
            status_code=503,
            detail="Voice synthesis engine is not installed or available on this host."
        )

    try:
        text = request.text
        language = request.language

        if not text.strip():
            raise HTTPException(
                status_code=400,
                detail="Text cannot be empty"
            )

        # Pass the dynamic language into the Voice Engine (Logs will auto-generate here)
        audio_base64 = convert_text_to_audio(
            text,
            language
        )

        if not audio_base64:
            raise HTTPException(
                status_code=500,
                detail="TTS failed across all fallback tiers"
            )

        return {
            "audio": audio_base64,
            "language": language
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Voice synthesis failed: {str(e)}"
        )


# Live accuracy scoreboard page (/scoreboard) -- runs evaluate_rag.py on the server
try:
    from backend.routes.scoreboard import router as scoreboard_router
    app.include_router(scoreboard_router)
except Exception as e:
    print(f"Scoreboard page not available: {e}")

# Admin insights page (/insights?key=...) -- what farmers are asking
try:
    from backend.routes.insights import router as insights_router
    app.include_router(insights_router)
except Exception as e:
    print(f"Insights page not available: {e}")

# KEEP THIS AT THE VERY END
if query_router is not None:
    app.include_router(query_router)