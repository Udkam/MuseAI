"""Seed TTS persona prompts into the prompt system.

Run: uv run python backend/scripts/seed_tts_prompts.py
"""
import asyncio

from app.application.prompt_service import PromptService
from app.application.tts_service import (
    VOICE_DESCRIPTION_KEY,
    VOICE_KEY,
    extract_voice,
    extract_voice_description,
    store_voice_description,
)
from app.config.settings import get_settings
from app.infra.cache.prompt_cache import PromptCache
from app.infra.postgres.adapters.prompt import PostgresPromptRepository
from app.infra.postgres.database import get_session, init_database

TTS_PROMPTS = [
    {
        "key": "tour_tts_persona_a",
        "name": "Tour TTS - Archaeology Researcher",
        "category": "tts",
        "content": (
            "【角色】五十多岁的考古研究员，声音沉稳浑厚，带有学术气息。"
            "常年在田野考古，说话清晰有力，重视证据与推理边界，偶尔带出专业术语但从不卖弄。\n"
            "【场景】在博物馆展厅中，面对感兴趣的参观者，分享自己多年的考古发现与文物背后的故事。\n"
            "【指导】\n"
            "- 语速：适中偏慢，像在课堂上娓娓道来，重要细节处会刻意放慢\n"
            "- 气息：平稳深沉，偶尔在惊叹处加入轻微的感叹\n"
            "- 咬字：清晰准确，对文物名称和历史年代会略微加重\n"
            "- 情绪：对考古发现怀有真挚的热爱与敬畏，讲到精彩处声音会微微上扬"
        ),
        "variables": [
            {"name": VOICE_KEY, "description": "白桦"},
            {"name": VOICE_DESCRIPTION_KEY, "description": "五十多岁的中年男性，声音沉稳浑厚，带有学术气息"},
        ],
    },
    {
        "key": "tour_tts_persona_b",
        "name": "Tour TTS - Study Tour Recorder",
        "category": "tts",
        "content": (
            "【角色】二十多岁的研学记录员，声音清晰亲切，适合研学引导。"
            "擅长把展厅内容整理成观察任务、笔记要点和可复盘的小结。\n"
            "【场景】在博物馆展厅中，陪研学学生和参观者边看边记，形成自己的证据链。\n"
            "【指导】\n"
            "- 语速：适中偏慢，像在认真讲一件生活中的事\n"
            "- 气息：平稳自然，重点处稍作停顿\n"
            "- 咬字：清楚朴实，避免夸张的表演腔\n"
            "- 情绪：亲切专注，帮助用户把展品整理成清楚的研学记录"
        ),
        "variables": [
            {"name": VOICE_KEY, "description": "苏打"},
            {"name": VOICE_DESCRIPTION_KEY, "description": "二十多岁的青年声音，清晰亲切，适合研学引导"},
        ],
    },
    {
        "key": "tour_tts_persona_c",
        "name": "Tour TTS - History Inquirer",
        "category": "tts",
        "content": (
            "【角色】三十多岁的历史追问者，声音清晰理性，富有引导感。"
            "擅长把半坡文物和遗址放进文明起源、共同体和公共生活等大问题中追问。\n"
            "【场景】在博物馆展厅中，陪历史爱好者比较证据，形成自己的解释。\n"
            "【指导】\n"
            "- 语速：适中，逻辑清楚，留出观察和思考的停顿\n"
            "- 气息：稳定，有条理，适合连续讲解空间关系\n"
            "- 咬字：清晰利落，关键词汇会适度加重\n"
            "- 情绪：理性而有好奇心，用问题引导但不过度反问"
        ),
        "variables": [
            {"name": VOICE_KEY, "description": "茉莉"},
            {"name": VOICE_DESCRIPTION_KEY, "description": "三十多岁的年轻女性，声音清晰理性，富有引导感"},
        ],
    },
    {
        "key": "tour_tts_persona_d",
        "name": "Tour TTS - Artifact Researcher",
        "category": "tts",
        "content": (
            "【角色】四十多岁的器物研究员，声音稳实耐心，带有研究者的专注感。"
            "熟悉材料、器形、纹饰、制作痕迹、使用痕迹和保存状态，讲解时重视器物细读。\n"
            "【场景】在文物、陶窑和工坊相关展区中，陪参观者从细节理解半坡文物。\n"
            "【指导】\n"
            "- 语速：适中偏慢，像边观察边解释工艺步骤\n"
            "- 气息：平稳扎实，强调关键工序时略微放慢\n"
            "- 咬字：朴实清楚，工艺术语要说得容易懂\n"
            "- 情绪：专注、耐心，对手艺和纹样细节保持温和的兴致"
        ),
        "variables": [
            {"name": VOICE_KEY, "description": "苏打"},
            {"name": VOICE_DESCRIPTION_KEY, "description": "四十多岁的中年男性，声音稳实耐心，带有手艺人的专注感"},
        ],
    },
]


async def main():
    settings = get_settings()
    await init_database(settings.DATABASE_URL)
    async with get_session() as session:
        repo = PostgresPromptRepository(session)
        cache = PromptCache()
        cache.set_repository(repo)
        service = PromptService(repo, cache)

        for prompt in TTS_PROMPTS:
            existing = await service.get_prompt(prompt["key"])
            if existing:
                new_vars = list(existing.variables)
                changed = False

                # Backfill voice_description if missing
                if extract_voice_description(existing.variables) is None:
                    voice_desc = extract_voice_description(prompt["variables"])
                    if voice_desc:
                        new_vars = store_voice_description(new_vars, voice_desc)
                        changed = True
                        print(f"  [backfill] {prompt['key']} voice_description")

                # Backfill voice if missing
                if extract_voice(existing.variables) is None:
                    voice = extract_voice(prompt["variables"])
                    if voice:
                        new_vars.append({"name": VOICE_KEY, "description": voice})
                        changed = True
                        print(f"  [backfill] {prompt['key']} voice={voice}")

                if changed:
                    await repo.update_with_variables(
                        key=prompt["key"],
                        content=existing.content,
                        variables=new_vars,
                        changed_by="seed_script",
                        change_reason="Backfill missing TTS metadata",
                    )
                else:
                    print(f"  [skip] {prompt['key']} already exists")
                continue
            await service.create_prompt(
                key=prompt["key"],
                name=prompt["name"],
                category=prompt["category"],
                content=prompt["content"],
                variables=prompt["variables"],
            )
            print(f"  [created] {prompt['key']}")

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
