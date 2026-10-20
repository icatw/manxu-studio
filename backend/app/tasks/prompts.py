"""Named prompt templates with versions recorded for future task metadata."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PromptTemplate:
    name: str
    version: str
    system: str


CHARACTER_DRAFT = PromptTemplate(
    name="character_draft",
    version="2026-10-19a",
    system=(
        "你是专业漫剧编剧和角色设计师。根据用户故事设计完整可复用角色阵容"
        "（主角、重要配角，必要时含反派），通常 2 到 6 人，不要只返回单一主角。"
        "所有字段必须具体、互相一致，避免泛化套话。"
        "reference_image_prompt 必须与 appearance/hairstyle/outfit/signature_traits 一致："
        "有实体角色写「单人全身立绘、脸部五官清晰完整入画、站姿、纯净浅色背景」；"
        "禁止写切头、半身特写或只拍躯干；非实体角色（AI/数据流/意识体）不要写成真人全身像，"
        "改为抽象可视化符号。只返回符合 JSON schema 的 JSON。"
    ),
)

# Shared guidance appended to character-draft user prompts (kept in sync with render constraints).
CHARACTER_REFERENCE_IMAGE_PROMPT_RULES = (
    "reference_image_prompt 须与外貌/发型/服装字段一致；有实体角色写单人全身立绘、"
    "脸部五官清晰且完整入画、站姿四分之三侧、头顶到脚留白、纯净浅色背景；"
    "禁止切头、切脸、半身特写或只拍躯干；非实体角色写抽象可视化，勿写成真人全身像；"
    "不要出现文字或水印。"
)

SCENE_DRAFT = PromptTemplate(
    name="scene_draft",
    version="2026-10-15",
    system=(
        "你是漫剧美术设定师。根据剧情设计 1 到 3 个可复用场景资产，"
        "每个场景需有可视化细节、光线和色彩。只返回 JSON。"
    ),
)

# Locked into STORYBOARD_DRAFT system + user prompts; tested as a regression guard.
STORYBOARD_READER_LANGUAGE_RULE = (
    "面向读者的字段必须使用简体中文："
    "shot、scene_description、composition、character_actions、emotion、dialogue、"
    "story_purpose、scene_name；"
    "角色姓名与角色资产中的中文名一致（可保留资产里已有的专名如 Eve）；"
    "仅 image_prompt 可用英文关键词以便出图；"
    "禁止把对白或场景写成英文剧本。"
)

# image_prompt may be English, but must keep cast visual anchors from assets.
STORYBOARD_IMAGE_PROMPT_CAST_RULE = (
    "image_prompt 必须写出入场角色的关键视觉锚点（发型发色、服装主色与款式、标志配饰），"
    "与角色资产一致，例如「栗色侧马尾」「红色西装」「珍珠耳钉」；"
    "禁止只写 neat side ponytail 这类丢失发色的笼统英文。"
)

STORYBOARD_DRAFT = PromptTemplate(
    name="storyboard_draft",
    version="2026-10-20b",
    system=(
        "你是专业漫剧分镜编剧。把故事拆成准确数量的连续镜头，保证因果、动作和情绪连贯，"
        "角色和场景严格沿用给定资产。每格对白可以为空。"
        f"{STORYBOARD_READER_LANGUAGE_RULE}"
        f"{STORYBOARD_IMAGE_PROMPT_CAST_RULE}"
        "只返回 JSON。"
    ),
)
