"""Episode page layout (PAGE A1) application service."""

from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ImageVersionRecord, LayoutPageRecord, PageSlotRecord, PanelRecord
from app.schemas.workspace import (
    BootstrapLayoutRequest,
    EpisodeLayout,
    LayoutPage,
    LayoutPreview,
    LayoutPreviewItem,
    LetteringObject,
    PageOrder,
    PageSlot,
    PageSlotPatch,
    SlotOrder,
    SyncLayoutRequest,
)


def _not_found(resource: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"{resource}不存在")


def _conflict(message: str) -> HTTPException:
    return HTTPException(status_code=409, detail=message)


def _slot_view(slot: PageSlotRecord, lettering: list[LetteringObject] | None = None) -> PageSlot:
    return PageSlot(
        id=slot.id,
        page_id=slot.page_id,
        position=slot.position,
        panel_id=slot.panel_id,
        image_version_id=slot.image_version_id,
        height_px=slot.height_px,
        gap_after_px=slot.gap_after_px,
        follow_current_version=slot.follow_current_version,
        lettering=lettering or [],
        created_at=slot.created_at,
        updated_at=slot.updated_at,
    )


async def list_pages_for_episode(session: AsyncSession, episode_id: UUID) -> list[LayoutPageRecord]:
    result = await session.scalars(
        select(LayoutPageRecord)
        .where(LayoutPageRecord.episode_id == episode_id)
        .order_by(LayoutPageRecord.position)
    )
    return list(result.all())


_pages_for_episode = list_pages_for_episode


async def list_slots_for_pages(
    session: AsyncSession, page_ids: list[UUID]
) -> dict[UUID, list[PageSlotRecord]]:
    if not page_ids:
        return {}
    result = await session.scalars(
        select(PageSlotRecord)
        .where(PageSlotRecord.page_id.in_(page_ids))
        .order_by(PageSlotRecord.page_id, PageSlotRecord.position)
    )
    grouped: dict[UUID, list[PageSlotRecord]] = {page_id: [] for page_id in page_ids}
    for slot in result.all():
        grouped.setdefault(slot.page_id, []).append(slot)
    return grouped


_slots_for_pages = list_slots_for_pages


async def _layout_view(session: AsyncSession, episode_id: UUID) -> EpisodeLayout:
    # Lazy import avoids circular dependency with lettering → layout.
    from app.services.lettering import lettering_for_slots

    pages = await _pages_for_episode(session, episode_id)
    slots_by_page = await _slots_for_pages(session, [page.id for page in pages])
    all_slots = [slot for slots in slots_by_page.values() for slot in slots]
    lettering_by_slot = await lettering_for_slots(session, [slot.id for slot in all_slots])
    return EpisodeLayout(
        episode_id=episode_id,
        template="vertical_strip",
        pages=[
            LayoutPage(
                id=page.id,
                episode_id=page.episode_id,
                position=page.position,
                template="vertical_strip",
                slots=[
                    _slot_view(slot, lettering_by_slot.get(slot.id, []))
                    for slot in slots_by_page.get(page.id, [])
                ],
                created_at=page.created_at,
                updated_at=page.updated_at,
            )
            for page in pages
        ],
    )


async def _current_version_id_for_panel(session: AsyncSession, panel: PanelRecord) -> UUID | None:
    if panel.current_image_asset_id is None:
        return None
    version = await session.scalar(
        select(ImageVersionRecord)
        .where(
            ImageVersionRecord.panel_id == panel.id,
            ImageVersionRecord.asset_id == panel.current_image_asset_id,
        )
        .order_by(ImageVersionRecord.created_at.desc())
        .limit(1)
    )
    return version.id if version is not None else None


async def get_episode_layout(episode_id: UUID, session: AsyncSession) -> EpisodeLayout:
    return await _layout_view(session, episode_id)


