from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_secret
from app.db.models import (
    CharacterRecord,
    EpisodeRecord,
    PanelRecord,
    PlotThreadRecord,
    ProjectRecord,
)
from app.providers import generate_structured_text
from app.schemas.workspace import (
    ContinuityOpenThread,
    ContinuityPreviousSummary,
    EpisodeReader,
    EpisodeSummaryResult,
    PlannedCharacter,
    PlannedEpisode,
    PlannedThread,
    ProjectContinuity,
    ProjectFromPlanCreate,
    ProjectFromPlanResult,
    ProjectPlanDraft,
    ProjectPlanRequest,
    ReaderPanel,
)
from app.schemas.workspace import Project as ProjectSchema
from app.tasks.support import require_text_model as _configured_model


class _PlanOutput(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    world_setting: str = Field(min_length=1, max_length=6000)
    characters: list[PlannedCharacter] = Field(min_length=1, max_length=12)
    chapters: list[PlannedEpisode] = Field(min_length=1, max_length=24)
    threads: list[PlannedThread] = Field(default_factory=list, max_length=50)


class _SummaryOutput(BaseModel):
    summary: str = Field(min_length=1, max_length=2000)


async def build_continuity(session: AsyncSession, project_id: UUID) -> ProjectContinuity:
    project = await session.get(ProjectRecord, project_id)
    if project is None:
        raise ValueError("项目不存在")
    episodes = list(
        (
            await session.scalars(
                select(EpisodeRecord)
                .where(EpisodeRecord.project_id == project_id)
                .order_by(EpisodeRecord.position)
            )
        ).all()
    )
    previous = [
        ContinuityPreviousSummary(
            episode_id=episode.id,
            position=episode.position,
            title=episode.title,
            summary=episode.summary,
        )
        for episode in episodes
        if episode.summary.strip()
    ]
    threads = list(
        (
            await session.scalars(
                select(PlotThreadRecord).where(
                    PlotThreadRecord.project_id == project_id,
                    PlotThreadRecord.resolved.is_(False),
                )
            )
        ).all()
    )
    return ProjectContinuity(
        world_setting=project.world_setting,
        previous_summaries=previous,
        open_threads=[
            ContinuityOpenThread(
                id=thread.id,
                text=thread.text,
                payoff_in_episode_id=thread.payoff_in_episode_id,
            )
            for thread in threads
        ],
    )


async def plan_project(
    session: AsyncSession, owner_id: UUID, body: ProjectPlanRequest
) -> ProjectPlanDraft:
    config = await _configured_model(session, owner_id)
    api_key = decrypt_secret(config.text_api_key_encrypted)
    output = await generate_structured_text(
        base_url=config.text_base_url,
        model=config.text_model,
        api_key=api_key,
        system_prompt=(
            "你是连载漫剧策划编辑。根据用户创意输出结构化季策划 JSON："
            "作品名、世界观、主要角色、分话大纲与跨话伏笔。只返回 JSON。"
        ),
        user_prompt=(
            f"创意：{body.premise}\n题材：{body.genre}\n画风：{body.art_style}\n"
            f"受众：{body.audience}\n目标话数：{body.chapter_count}\n"
            '返回 {"title":string,"world_setting":string,'
            '"characters":[{"name":string,"role":string,"appearance":string,'
            '"hairstyle":string,"outfit":string,"signature_traits":[string],'
            '"personality":string}],'
            '"chapters":[{"title":string,"synopsis":string}],'
            '"threads":[{"text":string,"planted_in":number|null,"payoff_in":number|null}]}。'
            f"chapters 数量必须为 {body.chapter_count}。"
        ),
        response_model=_PlanOutput,
    )
    if len(output.chapters) != body.chapter_count:
        raise ValueError("策划返回的话数与请求不一致，请重试")
    return ProjectPlanDraft(
        title=output.title,
        premise=body.premise,
        genre=body.genre,
        art_style=body.art_style,
        audience=body.audience,
        world_setting=output.world_setting,
        characters=output.characters,
        chapters=output.chapters,
        threads=output.threads,
        aspect_ratio=body.aspect_ratio,
    )


def _planned_outline_appendix(chapters: list[PlannedEpisode]) -> str:
    """Serialize chapters after the first into world_setting (SERIAL-01)."""
    rest = chapters[1:]
    if not rest:
        return ""
    lines = ["", "## 规划话大纲（尚未开作）", ""]
    for offset, chapter in enumerate(rest, start=2):
        lines.append(f"### 第{offset}话：{chapter.title}")
        lines.append(chapter.synopsis.strip() or "（待补充梗概）")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


async def create_project_from_plan(
    session: AsyncSession,
    owner_id: UUID,
    body: ProjectFromPlanCreate,
) -> ProjectFromPlanResult:
    if not body.chapters:
        raise ValueError("季策划至少需要一话大纲")
    world_setting = (body.world_setting or "").rstrip()
    appendix = _planned_outline_appendix(body.chapters)
    if appendix:
        world_setting = f"{world_setting}\n{appendix}".strip() if world_setting else appendix.strip()
    project = ProjectRecord(
        id=uuid4(),
        owner_id=owner_id,
        title=body.title,
        synopsis=body.premise,
        genre=body.genre,
        art_style=body.art_style,
        aspect_ratio=body.aspect_ratio,
        world_setting=world_setting,
    )
    session.add(project)
    await session.flush()
    # Only materialize chapter 1; later chapters stay as outline in world_setting.
    first = body.chapters[0]
    episode = EpisodeRecord(
        id=uuid4(),
        project_id=project.id,
        position=0,
        title=first.title,
        synopsis=first.synopsis,
        panel_count=8,
    )
    session.add(episode)
    await session.flush()
    episodes = [episode]
    episode_ids = [episode.id]
    for character in body.characters:
        session.add(
            CharacterRecord(
                id=uuid4(),
                project_id=project.id,
                name=character.name,
                status="draft",
                profile={
                    "generation_source": "ai",
                    "role": character.role,
                    "appearance": character.appearance,
                    "hairstyle": character.hairstyle,
                    "outfit": character.outfit,
                    "signature_traits": character.signature_traits,
                    "personality": character.personality,
                    "visual_traits": [character.hairstyle, *character.signature_traits],
                    "image_prompt": character.appearance,
                },
            )
        )
    for thread in body.threads:
        # Only chapter-1 episode exists; later plant/payoff indices stay unbound.
        planted = (
            episodes[0].id if thread.planted_in == 1 else None
        )
        payoff = episodes[0].id if thread.payoff_in == 1 else None
        session.add(
            PlotThreadRecord(
                id=uuid4(),
                project_id=project.id,
                text=thread.text,
                planted_in_episode_id=planted,
                payoff_in_episode_id=payoff,
                resolved=False,
            )
        )
    await session.commit()
    await session.refresh(project)
    return ProjectFromPlanResult(
        project=ProjectSchema.model_validate(project),
        episode_ids=episode_ids,
    )


async def generate_episode_summary(session: AsyncSession, episode_id: UUID) -> EpisodeSummaryResult:
    episode = await session.get(EpisodeRecord, episode_id)
    if episode is None:
        raise ValueError("故事单元不存在")
    project = await session.get(ProjectRecord, episode.project_id)
    if project is None:
        raise ValueError("项目不存在")
    panels = list(
        (
            await session.scalars(
                select(PanelRecord)
                .where(PanelRecord.episode_id == episode_id)
                .order_by(PanelRecord.position)
            )
        ).all()
    )
    config = await _configured_model(session, project.owner_id)
    api_key = decrypt_secret(config.text_api_key_encrypted)
    beats = [
        {
            "position": panel.position + 1,
            "scene": panel.scene_description,
            "action": panel.character_actions,
            "dialogue": panel.dialogue,
            "purpose": panel.story_purpose,
        }
        for panel in panels
    ]
    output = await generate_structured_text(
        base_url=config.text_base_url,
        model=config.text_model,
        api_key=api_key,
        system_prompt=(
            "你是连载编剧。根据本话分镜写 120–200 字前情摘要，供下一话续写。只返回 JSON。"
        ),
        user_prompt=(
            f"作品：{project.title}\n本话：{episode.title}\n梗概：{episode.synopsis}\n"
            f'分镜：{beats}\n返回 {{"summary":string}}。'
        ),
        response_model=_SummaryOutput,
    )
    episode.summary = output.summary
    await session.commit()
    return EpisodeSummaryResult(episode_id=episode.id, summary=episode.summary)


async def build_episode_reader(session: AsyncSession, episode_id: UUID) -> EpisodeReader:
    from app.schemas.workspace import Episode as EpisodeSchema

    episode = await session.get(EpisodeRecord, episode_id)
    if episode is None:
        raise ValueError("故事单元不存在")
    siblings = list(
        (
            await session.scalars(
                select(EpisodeRecord)
                .where(EpisodeRecord.project_id == episode.project_id)
                .order_by(EpisodeRecord.position)
            )
        ).all()
    )
    index = next((i for i, item in enumerate(siblings) if item.id == episode.id), 0)
    panels = list(
        (
            await session.scalars(
                select(PanelRecord)
                .where(PanelRecord.episode_id == episode_id)
                .order_by(PanelRecord.position)
            )
        ).all()
    )
    return EpisodeReader(
        episode=EpisodeSchema.model_validate(episode),
        panels=[
            ReaderPanel(
                id=panel.id,
                position=panel.position,
                image_url=panel.current_image_url,
                dialogue=panel.dialogue,
                action=panel.character_actions,
            )
            for panel in panels
        ],
        previous_episode_id=siblings[index - 1].id if index > 0 else None,
        next_episode_id=siblings[index + 1].id if index + 1 < len(siblings) else None,
    )
