import asyncio
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.tour_event_service import get_events_by_session
from app.application.hall_normalizer import hall_display_name, normalize_hall
from app.application.tour_session_service import get_session
from app.domain.entities import TourReport
from app.infra.postgres.models import TourReportModel

CERAMIC_KEYWORDS = [
    "陶", "瓷", "盆", "罐", "瓶", "碗", "鼎", "甑", "釜", "纹",
    "彩陶", "人面鱼纹", "鱼纹", "几何纹", "绳纹", "尖底瓶",
    "红陶", "灰陶", "黑陶", "泥塑", "陶塑", "陶器", "瓷器",
    "素面", "刻划", "彩绘",
]

ONE_LINER_CANDIDATES = [
    "今天，我用AI唤醒了沉睡六千年的半坡先民",
    "我的博物馆向导来自公元前4000年",
    "没有文字的时代，他们把不朽的灵魂画在彩陶上",
    "凝视人面鱼纹盆的瞬间，六千年的风从浐河吹进了现实",
    "我们在泥土里寻找的不是瓦罐，而是六千年前祖宗的倒影",
    "半坡一日游达成：确认过了，如果回到6000年前，我的手艺只配负责吃",
    "懂了，六千年前的先民不内卷，每天研究怎么抓鱼和捏泥巴",
]

HARDCORE_TAGS = ["史前细节显微镜", "碎片重构大师", "冷酷无情的地层勘探机"]
FUN_TAGS = ["六千年前的干饭王", "母系氏族社交悍匪", "沉睡的部落大祭司"]
AESTHETIC_TAGS = ["史前第一眼光", "彩陶纹饰解码者", "被文物选中的人"]

REFLECTION_TOPIC_LABELS = {
    "craft": "器物工艺",
    "settlement": "聚落空间",
    "social": "社会组织",
    "spiritual": "精神文化",
    "life": "日常生活",
    "evidence": "证据推理",
}

PERSONA_INITIAL_FOCUS = {
    "A": ("evidence", "先看证据和推理过程"),
    "B": ("evidence", "把观察整理成可复盘的研学记录"),
    "C": ("social", "追问半坡与更大的历史问题"),
    "D": ("craft", "从器物材料、器形、纹饰和工艺进入半坡"),
}

ASSUMPTION_REFLECTION_TEXTS = {
    "A": "你起初更关注共同体是否平等互助。",
    "B": "你起初更关注半坡人的日常生存和生活方式。",
    "C": "你起初更关注分工、规则和社会组织是否已经出现。",
    "D": "你起初选择先不下判断，希望跟着证据逐步形成看法。",
}

TOPIC_KEYWORDS = {
    "craft": [
        "陶", "器", "工艺", "纹", "材料", "制作", "烧制", "陶窑", "尖底瓶",
        "彩陶", "石器", "骨器", "工具", "器形", "用途", "痕迹", "磨损",
    ],
    "settlement": [
        "聚落", "房屋", "半地穴", "壕沟", "遗址", "空间", "布局", "作坊",
        "灶", "墓葬", "居住", "保护大厅", "地面圆形房屋",
    ],
    "social": [
        "社会", "组织", "分工", "规则", "共同体", "协作", "等级", "贫富",
        "身份", "公共", "权力", "资源", "秩序",
    ],
    "spiritual": [
        "精神", "信仰", "仪式", "审美", "象征", "人面", "鱼纹", "图案",
        "纹饰", "祭祀", "观念",
    ],
    "life": [
        "生活", "吃", "食物", "农业", "农耕", "居住", "日常", "生存",
        "采集", "狩猎", "儿童", "家庭",
    ],
    "evidence": [
        "证据", "推断", "不确定", "考古", "展签", "材料", "判断", "线索",
        "地层", "出土", "遗存",
    ],
}

HALL_TOPIC_WEIGHTS = {
    "basic-exhibition-hall": {"craft": 1, "life": 1, "evidence": 1},
    "site-protection-hall": {"settlement": 2, "social": 1, "evidence": 1},
    "kiln-hall": {"craft": 2, "evidence": 1},
    "prehistoric-workshop": {"craft": 1, "life": 1},
    "education-center": {"evidence": 2},
    "banpo-girl-sculpture": {"spiritual": 1, "social": 1},
    "peony-garden": {"life": 1},
}