async def bootstrap_episode_layout(
    episode_id: UUID,
    body: BootstrapLayoutRequest | None,
    session: AsyncSession,
) -> EpisodeLayout:
    existing = await _pages_for_episode(session, episode_id)
    if existing:
        raise _conflict("该话已有成稿布局，请使用同步或编辑接口")

    panels = list(
        (
            await session.scalars(
                select(PanelRecord)
                .where(PanelRecord.episode_id == episode_id)
                .order_by(PanelRecord.position)
            )
        ).all()
    )
    if not panels:
        raise HTTPException(status_code=422, detail="本话尚无画格，无法生成默认竖条页")

    opts = body or BootstrapLayoutRequest()
    page = LayoutPageRecord(
        id=uuid4(),
        episode_id=episode_id,
        position=0,
        template="vertical_strip",
    )
    session.add(page)
    await session.flush()

    for index, panel in enumerate(panels):
        session.add(
            PageSlotRecord(
                id=uuid4(),
                page_id=page.id,
                position=index,
                panel_id=panel.id,
                image_version_id=await _current_version_id_for_panel(session, panel),
                height_px=opts.default_height_px,
                gap_after_px=opts.default_gap_px,
                follow_current_version=True,
            )
        )

    await session.commit()
    return await _layout_view(session, episode_id)


async def sync_episode_layout(
    episode_id: UUID,
    body: SyncLayoutRequest | None,
    session: AsyncSession,
) -> EpisodeLayout:
    pages = await _pages_for_episode(session, episode_id)
    if not pages:
        raise _not_found("成稿布局")

    opts = body or SyncLayoutRequest()
    panels = list(
        (
            await session.scalars(
                select(PanelRecord)
                .where(PanelRecord.episode_id == episode_id)
                .order_by(PanelRecord.position)
            )
        ).all()
    )
    panel_by_id = {panel.id: panel for panel in panels}
    slots_by_page = await _slots_for_pages(session, [page.id for page in pages])
    all_slots = [slot for slots in slots_by_page.values() for slot in slots]

    # Drop slots for deleted panels.
    for slot in list(all_slots):
        if slot.panel_id not in panel_by_id:
            await session.delete(slot)
            all_slots.remove(slot)

    surviving_panel_ids = {slot.panel_id for slot in all_slots}
    # Append new panels to the last page (or create one).
    target_page = pages[-1]
    existing_positions = [slot.position for slot in slots_by_page.get(target_page.id, [])]
    next_position = max(existing_positions, default=-1) + 1
    for panel in panels:
        if panel.id in surviving_panel_ids:
            continue
        session.add(
            PageSlotRecord(
                id=uuid4(),
                page_id=target_page.id,
                position=next_position,
                panel_id=panel.id,
                image_version_id=await _current_version_id_for_panel(session, panel),
                height_px=720,
                gap_after_px=24,
                follow_current_version=True,
            )
        )
        next_position += 1

    if opts.follow_current_version:
        refreshed = await _slots_for_pages(session, [page.id for page in pages])
        for slots in refreshed.values():
            for slot in slots:
                if not slot.follow_current_version:
                    continue
                follow_panel = panel_by_id.get(slot.panel_id)
                if follow_panel is None:
                    continue
                slot.image_version_id = await _current_version_id_for_panel(session, follow_panel)

    # Compact positions per page.
    await session.flush()
    pages = await _pages_for_episode(session, episode_id)
    slots_by_page = await _slots_for_pages(session, [page.id for page in pages])
    for page in pages:
        for index, slot in enumerate(slots_by_page.get(page.id, [])):
            slot.position = index

    await session.commit()
    return await _layout_view(session, episode_id)


