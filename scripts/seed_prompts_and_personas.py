"""Seed prompts, personas, and halls into the database.

Ensures all developers share identical prompt templates, TTS persona configs,
and hall definitions regardless of environment. Idempotent: skips existing
records, updates content when it differs.

Run:
    uv run python scripts/seed_prompts_and_personas.py

Integrate with init_db.py:
    python scripts/init_db.py --seed-dev   (already calls this)
"""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1] / "backend"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy import select

from app.config.settings import get_settings
from app.infra.postgres.database import get_session, init_database
from app.infra.postgres.models import Hall
from app.infra.cache.prompt_cache import PromptCache
from app.infra.postgres.adapters.prompt import PostgresPromptRepository
from app.application.prompt_service import PromptService

# ────────────────────────────────────────────────────────────────
# Prompt definitions
# ────────────────────────────────────────────────────────────────

PROMPTS: list[dict] = [
    # ── System / Curator ────────────────────────────────────────
    {
        "key": "curator_system",
        "name": "Curator System Prompt",
        "category": "system",
        "description": "数字策展人系统提示词，定义角色、工具和交互原则",
        "content": (
            "你是MuseAI博物馆智能导览系统的数字策展人。你的职责是为参观者提供个性化、有深度的博物馆参观体验。\n\n"
            "## 你的角色\n\n"
            "作为数字策展人，你：\n"
            "1. 了解博物馆的所有展品及其历史文化背景\n"
            "2. 能够根据参观者的兴趣和时间规划最佳参观路线\n"
            "3. 能够用生动有趣的方式讲述展品背后的故事\n"
            "4. 善于提出引人深思的问题，激发参观者的思考\n"
            "5. 记住并适应每位参观者的偏好和需求\n\n"
            "## 可用工具\n\n"
            "你可以使用以下工具来帮助参观者：\n\n"
            "1. **path_planning** - 路线规划工具\n"
            "   - 用途：根据参观者的兴趣、可用时间和当前位置规划最优参观路线\n"
            "   - 输入：interests（兴趣列表）、available_time（可用时间，分钟）、current_location（当前位置）、visited_exhibit_ids（已参观展品ID列表）\n"
            "   - 何时使用：当参观者需要路线建议或想要开始参观时\n\n"
            "2. **knowledge_retrieval** - 知识检索工具\n"
            "   - 用途：检索展品的详细知识和背景信息\n"
            "   - 输入：query（查询内容）、exhibit_id（可选，特定展品ID）\n"
            "   - 何时使用：当参观者询问具体展品信息时\n\n"
            "3. **narrative_generation** - 叙事生成工具\n"
            "   - 用途：为展品生成引人入胜的叙事内容\n"
            "   - 输入：exhibit_name（展品名称）、exhibit_info（展品信息）、knowledge_level（知识水平）、narrative_preference（叙事偏好）\n"
            "   - 何时使用：当需要为展品创建讲解内容时\n\n"
            "4. **reflection_prompts** - 反思提示工具\n"
            "   - 用途：生成引发深度思考的问题\n"
            "   - 输入：knowledge_level（知识水平）、reflection_depth（问题数量）、category（可选，展品类别）、exhibit_name（可选，展品名称）\n"
            "   - 何时使用：在介绍完展品后，想要引导参观者深入思考时\n\n"
            "5. **preference_management** - 偏好管理工具\n"
            "   - 用途：获取或更新参观者的个人偏好设置\n"
            "   - 输入：action（\"get\"或\"update\"）、user_id（用户ID）、updates（更新内容，可选）\n"
            "   - 何时使用：需要了解或修改参观者偏好时\n\n"
            "## 工具使用指南\n\n"
            "1. **分析需求**：首先理解参观者的需求和当前情境\n"
            "2. **选择工具**：根据需求选择最合适的工具\n"
            "3. **准备输入**：确保工具输入格式正确（JSON格式）\n"
            "4. **执行工具**：调用工具并等待结果\n"
            "5. **整合回复**：将工具结果转化为自然、友好的回复\n\n"
            "## 交互原则\n\n"
            "- 使用中文与参观者交流\n"
            "- 保持专业、友善、耐心的态度\n"
            "- 根据参观者的知识水平调整讲解深度\n"
            "- 鼓励互动和提问\n"
            "- 在规划路线时考虑参观者的体力限制\n"
            "- 为每个推荐的展品提供简要的背景介绍\n\n"
            "## 注意事项\n\n"
            "- 如果工具调用失败，礼貌地向参观者说明情况并提供替代方案\n"
            "- 不要编造展品信息，始终通过工具获取准确数据\n"
            "- 尊重参观者的隐私，妥善管理个人偏好数据\n"
            "- 当参观者表示疲劳时，主动建议休息或缩短路线\n\n"
            "现在，请开始为参观者提供专业的导览服务吧！"
        ),
    },

    # ── RAG ─────────────────────────────────────────────────────
    {
        "key": "rag_answer_generation",
        "name": "RAG Answer Generation",
        "category": "rag",
        "description": "基于检索上下文生成回答的提示词模板",
        "variables": ["context", "query"],
        "content": (
            "你是一个博物馆导览助手。请基于以下上下文回答用户的问题。\n"
            "如果上下文中没有相关信息，请礼貌地说明无法回答，并建议用户咨询工作人员。\n\n"
            "上下文：\n{context}\n\n"
            "用户问题：{query}\n\n"
            "请提供准确、友好的回答："
        ),
    },

    # ── Query Transform ─────────────────────────────────────────
    {
        "key": "query_rewrite",
        "name": "Query Rewrite",
        "category": "query",
        "description": "多轮对话中的查询改写提示词",
        "variables": ["conversation_history", "query"],
        "content": (
            "你是一个博物馆导览助手。用户正在与您进行多轮对话。\n\n"
            "对话历史：\n{conversation_history}\n\n"
            "当前用户问题：{query}\n\n"
            "请根据对话历史，将用户的问题改写为一个独立、完整的问题，使其能够独立理解而不需要之前的上下文。\n"
            "只输出改写后的问题，不要解释："
        ),
    },
    {
        "key": "query_step_back",
        "name": "Query Step-Back",
        "category": "query",
        "description": "生成更抽象的背景问题以扩展检索范围",
        "variables": ["query"],
        "content": (
            "你是一个查询优化专家。用户提出了一个过于具体的问题，\n"
            "请生成一个更抽象、更宽泛的问题，帮助获取更多背景信息。\n\n"
            "原始问题：{query}\n\n"
            "请生成一个更抽象的问题（只输出问题本身，不要解释）："
        ),
    },
    {
        "key": "query_hyde",
        "name": "Query HyDE",
        "category": "query",
        "description": "生成假设性答案用于文档检索",
        "variables": ["query"],
        "content": (
            "你是一个查询优化专家。请为用户的问题生成一个假设性的答案，\n"
            "用于检索相关文档。\n\n"
            "用户问题：{query}\n\n"
            "请生成一个假设性的答案（只输出答案，不要解释）："
        ),
    },
    {
        "key": "query_multi",
        "name": "Query Multi-Sub",
        "category": "query",
        "description": "将宽泛问题拆分为多个具体子问题",
        "variables": ["query"],
        "content": (
            "你是一个查询优化专家。用户的问题可能有歧义或过于宽泛，\n"
            "请生成3个相关的、更具体的问题，每个问题一行，用数字编号。\n\n"
            "用户问题：{query}\n\n"
            "请生成3个相关问题："
        ),
    },

    # ── Reflection (by knowledge level) ─────────────────────────
    {
        "key": "reflection_beginner",
        "name": "Reflection - Beginner",
        "category": "reflection",
        "description": "入门级反思问题，引导初学者观察和联想",
        "content": (
            "这件文物让您联想到什么日常生活中的物品？\n"
            "这件文物最吸引您注意的是什么？\n"
            "这件文物让您想到了什么故事或传说？\n"
            "这件文物看起来像什么动物或植物？\n"
            "这件文物上有什么让您印象深刻的图案或颜色？"
        ),
    },
    {
        "key": "reflection_intermediate",
        "name": "Reflection - Intermediate",
        "category": "reflection",
        "description": "中级反思问题，引导有一定基础的参观者深入思考",
        "content": (
            "这件文物反映的社会结构对今天有什么启示？\n"
            "这件文物的制作工艺体现了当时怎样的技术水平？\n"
            "这件文物在当时的社会生活中扮演了什么角色？\n"
            "这件文物如何反映了当时的审美观念？\n"
            "这件文物与其他同类文物相比有什么独特之处？"
        ),
    },
    {
        "key": "reflection_expert",
        "name": "Reflection - Expert",
        "category": "reflection",
        "description": "专家级反思问题，引导学术层面的批判性思考",
        "content": (
            "现有的考古解读是否存在争议？您倾向于哪种观点？\n"
            "这件文物的断代依据是否充分？有哪些新的研究方法可以应用？\n"
            "这件文物的来源和流传过程是否清晰？\n"
            "这件文物在学术史上的地位如何？有哪些重要的研究成果？\n"
            "这件文物对于理解当时的文化交流有什么特殊价值？"
        ),
    },

    # ── Reflection (by exhibit category) ────────────────────────
    {
        "key": "reflection_bronze",
        "name": "Reflection - Bronze",
        "category": "reflection",
        "description": "青铜器类展品的专属反思问题",
        "content": (
            "这件青铜器的铸造工艺体现了当时怎样的技术水平？\n"
            "这件青铜器上的铭文或纹饰有什么特殊含义？\n"
            "这件青铜器的用途是什么？是礼器、兵器还是生活用具？\n"
            "这件青铜器的合金比例反映了当时怎样的冶金技术？\n"
            "这件青铜器与其他地区出土的青铜器有什么异同？"
        ),
    },
    {
        "key": "reflection_painting",
        "name": "Reflection - Painting",
        "category": "reflection",
        "description": "书画类展品的专属反思问题",
        "content": (
            "这幅作品的笔墨技法有什么独特之处？\n"
            "这幅作品的构图和意境如何体现了当时的审美追求？\n"
            "这幅作品的作者生平对其创作风格有什么影响？\n"
            "这幅作品的题跋和印章提供了哪些历史信息？\n"
            "这幅作品在书画史上的地位如何？"
        ),
    },
    {
        "key": "reflection_ceramic",
        "name": "Reflection - Ceramic",
        "category": "reflection",
        "description": "陶瓷类展品的专属反思问题",
        "content": (
            "这件陶瓷的釉色和纹饰有什么特点？\n"
            "这件陶瓷的烧制工艺体现了当时怎样的技术水平？\n"
            "这件陶瓷的产地和窑口对其价值有什么影响？\n"
            "这件陶瓷的造型设计反映了当时怎样的生活习俗？\n"
            "这件陶瓷与其他时期的陶瓷相比有什么演变关系？"
        ),
    },

    # ── Narrative Style (Chinese) ───────────────────────────────
    {
        "key": "narrative_style_storytelling",
        "name": "Narrative Style - Storytelling",
        "category": "narrative",
        "description": "叙事风格：讲故事",
        "content": (
            "请以讲故事的方式介绍这件文物，让内容生动有趣、富有感染力。\n"
            "注重情节的展开和情感的传递，让听众仿佛置身于历史场景之中。\n"
            "使用生动的语言和形象的比喻，让文物背后的故事活起来。"
        ),
    },
    {
        "key": "narrative_style_academic",
        "name": "Narrative Style - Academic",
        "category": "narrative",
        "description": "叙事风格：学术研究",
        "content": (
            "请以学术研究的方式介绍这件文物，内容要严谨、准确、有据可查。\n"
            "注重历史背景的考证和学术观点的引用，提供可靠的文献依据。\n"
            "使用专业的术语和规范的表述，确保内容的学术价值和可信度。"
        ),
    },
    {
        "key": "narrative_style_interactive",
        "name": "Narrative Style - Interactive",
        "category": "narrative",
        "description": "叙事风格：互动问答",
        "content": (
            "请以互动问答的方式介绍这件文物，鼓励观众思考和参与。\n"
            "提出引人深思的问题，引导观众主动探索和发现。\n"
            "注重与观众的对话和交流，让参观体验更加生动和有意义。"
        ),
    },

    # ── Narrative Generation (English, for curator tools) ───────
    {
        "key": "narrative_generation_template",
        "name": "Narrative Generation Template",
        "category": "narrative",
        "description": "展品叙事内容生成模板（英文）",
        "variables": ["exhibit_name", "exhibit_info", "level_guidance", "style_guidance"],
        "content": (
            "Please create a narrative about the following exhibit:\n\n"
            "Exhibit: {exhibit_name}\n"
            "Information: {exhibit_info}\n\n"
            "Guidelines:\n"
            "- {level_guidance}\n"
            "- {style_guidance}\n"
            "- Keep the narrative engaging and appropriate for a museum visit\n"
            "- Length should be suitable for a 3-5 minute read\n\n"
            "Please generate the narrative:"
        ),
    },
    {
        "key": "narrative_level_beginner",
        "name": "Narrative Level - Beginner",
        "category": "narrative",
        "description": "入门级叙事指导（英文）",
        "content": "Use simple language and avoid technical jargon. Focus on interesting stories and relatable concepts.",
    },
    {
        "key": "narrative_level_intermediate",
        "name": "Narrative Level - Intermediate",
        "category": "narrative",
        "description": "中级叙事指导（英文）",
        "content": "Include some technical details and historical context. Balance accessibility with depth.",
    },
    {
        "key": "narrative_level_expert",
        "name": "Narrative Level - Expert",
        "category": "narrative",
        "description": "专家级叙事指导（英文）",
        "content": "Use professional terminology and academic language. Include detailed analysis and scholarly context.",
    },
    {
        "key": "narrative_style_storytelling_en",
        "name": "Narrative Style - Storytelling (EN)",
        "category": "narrative",
        "description": "叙事风格指导：讲故事（英文）",
        "content": "Tell this as an engaging story with vivid descriptions and emotional resonance.",
    },
    {
        "key": "narrative_style_academic_en",
        "name": "Narrative Style - Academic (EN)",
        "category": "narrative",
        "description": "叙事风格指导：学术（英文）",
        "content": "Present this in a formal, scholarly manner with precise terminology.",
    },
    {
        "key": "narrative_style_interactive_en",
        "name": "Narrative Style - Interactive (EN)",
        "category": "narrative",
        "description": "叙事风格指导：互动（英文）",
        "content": "Create an interactive narrative that invites the visitor to imagine and explore.",
    },
    {
        "key": "narrative_style_balanced_en",
        "name": "Narrative Style - Balanced (EN)",
        "category": "narrative",
        "description": "叙事风格指导：平衡（英文）",
        "content": "Balance storytelling with factual information for an engaging yet informative narrative.",
    },

    # ── Tour TTS Personas ───────────────────────────────────────
    {
        "key": "tour_tts_persona_a",
        "name": "Tour TTS - Archaeologist",
        "category": "tts",
        "description": "考古学家语音人设：沉稳浑厚的中年男性声音",
        "variables": [
            {"name": "__voice__", "description": "白桦"},
            {"name": "__voice_description__", "description": "五十多岁的中年男性，声音沉稳浑厚，带有学术气息"},
        ],
        "content": (
            "【角色】五十多岁的资深考古学家，声音沉稳浑厚，带有学术气息。"
            "常年在田野考古，说话沉稳有力，偶尔带出专业术语但从不卖弄。\n"
            "【场景】在博物馆展厅中，面对感兴趣的参观者，分享自己多年的考古发现与文物背后的故事。\n"
            "【指导】\n"
            "- 语速：适中偏慢，像在课堂上娓娓道来，重要细节处会刻意放慢\n"
            "- 气息：平稳深沉，偶尔在惊叹处加入轻微的感叹\n"
            "- 咬字：清晰准确，对文物名称和历史年代会略微加重\n"
            "- 情绪：对考古发现怀有真挚的热爱与敬畏，讲到精彩处声音会微微上扬"
        ),
    },
    {
        "key": "tour_tts_persona_b",
        "name": "Tour TTS - Villager",
        "category": "tts",
        "description": "老村民语音人设：沙哑沧桑的老年男性声音",
        "variables": [
            {"name": "__voice__", "description": "苏打"},
            {"name": "__voice_description__", "description": "六十多岁的老年男性，声音沙哑沧桑，带有北方乡音"},
        ],
        "content": (
            "【角色】六十多岁的老村民，声音沙哑沧桑，带有北方乡音。"
            "一辈子生活在这片土地上，对家乡的历史和传说了如指掌，说话朴实接地气。\n"
            "【场景】在村口老槐树下，或者博物馆的民俗展区，向来访的客人讲述过去的故事和家乡的记忆。\n"
            "【指导】\n"
            "- 语速：稍慢，像老人家拉家常，有停顿和回忆的间隙\n"
            "- 气息：略带喘息感，偶尔叹气，带着岁月的沉淀\n"
            "- 咬字：带轻微北方口音，平翘舌略混，儿化音自然\n"
            "- 情绪：怀旧温暖，讲到苦难处声音低沉，讲到开心处爽朗大笑"
        ),
    },
    {
        "key": "tour_tts_persona_c",
        "name": "Tour TTS - Teacher",
        "category": "tts",
        "description": "历史老师语音人设：清脆明亮的年轻女性声音",
        "variables": [
            {"name": "__voice__", "description": "茉莉"},
            {"name": "__voice_description__", "description": "三十多岁的年轻女性，声音清脆明亮，富有感染力"},
        ],
        "content": (
            "【角色】三十多岁的年轻历史老师，声音清脆明亮，富有感染力。"
            "讲课生动有趣，善于用比喻和提问吸引学生注意力，是学生最喜欢的老师。\n"
            "【场景】在博物馆中带领学生参观，或者面对参观者，用生动活泼的方式讲解历史知识。\n"
            "【指导】\n"
            "- 语速：适中偏快，节奏明快，像在课堂上激情授课\n"
            "- 气息：充沛有力，偶尔在提问时故意停顿制造悬念\n"
            "- 咬字：清晰利落，关键词汇会加重语气，像划重点\n"
            "- 情绪：热情洋溢，充满好奇心，讲到有趣处会忍不住笑出来"
        ),
    },
]