RECORD_SUMMARY_MAX_CHARS = 400
RECORD_SUMMARY_MAX_PAIRS = 12
RECORD_SUMMARY_ANSWER_CHARS = 320
RECORD_SUMMARY_QUESTION_CHARS = 120

PERSONA_SUMMARY_NAMES = {
    "A": "考古研究员",
    "B": "研学记录员",
    "C": "历史追问者",
    "D": "器物研究员",
}


def detect_ceramic_question(message: str) -> bool:
    return any(kw in message for kw in CERAMIC_KEYWORDS)


def calculate_radar_scores(stats: dict) -> dict:
    total_minutes = stats.get("total_duration_minutes", 0)
    total_questions = stats.get("total_questions", 0)
    total_exhibits = stats.get("total_exhibits_viewed", 0)
    site_hall_minutes = stats.get("site_hall_duration_minutes", 0)
    ceramic_q = stats.get("ceramic_questions", 0)

    civilization = 3 if total_minutes > 60 else (2 if total_minutes >= 30 else 1)
    imagination = 3 if total_questions > 15 else (2 if total_questions >= 10 else 1)
    history = 3 if total_exhibits > 10 else (2 if total_exhibits >= 5 else 1)
    lifestyle = 3 if site_hall_minutes > 20 else (2 if site_hall_minutes >= 10 else 1)
    aesthetics = 3 if ceramic_q >= 3 else (2 if ceramic_q >= 1 else 1)

    return {
        "civilization_resonance": civilization,
        "imagination_breadth": imagination,
        "history_collection": history,
        "life_experience": lifestyle,
        "ceramic_aesthetics": aesthetics,
    }


def select_identity_tags(radar_scores: dict) -> list[str]:
    tags = []

    civ = radar_scores.get("civilization_resonance", 1)
    hist = radar_scores.get("history_collection", 1)
    img = radar_scores.get("imagination_breadth", 1)
    life = radar_scores.get("life_experience", 1)
    aes = radar_scores.get("ceramic_aesthetics", 1)

    if civ == 3:
        tags.append(HARDCORE_TAGS[2])
    elif hist == 3:
        tags.append(HARDCORE_TAGS[1])
    else:
        tags.append(HARDCORE_TAGS[0])

    if img == 3:
        tags.append(FUN_TAGS[1])
    elif life == 3:
        tags.append(FUN_TAGS[2])
    else:
        tags.append(FUN_TAGS[0])

    if aes == 3:
        tags.append(AESTHETIC_TAGS[1])
    elif civ == 3:
        tags.append(AESTHETIC_TAGS[2])
    else:
        tags.append(AESTHETIC_TAGS[0])

    return tags


def get_report_theme(persona: str) -> str:
    return {
        "A": "archaeology",
        "B": "field_study",
        "C": "history_inquiry",
        "D": "artifact_study",
    }.get(persona, "archaeology")


