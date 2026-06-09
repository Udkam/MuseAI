import uuid
from datetime import UTC, datetime

from loguru import logger
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import TourEvent
from app.infra.postgres.models import TourEventModel

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 0.5


async def record_events(
    session: AsyncSession,
    tour_session_id: str,
    events: list[dict],
) -> list[TourEvent]:
    if not events:
        return []

    incoming_client_ids = {
        str((event_data.get("metadata") or {}).get("client_event_id"))
        for event_data in events
        if (event_data.get("metadata") or {}).get("client_event_id")
    }
    existing_client_ids: set[str] = set()
    if incoming_client_ids:
        result = await session.execute(
            select(TourEventModel).where(TourEventModel.tour_session_id == tour_session_id)
        )
        for model in result.scalars().all():
            meta = model.event_meta or {}
            client_event_id = meta.get("client_event_id")
            if client_event_id:
                existing_client_ids.add(str(client_event_id))

    now = datetime.now(UTC)
    models = []
    batch_client_ids: set[str] = set()
    for event_data in events:
        metadata = event_data.get("metadata") or {}
        client_event_id = metadata.get("client_event_id")
        if client_event_id:
            client_event_id = str(client_event_id)
            if client_event_id in existing_client_ids or client_event_id in batch_client_ids:
                continue
            batch_client_ids.add(client_event_id)
        model = TourEventModel(
            id=str(uuid.uuid4()),
            tour_session_id=tour_session_id,
            event_type=event_data["event_type"],
            exhibit_id=event_data.get("exhibit_id"),
            hall=event_data.get("hall"),
            duration_seconds=event_data.get("duration_seconds"),
            event_meta=metadata,
            created_at=now,
        )
        session.add(model)
        models.append(model)

    if not models:
        return []

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            await session.commit()
            break
        except OperationalError as e:
            if attempt < MAX_RETRIES:
                logger.warning(f"record_events commit failed (attempt {attempt}/{MAX_RETRIES}): {e}")
                import asyncio
                await asyncio.sleep(RETRY_DELAY_SECONDS * attempt)
            else:
                raise

    for m in models:
        await session.refresh(m)
    return [m.to_entity() for m in models]


async def get_events_by_session(
    session: AsyncSession,
    tour_session_id: str,
) -> list[TourEvent]:
    stmt = (
        select(TourEventModel)
        .where(TourEventModel.tour_session_id == tour_session_id)
        .order_by(TourEventModel.created_at.asc())
    )
    result = await session.execute(stmt)
    return [model.to_entity() for model in result.scalars().all()]
