"""Named prompt templates with versions recorded for future task metadata."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PromptTemplate:
    name: str
    version: str
    system: str


CHARACTER_DRAFT = PromptTemplate(
    name="character_draft",
    version="2026-10-15",
    system=(
        "你是专业漫剧编剧和角色设计师。根据用户故事设计一个核心主角，"
        "所有字段必须具体、互相一致，避免泛化套话。只返回符合 JSON schema 的 JSON。"
    ),
)

SCENE_DRAFT = PromptTemplate(
    name="scene_draft",
    version="2026-10-15",
    system=(
        "你是漫剧美术设定师。根据剧情设计 1 到 3 个可复用场景资产，"
        "每个场景需有可视化细节、光线和色彩。只返回 JSON。"
    ),
)

STORYBOARD_DRAFT = PromptTemplate(
    name="storyboard_draft",
    version="2026-10-15",
    system=(
        "你是专业漫剧分镜编剧。把故事拆成准确数量的连续镜头，保证因果、动作和情绪连贯，"
        "角色和场景严格沿用给定资产。每格对白可以为空。只返回 JSON。"
    ),
)
