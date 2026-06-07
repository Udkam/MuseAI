import base64

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.application.tts_service import DEFAULT_TTS_VOICE
from app.infra.providers.tts.base import TTSConfig

router = APIRouter(prefix="/tts", tags=["tts"])


class SynthesizeRequest(BaseModel):
    text: str
    voice: str | None = DEFAULT_TTS_VOICE
    style: str | None = None
    persona: str | None = None


class SynthesizeResponse(BaseModel):
    audio: str  # base64-encoded WAV audio
    format: str = "wav"


def _get_tts_service(request: Request):
    return getattr(request.app.state, "tts_service", None)


@router.post("/synthesize", response_model=SynthesizeResponse)
async def synthesize_tts(body: SynthesizeRequest, request: Request):
    tts_service = _get_tts_service(request)
    if tts_service is None:
        raise HTTPException(
            status_code=503,
            detail="TTS service not available. Check TTS_ENABLED and TTS_API_KEY in server config.",
        )

    if body.persona:
        config = await tts_service.get_tour_tts_config(body.persona)
        if body.style:
            base_style = config.style or ""
            config.style = (base_style + "\n" + body.style).strip()
    else:
        config = TTSConfig(voice=DEFAULT_TTS_VOICE, style=body.style)
    try:
        audio_bytes = await tts_service.provider.synthesize(body.text, config)
        audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
    except Exception:
        raise HTTPException(status_code=502, detail="TTS synthesis failed") from None

    return SynthesizeResponse(
        audio=audio_b64,
        format="wav",
    )
