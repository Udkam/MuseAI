"""Admin API endpoints for hall settings management."""

from datetime import UTC, datetime
import hashlib
import re

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update

from app.api.deps import CurrentAdminUser, SessionDep
from app.application.hall_normalizer import (
    CANONICAL_HALL_SLUGS,
    canonical_hall_contract,
    normalize_hall,
)
from app.infra.postgres.models import Exhibit, Hall

router = APIRouter(prefix="/admin/halls", tags=["admin-halls"])


class HallCreateRequest(BaseModel):
    slug: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    floor: int | None = Field(default=None, ge=1, le=10)
    estimated_duration_minutes: int = Field(default=30, ge=1, le=480)
    display_order: int = Field(default=0, ge=0, le=100000)
    is_active: bool = True


class HallUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    floor: int | None = Field(default=None, ge=1, le=10)
    estimated_duration_minutes: int | None = Field(default=None, ge=1, le=480)
    display_order: int | None = Field(default=None, ge=0, le=100000)
    is_active: bool | None = None


class HallResponse(BaseModel):
    slug: str
    name: str
    description: str | None
    floor: int | None
    estimated_duration_minutes: int
    display_order: int
    is_active: bool
    created_at: str
    updated_at: str


class HallListResponse(BaseModel):
    halls: list[HallResponse]
    total: int


class HallDeleteResponse(BaseModel):
    status: str
    slug: str


def _slugify(value: str) -> str:
    stripped = value.strip().lower()
    ascii_slug = re.sub(r"[^a-z0-9]+", "-", stripped).strip("-")
    if ascii_slug:
        return ascii_slug
    digest = hashlib.md5(value.encode("utf-8")).hexdigest()[:8]
    return f"hall-{digest}"


def _allocate_slug(raw_name: str, slug_name_map: dict[str, str]) -> str:
    for existing_slug, existing_name in slug_name_map.items():
        if existing_name == raw_name:
            return existing_slug

    base = _slugify(raw_name)
    candidate = base
    suffix = 2
    while candidate in slug_name_map and slug_name_map[candidate] != raw_name:
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


