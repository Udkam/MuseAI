from loguru import logger

from app.application.ports.prompt_gateway import PromptGateway
from app.infra.providers.tts.base import BaseTTSProvider, TTSConfig

VOICE_DESCRIPTION_KEY = "__voice_description__"
VOICE_KEY = "__voice__"
DEFAULT_TTS_VOICE = "冰糖"
DEFAULT_TTS_STYLE = (
    "只朗读给定文本，不要补充任何内容。"
    "固定使用“冰糖”美少女声线，声音清甜、明亮、自然、年轻。"
    "不要使用男声、低沉声线或中年感声线。"
    "语速正常偏快，句间停顿短，尾音不要拖长。"
)


def extract_voice_description(variables: list[dict[str, str]]) -> str | None:
    """Extract voice_description from the variables metadata list."""
    for var in variables:
        if var.get("name") == VOICE_DESCRIPTION_KEY:
            return var.get("description", "")
    return None


def extract_voice(variables: list[dict[str, str]]) -> str | None:
    """Extract preset voice name from the variables metadata list."""
    for var in variables:
        if var.get("name") == VOICE_KEY:
            return var.get("description", "")
    return None


def store_voice_description(
    variables: list[dict[str, str]], voice_description: str
) -> list[dict[str, str]]:
    """Store voice_description in the variables metadata list."""
    cleaned = [v for v in variables if v.get("name") != VOICE_DESCRIPTION_KEY]
    if voice_description:
        cleaned.append({"name": VOICE_DESCRIPTION_KEY, "description": voice_description})
    return cleaned


class TTSService:
    def __init__(self, provider: BaseTTSProvider, prompt_gateway: PromptGateway):
        self.provider = provider
        self.prompt_gateway = prompt_gateway

    def get_qa_tts_config(self, user_voice: str | None = None) -> TTSConfig:
        return TTSConfig(
            voice=DEFAULT_TTS_VOICE,
            style=DEFAULT_TTS_STYLE,
        )

    async def get_tour_tts_config(self, persona: str) -> TTSConfig:
        prompt_key = f"tour_tts_persona_{persona.lower()}"
        prompt = await self.prompt_gateway.get_entity(prompt_key)
        if prompt:
            logger.debug(f"TTS prompt found: key={prompt_key}, variables={prompt.variables}")
        else:
            logger.warning(f"TTS prompt NOT found: key={prompt_key}")
        prompt_voice = extract_voice(prompt.variables) if prompt else None
        final_voice = DEFAULT_TTS_VOICE
        logger.debug(
            "TTS config: persona={}, prompt_key={}, prompt_voice={}, final_voice={}, style=fixed_default",
            persona,
            prompt_key,
            prompt_voice,
            final_voice,
        )
        return TTSConfig(
            voice=final_voice,
            style=DEFAULT_TTS_STYLE,
        )