def build_reflection_summary(
    tour_session,
    events: list,
    stats: dict | None = None,
    radar_scores: dict | None = None,
) -> dict[str, Any]:
    """Infer reflection summary from existing session/events without an LLM call."""
    stats = stats or {}
    radar_scores = radar_scores or {}
    persona = getattr(tour_session, "persona", None) or "A"
    assumption = getattr(tour_session, "assumption", None) or "D"
    initial_topic, initial_focus_text = PERSONA_INITIAL_FOCUS.get(persona, PERSONA_INITIAL_FOCUS["A"])
    assumption_text = ASSUMPTION_REFLECTION_TEXTS.get(assumption, ASSUMPTION_REFLECTION_TEXTS["D"])

    question_count = 0
    deep_dive_count = 0
    scores: dict[str, float] = {key: 0.0 for key in REFLECTION_TOPIC_LABELS}

    for event in events or []:
        event_type = getattr(event, "event_type", "") or ""
        metadata = getattr(event, "metadata", None) or {}
        hall = normalize_hall(getattr(event, "hall", None)) or ""
        text = _reflection_event_text(event, metadata, hall)

        if event_type == "exhibit_question":
            question_count += 1
            weight = 3.0
        elif event_type == "exhibit_deep_dive":
            deep_dive_count += 1
            weight = 3.0
        elif event_type == "exhibit_view":
            weight = 1.0
        elif event_type in {"hall_enter", "hall_leave"}:
            weight = 0.0
        else:
            weight = 0.5

        for topic, topic_weight in HALL_TOPIC_WEIGHTS.get(hall, {}).items():
            scores[topic] += topic_weight * weight

        for topic in _match_reflection_topics(text):
            scores[topic] += weight

    total_signals = question_count + deep_dive_count
    if total_signals < 2:
        return {
            "initial_assumption": f"{initial_focus_text}；{assumption_text}",
            "observed_focus": "目前只记录到少量提问或深入查看，更多是展厅到访线索。",
            "change_summary": "证据不足，关注点变化暂不明显。",
            "confidence": 0.35,
            "status": "insufficient",
            "initial_focus": REFLECTION_TOPIC_LABELS.get(initial_topic, initial_topic),
            "observed_focus_key": None,
        }

    top_topic = max(scores, key=scores.get)
    top_score = scores.get(top_topic, 0.0)
    total_score = sum(scores.values()) or 1.0
    observed_label = REFLECTION_TOPIC_LABELS.get(top_topic, top_topic)
    initial_label = REFLECTION_TOPIC_LABELS.get(initial_topic, initial_topic)
    confidence = min(0.92, 0.5 + (top_score / total_score) * 0.3 + min(total_signals, 6) * 0.03)

    if top_score <= 0:
        observed_focus = "你的提问还没有形成清晰主题。"
        change_summary = "证据不足，暂时不能判断关注点变化。"
        status = "insufficient"
        confidence = 0.35
    elif top_topic == initial_topic:
        observed_focus = f"你的提问和深入查看主要集中在{observed_label}。"
        change_summary = f"关注点基本保持稳定：你从{initial_label}进入导览，过程中也持续围绕这一方向积累证据。"
        status = "stable"
    else:
        observed_focus = f"你的提问和深入查看逐渐集中到{observed_label}。"
        change_summary = f"关注点出现了转向：你从{initial_label}进入导览，但过程中更频繁地追问{observed_label}，说明新的证据正在改变你的观察重心。"
        status = "shifted"

    if radar_scores:
        strongest_radar = max(radar_scores, key=lambda key: radar_scores.get(key, 0))
        if strongest_radar == "ceramic_aesthetics" and top_topic != "craft":
            observed_focus += " 同时，报告画像仍显示你保留了器物细节观察的能力。"
        elif strongest_radar == "life_experience" and top_topic != "life":
            observed_focus += " 同时，报告画像里也能看到你对生活经验的关注。"

    return {
        "initial_assumption": f"{initial_focus_text}；{assumption_text}",
        "observed_focus": observed_focus,
        "change_summary": change_summary,
        "confidence": round(confidence, 2),
        "status": status,
        "initial_focus": initial_label,
        "observed_focus_key": top_topic if top_score > 0 else None,
    }


def _reflection_event_text(event, metadata: dict, hall: str) -> str:
    parts = [
        hall,
        str(metadata.get("question") or ""),
        str(metadata.get("message") or ""),
        str(metadata.get("exhibit_name") or ""),
        str(metadata.get("name") or ""),
    ]
    exhibit_id = getattr(event, "exhibit_id", None)
    if exhibit_id:
        parts.append(str(exhibit_id.value if hasattr(exhibit_id, "value") else exhibit_id))
    return " ".join(part for part in parts if part)


def _match_reflection_topics(text: str) -> set[str]:
    matched: set[str] = set()
    if not text:
        return matched
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            matched.add(topic)
    return matched


def _ensure_aware(dt):
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _event_metadata(event) -> dict:
    return getattr(event, "metadata", None) or {}


def _event_dedupe_key(event, *parts: Any) -> str:
    metadata = _event_metadata(event)
    client_event_id = metadata.get("client_event_id")
    if client_event_id:
        return str(client_event_id)
    normalized_parts = [str(part or "").strip() for part in parts]
    return "|".join(normalized_parts)


