from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

import tempfile
import os
from dotenv import load_dotenv

# Load local .env files if present (safely ignored on Render)
load_dotenv()

# Note: The broken genai/Sarvam config block has been completely removed.
# LLM configuration is now handled safely inside backend/services/rag_service.py.

# Safe import for voice engine
try:
    from anadi_voice_engine import (
        convert_audio_to_text,
        convert_text_to_audio
    )
except ImportError:
    try:
        # Fallback in case your engine is inside the services folder
        from backend.services.voice_engine import convert_audio_to_text, convert_text_to_audio
    except ImportError:
        convert_audio_to_text = None
        convert_text_to_audio = None

from backend.models.database import init_db
from backend.routes.auth import router as auth_router

try:
    from backend.routes.query import router as query_router
except ImportError:
    query_router = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables and migrations on startup
    init_db()
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


@app.post("/voice/speak")
async def speak_voice(data: dict):
    if convert_text_to_audio is None:
        raise HTTPException(
            status_code=503,
            detail="Voice synthesis engine is not installed or available on this host."
        )

    try:
        text = data.get("text", "")
        # Safely extracts the language chosen on the frontend UI
        language = data.get("language", "en")

        if not text.strip():
            raise HTTPException(
                status_code=400,
                detail="Text cannot be empty"
            )

        # Pass the dynamic language into the Voice Engine
        audio_base64 = convert_text_to_audio(
            text,
            language
        )

        if not audio_base64:
            raise HTTPException(
                status_code=500,
                detail="TTS failed"
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


# KEEP THIS AT THE VERY END
if query_router is not None:
    app.include_router(query_router)