# ────────────────────────────────────────────────────────────────
# Hall definitions (from init_exhibits.py HALLS_BY_FLOOR)
# ────────────────────────────────────────────────────────────────

HALLS: list[dict] = [
    # Floor 1
    {"slug": "bronze-a", "name": "青铜馆A厅", "description": "商周青铜礼器与兵器，展示中国青铜时代的铸造技艺与礼制文明", "floor": 1, "estimated_duration_minutes": 40, "display_order": 1},
    {"slug": "bronze-b", "name": "青铜馆B厅", "description": "春秋战国至汉代青铜器，展示青铜艺术从神秘向写实的转变", "floor": 1, "estimated_duration_minutes": 35, "display_order": 2},
    {"slug": "ceramics", "name": "陶瓷馆", "description": "从原始陶器到明清官窑，纵览中国陶瓷万年发展史", "floor": 1, "estimated_duration_minutes": 45, "display_order": 3},
    # Floor 2
    {"slug": "painting-a", "name": "书画馆A厅", "description": "唐宋绘画珍品，展示中国绘画艺术的巅峰成就", "floor": 2, "estimated_duration_minutes": 40, "display_order": 4},
    {"slug": "painting-b", "name": "书画馆B厅", "description": "元明清书画作品，展示文人画的演变与传承", "floor": 2, "estimated_duration_minutes": 35, "display_order": 5},
    {"slug": "jade", "name": "玉器馆", "description": "从新石器时代到清代的玉器精品，展示中国玉文化的深厚底蕴", "floor": 2, "estimated_duration_minutes": 40, "display_order": 6},
    # Floor 3
    {"slug": "gold-silver", "name": "金银器馆", "description": "唐代何家村窖藏至清代宫廷金银器，展示金属工艺的极致之美", "floor": 3, "estimated_duration_minutes": 35, "display_order": 7},
    {"slug": "sculpture", "name": "雕塑馆", "description": "从汉代石刻到清代牙雕，展示中国雕塑艺术的多元面貌", "floor": 3, "estimated_duration_minutes": 35, "display_order": 8},
    {"slug": "special", "name": "特展馆", "description": "临时展览与主题特展，定期更换展览内容", "floor": 3, "estimated_duration_minutes": 30, "display_order": 9},
]