def aggregate_stats(events: list, tour_session) -> dict:
    total_duration = 0.0
    started_at = _ensure_aware(tour_session.started_at)
    completed_at = _ensure_aware(tour_session.completed_at)
    if started_at and completed_at:
        total_duration = (completed_at - started_at).total_seconds() / 60.0
    elif started_at:
        total_duration = (datetime.now(UTC) - started_at).total_seconds() / 60.0

    exhibit_durations: dict[str, int] = {}
    hall_durations: dict[str, int] = {}
    total_questions = 0
    ceramic_questions = 0
    viewed_exhibits: set[str] = set()
    seen_questions: set[str] = set()
    seen_duration_events: set[str] = set()

    for event in events:
        metadata = _event_metadata(event)
        if event.event_type == "exhibit_view" and event.exhibit_id and event.duration_seconds:
            duration_key = _event_dedupe_key(
                event,
                event.event_type,
                event.exhibit_id,
                event.hall,
                event.duration_seconds,
            )
            if duration_key in seen_duration_events:
                continue
            seen_duration_events.add(duration_key)
            eid = event.exhibit_id.value if hasattr(event.exhibit_id, 'value') else str(event.exhibit_id)
            exhibit_durations[eid] = exhibit_durations.get(eid, 0) + event.duration_seconds
            viewed_exhibits.add(eid)
        elif event.event_type == "hall_leave" and event.hall and event.duration_seconds:
            duration_key = _event_dedupe_key(
                event,
                event.event_type,
                event.hall,
                event.duration_seconds,
            )
            if duration_key in seen_duration_events:
                continue
            seen_duration_events.add(duration_key)
            hall = normalize_hall(event.hall)
            if not hall:
                continue
            hall_durations[hall] = hall_durations.get(hall, 0) + event.duration_seconds
        elif event.event_type == "exhibit_question":
            question_text = metadata.get("message") or metadata.get("question") or ""
            question_key = _event_dedupe_key(
                event,
                event.event_type,
                normalize_hall(event.hall),
                question_text,
            )
            if question_key in seen_questions:
                continue
            seen_questions.add(question_key)
            total_questions += 1
            if metadata.get("is_ceramic_question"):
                ceramic_questions += 1

    most_viewed_exhibit_id = None
    most_viewed_exhibit_duration = None
    if exhibit_durations:
        top_eid = max(exhibit_durations, key=exhibit_durations.get)
        most_viewed_exhibit_id = top_eid
        most_viewed_exhibit_duration = exhibit_durations[top_eid]

    longest_hall = None
    longest_hall_duration = None
    if hall_durations:
        top_hall = max(hall_durations, key=hall_durations.get)
        longest_hall = top_hall
        longest_hall_duration = hall_durations[top_hall]

    site_hall_minutes = hall_durations.get("site-protection-hall", 0) / 60.0

    return {
        "total_duration_minutes": round(total_duration, 1),
        "most_viewed_exhibit_id": most_viewed_exhibit_id,
        "most_viewed_exhibit_duration": most_viewed_exhibit_duration,
        "longest_hall": longest_hall,
        "longest_hall_duration": longest_hall_duration,
        "total_questions": total_questions,
        "total_exhibits_viewed": len(viewed_exhibits),
        "ceramic_questions": ceramic_questions,
        "site_hall_duration_minutes": round(site_hall_minutes, 1),
    }


