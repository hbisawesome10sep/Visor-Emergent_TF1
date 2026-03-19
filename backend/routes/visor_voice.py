"""
Visor AI — Voice Chat Endpoint
Accepts audio input, transcribes via ElevenLabs STT, processes through
the shared Visor AI engine, converts response to speech via ElevenLabs TTS.
"""
import io
import base64
import logging
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from auth import get_current_user
from config import ELEVENLABS_API_KEY
from services.visor_engine import process_visor_message

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

# ElevenLabs config
VISOR_VOICE_ID = "onwK4e9ZLuTAKqWW03F9"  # Daniel — Steady Broadcaster (professional, calm)
TTS_MODEL = "eleven_multilingual_v2"
STT_MODEL = "scribe_v1"


def _get_eleven_client():
    from elevenlabs import ElevenLabs
    return ElevenLabs(api_key=ELEVENLABS_API_KEY)


@router.post("/visor-ai/voice-chat")
async def visor_voice_chat(
    audio_file: UploadFile = File(...),
    screen_context: str = Form(None),
    user=Depends(get_current_user),
):
    """Voice conversation endpoint: audio in → text + audio out."""
    if not ELEVENLABS_API_KEY:
        raise HTTPException(status_code=500, detail="ElevenLabs API key not configured")

    user_id = user["id"]
    client = _get_eleven_client()

    # ── Step 1: Speech-to-Text ───────────────────────────────────────
    try:
        audio_content = await audio_file.read()
        if len(audio_content) < 100:
            raise HTTPException(status_code=400, detail="Audio file too small or empty")

        transcription = client.speech_to_text.convert(
            file=io.BytesIO(audio_content),
            model_id=STT_MODEL,
        )
        transcribed_text = transcription.text if hasattr(transcription, 'text') else str(transcription)
        language_detected = getattr(transcription, 'language_code', None) or "auto"
        logger.info(f"STT transcription [{language_detected}]: {transcribed_text[:80]}...")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"STT error: {e}")
        raise HTTPException(status_code=500, detail=f"Speech transcription failed: {str(e)}")

    if not transcribed_text or not transcribed_text.strip():
        raise HTTPException(status_code=400, detail="Could not understand the audio. Please try again.")

    # ── Step 2: Process through Visor AI engine ──────────────────────
    result = await process_visor_message(
        user_id=user_id,
        message=transcribed_text.strip(),
        screen_context=screen_context,
        input_type="voice",
    )

    # ── Step 3: Text-to-Speech ───────────────────────────────────────
    audio_base64 = None
    try:
        from elevenlabs import VoiceSettings
        audio_generator = client.text_to_speech.convert(
            text=result["content"],
            voice_id=VISOR_VOICE_ID,
            model_id=TTS_MODEL,
            voice_settings=VoiceSettings(
                stability=0.6,
                similarity_boost=0.75,
                style=0.3,
                use_speaker_boost=True,
            ),
        )
        audio_data = b""
        for chunk in audio_generator:
            audio_data += chunk

        if audio_data:
            audio_base64 = base64.b64encode(audio_data).decode()
            logger.info(f"TTS generated: {len(audio_data)} bytes")
    except Exception as e:
        logger.error(f"TTS error: {e}")
        # Non-fatal — return text response even if TTS fails

    # ── Step 4: Update AI message with audio metadata ────────────────
    if audio_base64:
        from database import db
        await db.visor_chat.update_one(
            {"id": result["id"]},
            {"$set": {"has_audio": True}},
        )

    return {
        **result,
        "transcribed_text": transcribed_text.strip(),
        "language_detected": language_detected,
        "audio_base64": audio_base64,
    }