async def _backfill_halls_from_exhibits(session: SessionDep) -> None:
    existing_result = await session.execute(select(Hall.slug, Hall.name))
    slug_name_map: dict[str, str] = {row[0]: row[1] for row in existing_result.all()}

    raw_hall_rows = await session.execute(
        select(Exhibit.hall)
        .where(Exhibit.hall.is_not(None), func.trim(Exhibit.hall) != "")
        .distinct()
        .order_by(Exhibit.hall.asc())
    )
    raw_halls = [row[0] for row in raw_hall_rows.all() if row[0]]
    if not raw_halls:
        return

    max_order_result = await session.execute(select(func.max(Hall.display_order)))
    next_display_order = (max_order_result.scalar_one_or_none() or 0) + 10

    changed = False
    for raw_hall in raw_halls:
        if raw_hall in slug_name_map:
            continue

        target_slug = _allocate_slug(raw_hall, slug_name_map)

        if target_slug not in slug_name_map:
            session.add(
                Hall(
                    slug=target_slug,
                    name=raw_hall,
                    description=None,
                    floor=None,
                    estimated_duration_minutes=30,
                    display_order=next_display_order,
                    is_active=True,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
            )
            slug_name_map[target_slug] = raw_hall
            next_display_order += 10
            changed = True

        if raw_hall != target_slug:
            await session.execute(
                update(Exhibit)
                .where(Exhibit.hall == raw_hall)
                .values(hall=target_slug)
            )
            changed = True

    if changed:
        await session.commit()


async def _sync_halls_with_contract(session: SessionDep) -> None:
    """Keep the DB hall table aligned to the Banpo canonical contract."""
    changed = False

    raw_hall_rows = await session.execute(
        select(Exhibit.hall)
        .where(Exhibit.hall.is_not(None), func.trim(Exhibit.hall) != "")
        .distinct()
    )
    for row in raw_hall_rows.all():
        raw_hall = row[0]
        target_hall = normalize_hall(raw_hall)
        if target_hall in CANONICAL_HALL_SLUGS and target_hall != raw_hall:
            await session.execute(
                update(Exhibit)
                .where(Exhibit.hall == raw_hall)
                .values(hall=target_hall, updated_at=datetime.now(UTC))
            )
            changed = True

    result = await session.execute(
        select(Hall).order_by(Hall.display_order.asc(), Hall.created_at.asc())
    )
    rows = list(result.scalars().all())
    rows_by_target: dict[str, list[Hall]] = {}
    for row in rows:
        target = normalize_hall(row.slug)
        if target not in CANONICAL_HALL_SLUGS:
            target = normalize_hall(row.name)
        if target in CANONICAL_HALL_SLUGS:
            rows_by_target.setdefault(target, []).append(row)

    now = datetime.now(UTC)
    for contract in canonical_hall_contract():
        slug = contract["slug"]
        matching_rows = rows_by_target.get(slug, [])
        canonical = next((row for row in matching_rows if row.slug == slug), None)
        legacy_rows = [row for row in matching_rows if row.slug != slug]
        row_changed = False

        if canonical is None and legacy_rows:
            canonical = legacy_rows.pop(0)
            canonical.slug = slug
            row_changed = True
        elif canonical is None:
            canonical = Hall(slug=slug, created_at=now)
            session.add(canonical)
            row_changed = True

        deleted_legacy = False
        for legacy in legacy_rows:
            await session.delete(legacy)
            changed = True
            deleted_legacy = True
        if deleted_legacy:
            await session.flush()

        for field in (
            "name",
            "description",
            "floor",
            "estimated_duration_minutes",
            "display_order",
            "is_active",
        ):
            value = contract[field]
            if field == "description" and value is None and getattr(canonical, field):
                continue
            if getattr(canonical, field) != value:
                setattr(canonical, field, value)
                row_changed = True
        if row_changed:
            canonical.updated_at = now
            changed = True

    if changed:
        await session.commit()


def _to_response(hall: Hall) -> HallResponse:
    return HallResponse(
        slug=hall.slug,
        name=hall.name,
        description=hall.description,
        floor=hall.floor,
        estimated_duration_minutes=hall.estimated_duration_minutes,
        display_order=hall.display_order,
        is_active=hall.is_active,
        created_at=hall.created_at.isoformat(),
        updated_at=hall.updated_at.isoformat(),
    )


def _normalize_slug(slug: str) -> str:
    normalized = slug.strip().lower()
    if not normalized:
        raise HTTPException(status_code=400, detail="Slug cannot be empty")
    return normalized


@router.get("", response_model=HallListResponse, summary="List halls (admin)")
async def list_halls(
    session: SessionDep,
    current_user: CurrentAdminUser,
    include_inactive: bool = Query(True),
) -> HallListResponse:
    has_hall_rows = await session.execute(select(Hall.slug).limit(1))
    if has_hall_rows.scalar_one_or_none() is None:
        await _backfill_halls_from_exhibits(session)
    await _sync_halls_with_contract(session)

    stmt = select(Hall)
    if not include_inactive:
        stmt = stmt.where(Hall.is_active.is_(True))
    stmt = stmt.order_by(Hall.display_order.asc(), Hall.created_at.asc())

    result = await session.execute(stmt)
    halls = list(result.scalars().all())

    return HallListResponse(halls=[_to_response(h) for h in halls], total=len(halls))


@router.post("", response_model=HallResponse, status_code=status.HTTP_201_CREATED, summary="Create hall (admin)")
async def create_hall(
    session: SessionDep,
    request: HallCreateRequest,
    current_user: CurrentAdminUser,
) -> HallResponse:
    slug = _normalize_slug(request.slug)

    existing = await session.get(Hall, slug)
    if existing is not None:
        raise HTTPException(status_code=409, detail=f"Hall already exists: {slug}")

    hall = Hall(
        slug=slug,
        name=request.name.strip(),
        description=request.description,
        floor=request.floor,
        estimated_duration_minutes=request.estimated_duration_minutes,
        display_order=request.display_order,
        is_active=request.is_active,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.add(hall)
    await session.commit()
    await session.refresh(hall)

    return _to_response(hall)


@router.put("/{slug}", response_model=HallResponse, summary="Update hall (admin)")
async def update_hall(
    session: SessionDep,
    slug: str,
    request: HallUpdateRequest,
    current_user: CurrentAdminUser,
) -> HallResponse:
    normalized_slug = _normalize_slug(slug)
    hall = await session.get(Hall, normalized_slug)
    if hall is None:
        raise HTTPException(status_code=404, detail=f"Hall not found: {normalized_slug}")

    if request.name is not None:
        hall.name = request.name.strip()
    if request.description is not None:
        hall.description = request.description
    if request.floor is not None:
        hall.floor = request.floor
    if request.estimated_duration_minutes is not None:
        hall.estimated_duration_minutes = request.estimated_duration_minutes
    if request.display_order is not None:
        hall.display_order = request.display_order
    if request.is_active is not None:
        hall.is_active = request.is_active

    hall.updated_at = datetime.now(UTC)

    await session.commit()
    await session.refresh(hall)

    return _to_response(hall)


@router.delete("/{slug}", response_model=HallDeleteResponse, summary="Delete hall (admin)")
async def delete_hall(
    session: SessionDep,
    slug: str,
    current_user: CurrentAdminUser,
) -> HallDeleteResponse:
    normalized_slug = _normalize_slug(slug)
    hall = await session.get(Hall, normalized_slug)
    if hall is None:
        raise HTTPException(status_code=404, detail=f"Hall not found: {normalized_slug}")

    await session.delete(hall)
    await session.commit()

    return HallDeleteResponse(status="deleted", slug=normalized_slug)