async def generate_report(
    session: AsyncSession,
    tour_session_id: str,
    llm_provider: Any = None,
) -> TourReport:
    stmt = select(TourReportModel).where(TourReportModel.tour_session_id == tour_session_id)
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    tour_session = await get_session(session, tour_session_id)
    events = await get_events_by_session(session, tour_session_id)

    stats = aggregate_stats(events, tour_session)
    radar_scores = calculate_radar_scores(stats)
    identity_tags = select_identity_tags(radar_scores)
    report_theme = get_report_theme(tour_session.persona)

    one_liner = existing.one_liner if existing is not None else _pick_one_liner(stats, tour_session.persona)
    record_summary = existing.record_summary if existing is not None else None
    previous_question_count = existing.total_questions if existing is not None else None
    should_refresh_record_summary = (
        existing is None
        or not record_summary
        or previous_question_count != stats["total_questions"]
    )

    # ── LLM enrichment (one-liner + record summary) ─────────────────────────────
    # Both are independent LLM calls; run them concurrently so report generation
    # pays one round-trip instead of two. The record summary is only attempted
    # when we captured answered Q&A — otherwise the API falls back to the keyword
    # template (no regression). Failures degrade to the non-LLM fallback per task.
    if llm_provider:
        qa_pairs = collect_qa_pairs(events) if should_refresh_record_summary else []
        tasks: dict[str, Any] = {}
        if existing is None:
            tasks["one_liner"] = _generate_one_liner_llm(llm_provider, tour_session.persona, stats)
        if qa_pairs:
            tasks["record_summary"] = generate_record_summary_llm(
                llm_provider, tour_session.persona, qa_pairs
            )
        if tasks:
            outcomes = await asyncio.gather(*tasks.values(), return_exceptions=True)
            for key, outcome in zip(tasks.keys(), outcomes):
                if isinstance(outcome, Exception):
                    logger.warning(f"Failed to generate {key} via LLM, using fallback: {outcome}")
                    continue
                if key == "one_liner" and outcome:
                    one_liner = outcome
                elif key == "record_summary":
                    record_summary = outcome or None

    if existing is not None:
        existing.total_duration_minutes = stats["total_duration_minutes"]
        existing.most_viewed_exhibit_id = stats["most_viewed_exhibit_id"]
        existing.most_viewed_exhibit_duration = stats["most_viewed_exhibit_duration"]
        existing.longest_hall = stats["longest_hall"]
        existing.longest_hall_duration = stats["longest_hall_duration"]
        existing.total_questions = stats["total_questions"]
        existing.total_exhibits_viewed = stats["total_exhibits_viewed"]
        existing.ceramic_questions = stats["ceramic_questions"]
        existing.identity_tags = identity_tags
        existing.radar_scores = radar_scores
        existing.one_liner = one_liner
        existing.report_theme = report_theme
        existing.record_summary = record_summary
        await session.commit()
        await session.refresh(existing)
        return existing.to_entity()

    report_id = str(uuid.uuid4())
    model = TourReportModel(
        id=report_id,
        tour_session_id=tour_session_id,
        total_duration_minutes=stats["total_duration_minutes"],
        most_viewed_exhibit_id=stats["most_viewed_exhibit_id"],
        most_viewed_exhibit_duration=stats["most_viewed_exhibit_duration"],
        longest_hall=stats["longest_hall"],
        longest_hall_duration=stats["longest_hall_duration"],
        total_questions=stats["total_questions"],
        total_exhibits_viewed=stats["total_exhibits_viewed"],
        ceramic_questions=stats["ceramic_questions"],
        identity_tags=identity_tags,
        radar_scores=radar_scores,
        one_liner=one_liner,
        report_theme=report_theme,
        record_summary=record_summary,
        created_at=datetime.now(UTC),
    )
    session.add(model)
    await session.commit()
    await session.refresh(model)
    return model.to_entity()


async def get_report(session: AsyncSession, tour_session_id: str) -> TourReport | None:
    stmt = select(TourReportModel).where(TourReportModel.tour_session_id == tour_session_id)
    result = await session.execute(stmt)
    model = result.scalar_one_or_none()
    return model.to_entity() if model else None


def _pick_one_liner(stats: dict, persona: str) -> str:
    import random
    return random.choice(ONE_LINER_CANDIDATES)