async def get_episode_layout_preview(episode_id: UUID, session: AsyncSession) -> LayoutPreview:
    layout = await _layout_view(session, episode_id)
    version_ids = [
        slot.image_version_id
        for page in layout.pages
        for slot in page.slots
        if slot.image_version_id is not None
    ]
    url_by_version: dict[UUID, str] = {}
    if version_ids:
        rows = (
            await session.scalars(
                select(ImageVersionRecord).where(ImageVersionRecord.id.in_(version_ids))
            )
        ).all()
        url_by_version = {row.id: row.image_url for row in rows}

    items: list[LayoutPreviewItem] = []
    for page in layout.pages:
        for slot in page.slots:
            items.append(
                LayoutPreviewItem(
                    slot_id=slot.id,
                    page_id=page.id,
                    panel_id=slot.panel_id,
                    height_px=slot.height_px,
                    gap_after_px=slot.gap_after_px,
                    image_url=url_by_version.get(slot.image_version_id)
                    if slot.image_version_id
                    else None,
                    lettering=list(slot.lettering),
                )
            )
    return LayoutPreview(
        episode_id=episode_id,
        kind="manuscript_preview",
        width_hint_px=720,
        items=items,
    )


async def reorder_pages(episode_id: UUID, body: PageOrder, session: AsyncSession) -> EpisodeLayout:
    pages = await _pages_for_episode(session, episode_id)
    if not pages:
        raise _not_found("成稿布局")
    page_by_id = {page.id: page for page in pages}
    if set(body.page_ids) != set(page_by_id):
        raise _conflict("页序必须包含该话全部页且仅这些页")
    for index, page_id in enumerate(body.page_ids):
        page_by_id[page_id].position = index
    await session.commit()
    return await _layout_view(session, episode_id)


async def reorder_page_slots(page_id: UUID, body: SlotOrder, session: AsyncSession) -> LayoutPage:
    page = await session.get(LayoutPageRecord, page_id)
    if page is None:
        raise _not_found("页")
    slots = list(
        (
            await session.scalars(
                select(PageSlotRecord)
                .where(PageSlotRecord.page_id == page_id)
                .order_by(PageSlotRecord.position)
            )
        ).all()
    )
    slot_by_id = {slot.id: slot for slot in slots}
    if set(body.slot_ids) != set(slot_by_id):
        raise _conflict("槽序必须包含该页全部槽位且仅这些槽位")
    for index, slot_id in enumerate(body.slot_ids):
        slot_by_id[slot_id].position = index
    await session.commit()
    layout = await _layout_view(session, page.episode_id)
    for layout_page in layout.pages:
        if layout_page.id == page_id:
            return layout_page
    raise _not_found("页")


async def update_page_slot(slot_id: UUID, body: PageSlotPatch, session: AsyncSession) -> PageSlot:
    slot = await session.get(PageSlotRecord, slot_id)
    if slot is None:
        raise _not_found("槽位")
    if body.height_px is not None:
        slot.height_px = body.height_px
    if body.gap_after_px is not None:
        slot.gap_after_px = body.gap_after_px
    if body.follow_current_version is not None:
        slot.follow_current_version = body.follow_current_version
    if "image_version_id" in body.model_fields_set:
        if body.image_version_id is None:
            slot.image_version_id = None
        else:
            version = await session.get(ImageVersionRecord, body.image_version_id)
            if version is None or version.panel_id != slot.panel_id:
                raise HTTPException(status_code=422, detail="图像版本必须属于该槽位对应画格")
            slot.image_version_id = version.id
            slot.follow_current_version = False
    await session.commit()
    await session.refresh(slot)
    from app.services.lettering import lettering_for_slots

    lettering = (await lettering_for_slots(session, [slot.id])).get(slot.id, [])
    return _slot_view(slot, lettering)


async def retarget_slots_for_panel_version(
    session: AsyncSession,
    *,
    panel_id: UUID,
    image_version_id: UUID,
) -> None:
    """Called after a panel's current image version changes."""
    slots = list(
        (
            await session.scalars(
                select(PageSlotRecord).where(
                    PageSlotRecord.panel_id == panel_id,
                    PageSlotRecord.follow_current_version.is_(True),
                )
            )
        ).all()
    )
    for slot in slots:
        slot.image_version_id = image_version_id
    if slots:
        await session.flush()