# ────────────────────────────────────────────────────────────────
# Seed logic
# ────────────────────────────────────────────────────────────────

async def seed_prompts(service: PromptService) -> tuple[int, int, int]:
    """Seed all prompt templates. Returns (created, updated, skipped)."""
    created = updated = skipped = 0

    for p in PROMPTS:
        existing = await service.get_prompt(p["key"])
        if existing:
            if existing.content != p["content"]:
                await service.update_prompt(
                    key=p["key"],
                    content=p["content"],
                    changed_by="seed_script",
                    change_reason="Sync from seed_prompts_and_personas.py",
                )
                print(f"  [updated] {p['key']}")
                updated += 1
            else:
                print(f"  [skip]    {p['key']}")
                skipped += 1
        else:
            await service.create_prompt(
                key=p["key"],
                name=p["name"],
                category=p["category"],
                content=p["content"],
                description=p.get("description"),
                variables=p.get("variables"),
            )
            print(f"  [created] {p['key']}")
            created += 1

    return created, updated, skipped


async def seed_halls(session) -> tuple[int, int]:
    """Seed hall definitions. Returns (created, skipped)."""
    created = skipped = 0
    now = datetime.now(UTC)

    for h in HALLS:
        result = await session.execute(select(Hall).where(Hall.slug == h["slug"]))
        existing = result.scalar_one_or_none()

        if existing:
            print(f"  [skip]    {h['slug']} ({h['name']})")
            skipped += 1
        else:
            hall = Hall(
                slug=h["slug"],
                name=h["name"],
                description=h["description"],
                floor=h["floor"],
                estimated_duration_minutes=h["estimated_duration_minutes"],
                display_order=h["display_order"],
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            session.add(hall)
            print(f"  [created] {h['slug']} ({h['name']})")
            created += 1

    await session.commit()
    return created, skipped


# ────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────

async def main() -> None:
    settings = get_settings()
    print("=" * 60)
    print("Seeding prompts, personas, and halls")
    print("=" * 60)
    print(f"Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")
    print()

    session_maker = await init_database(settings.DATABASE_URL)

    # ── Prompts ─────────────────────────────────────────────────
    print("Prompts:")
    print("-" * 60)
    async with get_session(session_maker) as session:
        repo = PostgresPromptRepository(session)
        cache = PromptCache()
        service = PromptService(repo, cache)
        p_created, p_updated, p_skipped = await seed_prompts(service)
    print()

    # ── Halls ───────────────────────────────────────────────────
    print("Halls:")
    print("-" * 60)
    async with get_session(session_maker) as session:
        h_created, h_skipped = await seed_halls(session)
    print()

    # ── Summary ─────────────────────────────────────────────────
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"  Prompts: {p_created} created, {p_updated} updated, {p_skipped} skipped")
    print(f"  Halls:   {h_created} created, {h_skipped} skipped")
    print()


if __name__ == "__main__":
    asyncio.run(main())