def _clean_record_text(value: str | None) -> str:
    """Strip markdown/whitespace noise from recorded question/answer text."""
    text = str(value or "")
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[*_`#>]+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _trim_summary(text: str, max_chars: int = RECORD_SUMMARY_MAX_CHARS) -> str:
    """Keep the summary within the budget without cutting mid-sentence."""
    cleaned = _clean_record_text(text)
    if len(cleaned) <= max_chars:
        return cleaned
    window = cleaned[:max_chars]
    cut = max(window.rfind(sep) for sep in "。！？；")
    if cut >= int(max_chars * 0.6):
        return window[: cut + 1]
    return window.rstrip("，、；：…. ") + "。"


def collect_qa_pairs(events: list) -> list[dict[str, str]]:
    """Reconstruct ordered visitor↔guide Q&A pairs that actually have answers.

    The frontend records ``assistant_answer`` events carrying both the original
    question and the AI answer; bare ``exhibit_question`` events seed the entry so
    a later answer can attach to it. Only pairs with a non-empty answer are kept —
    a conversation with no answers has nothing to summarize.
    """
    entries: dict[str, dict[str, str]] = {}
    order: list[str] = []
    for event in events or []:
        event_type = getattr(event, "event_type", None)
        if event_type not in {"assistant_answer", "exhibit_question"}:
            continue
        metadata = getattr(event, "metadata", None) or {}
        question = _clean_record_text(
            metadata.get("question") or metadata.get("message") or metadata.get("query")
        )
        if not question:
            continue
        hall = normalize_hall(getattr(event, "hall", None) or metadata.get("hall")) or ""
        key = f"{hall}|{question}"
        entry = entries.get(key)
        if entry is None:
            entry = {"hall": hall, "question": question, "answer": ""}
            entries[key] = entry
            order.append(key)
        if event_type == "assistant_answer":
            answer = _clean_record_text(metadata.get("answer"))
            if answer and not entry["answer"]:
                entry["answer"] = answer
    return [entries[key] for key in order if entries[key]["answer"]]


def _build_summary_prompt(persona: str, qa_pairs: list[dict[str, str]]) -> str:
    persona_name = PERSONA_SUMMARY_NAMES.get(persona, "考古研究员")
    lines: list[str] = []
    for index, pair in enumerate(qa_pairs[:RECORD_SUMMARY_MAX_PAIRS], 1):
        hall = hall_display_name(pair["hall"]) if pair["hall"] else ""
        prefix = f"（{hall}）" if hall else ""
        question = pair["question"][:RECORD_SUMMARY_QUESTION_CHARS]
        answer = pair["answer"][:RECORD_SUMMARY_ANSWER_CHARS]
        lines.append(f"{index}. {prefix}游客问：{question}\n   导览答：{answer}")
    transcript = "\n".join(lines)
    return (
        "你正在为一次西安半坡博物馆的AI导览生成「记录摘要」。\n"
        "以下是本次游客与AI导览员的真实问答记录（按时间顺序）：\n\n"
        f"{transcript}\n\n"
        f"请以{persona_name}的视角，把上面这段真实对话提炼成一段连贯的中文「记录摘要」，要求：\n"
        "1. 必须基于上面真实问答的具体内容，准确写出游客实际关心的问题，"
        "以及对话中得到的关键信息或结论；不要套用与本次对话无关的通用说辞，也不要编造未提到的展品。\n"
        "2. 用第二人称「你」称呼游客，像在帮游客复盘这次参观。\n"
        "3. 输出一段完整的话，不超过400字，必须有完整结尾，"
        "不要写标题、列表、编号或Markdown符号。\n"
        "4. 只输出摘要正文本身，不要任何前后缀、引号或解释。"
    )


async def generate_record_summary_llm(
    llm_provider: Any,
    persona: str,
    qa_pairs: list[dict[str, str]],
) -> str:
    """Summarize the real tour conversation into a <=400 char record summary."""
    prompt = _build_summary_prompt(persona, qa_pairs)
    messages = [{"role": "user", "content": prompt}]
    model = getattr(llm_provider, "report_model", None)
    if getattr(llm_provider, "supports_model_override", False) is True and model:
        result = await llm_provider.generate(messages, model=model)
    else:
        result = await llm_provider.generate(messages)
    content = getattr(result, "content", result)
    return _trim_summary(str(content or ""))


async def _generate_one_liner_llm(llm_provider: Any, persona: str, stats: dict) -> str:
    persona_names = {
        "A": "考古研究员",
        "B": "研学记录员",
        "C": "历史追问者",
        "D": "器物研究员",
    }
    prompt = (
        f"根据以下游览数据，生成一句有感染力的'游览一句话'（15字以内），"
        f"风格要符合{persona_names.get(persona, '考古研究员')}的身份：\n"
        f"- 游览时长：{stats.get('total_duration_minutes', 0):.0f}分钟\n"
        f"- 提问次数：{stats.get('total_questions', 0)}\n"
        f"- 参观展品数：{stats.get('total_exhibits_viewed', 0)}\n"
        f"只输出一句话，不要其他内容。"
    )
    messages = [{"role": "user", "content": prompt}]
    model = getattr(llm_provider, "report_model", None)
    if getattr(llm_provider, "supports_model_override", False) is True and model:
        result = await llm_provider.generate(messages, model=model)
    else:
        result = await llm_provider.generate(messages)
    content = getattr(result, "content", result)
    return str(content).strip()[:50] if content else _pick_one_liner(stats, persona)
