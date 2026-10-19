"""End-to-end generation trajectory for offline model comparison."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

# Import production schemas when backend is on PYTHONPATH.
from app.tasks.prompts import CHARACTER_DRAFT, SCENE_DRAFT, STORYBOARD_DRAFT
from app.tasks.schemas import (
    CharacterGenerationOutput,
    SceneGenerationOutput,
    StoryboardGenerationOutput,
)
from model_eval.clients import (
    generate_agnes_image,
    generate_openai_compatible_image,
    generate_qwen_image,
    generate_structured_text,
    size_for_ratio,
)

# Strong no-glyph constraint for comic panels (LETTER layer owns readable text).
NO_TEXT_CONSTRAINT = (
    "画面中禁止出现任何可读文字、字母、汉字、假名、数字、二维码或水印；"
    "禁止工牌/名牌上的字、手机屏幕 UI 字、货架价签与包装印刷字、霓虹招牌字；"
    "招牌与屏幕只保留色块与光晕，不要可辨认字形；气泡与旁白留空，由后期字层添加。"
)
from model_eval.configs import EvalConfig
from model_eval.schemas_local import PlanOutput
from model_eval.scoring import (
    StageScore,
    TrialScore,
    assemble_trial_score,
    score_characters,
    score_images,
    score_plan,
    score_scenes,
    score_storyboard,
)


async def run_trial(
    *,
    config: EvalConfig,
    case: dict[str, Any],
    trial_index: int,
    out_dir: Path,
    skip_images: bool = False,
    with_agnes_refs: bool = False,
    panel_image_limit: int = 4,
) -> TrialScore:
    case_id = str(case["id"])
    run_dir = out_dir / f"trial-{trial_index:02d}"
    run_dir.mkdir(parents=True, exist_ok=True)
    stages: list[StageScore] = []
    metrics_log: list[dict[str, Any]] = []
    text_tokens = 0
    token_known = False
    image_paths: list[str] = []
    wall_started = time.perf_counter()

    art_style = str(case.get("art_style") or "日系竖条漫画，清晰线稿")
    genre = str(case.get("genre") or "都市")
    chapter_count = int(case.get("chapter_count") or 2)
    panel_count = int(case.get("panel_count") or 6)
    min_cast = int(case.get("min_characters") or 2)
    max_cast = int(case.get("max_characters") or 6)
    min_scenes = int(case.get("min_scenes") or 1)
    max_scenes = int(case.get("max_scenes") or 3)

    # --- plan ---
    try:
        plan_result = await generate_structured_text(
            base_url=config.text.base_url,
            model=config.text.model,
            api_key=config.text.api_key(),
            system_prompt=(
                "你是连载漫剧策划编辑。根据用户创意输出结构化季策划 JSON："
                "作品名、世界观、主要角色、分话大纲与跨话伏笔。只返回 JSON。"
            ),
            user_prompt=(
                f"创意：{case['premise']}\n题材：{genre}\n画风：{art_style}\n"
                f"受众：{case.get('audience', '年轻连载读者')}\n目标话数：{chapter_count}\n"
                '返回 {"title":string,"world_setting":string,'
                '"characters":[{"name":string,"role":string,"appearance":string,'
                '"hairstyle":string,"outfit":string,"signature_traits":[string],'
                '"personality":string}],'
                '"chapters":[{"title":string,"synopsis":string}],'
                '"threads":[{"text":string,"planted_in":number|null,"payoff_in":number|null}]}。'
                f"chapters 数量必须为 {chapter_count}。"
            ),
            response_model=PlanOutput,
        )
        _accumulate_tokens(plan_result.metrics, metrics_log, "plan")
        if plan_result.metrics.total_tokens is not None:
            text_tokens += plan_result.metrics.total_tokens
            token_known = True
        plan = plan_result.value
        (run_dir / "plan.json").write_text(
            plan.model_dump_json(indent=2), encoding="utf-8"
        )
        stages.append(score_plan(plan.model_dump(), chapter_count=chapter_count))
        title = plan.title
        world_setting = plan.world_setting
        synopsis = plan.chapters[0].synopsis if plan.chapters else case["premise"]
    except Exception as error:  # noqa: BLE001 — eval must continue scoring failures
        stages.append(
            StageScore(stage="plan", passed=False, checks={"exception": False}, detail=str(error))
        )
        return _finalize(
            config,
            case_id,
            trial_index,
            stages,
            wall_started,
            text_tokens if token_known else None,
            image_paths,
            run_dir,
            metrics_log,
        )

    # --- characters ---
    characters_data: list[dict[str, Any]] = []
    try:
        char_result = await generate_structured_text(
            base_url=config.text.base_url,
            model=config.text.model,
            api_key=config.text.api_key(),
            system_prompt=CHARACTER_DRAFT.system,
            user_prompt=(
                f"故事标题：{title}\n故事梗概：{synopsis}\n题材：{genre}\n画风：{art_style}\n"
                f"根据剧情设计完整可复用角色阵容（主角、重要配角、必要时反派），"
                f"通常 {min_cast} 到 {max_cast} 人，避免只返回单一主角。\n"
                '返回对象格式：{"characters":[{"name":string,"role":string,'
                '"appearance":string,"hairstyle":string,"outfit":string,'
                '"signature_traits":[string],"personality":string,'
                '"reference_image_prompt":string}]}。参考图提示词描述单人全身立绘、'
                "纯净背景、清晰服装和辨识特征，不要出现文字或水印。"
            ),
            response_model=CharacterGenerationOutput,
        )
        _accumulate_tokens(char_result.metrics, metrics_log, "characters")
        if char_result.metrics.total_tokens is not None:
            text_tokens += char_result.metrics.total_tokens
            token_known = True
        characters_data = [item.model_dump() for item in char_result.value.characters]
        (run_dir / "characters.json").write_text(
            json.dumps(characters_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        stages.append(
            score_characters(characters_data, min_count=min_cast, max_count=max_cast)
        )
    except Exception as error:  # noqa: BLE001
        stages.append(
            StageScore(
                stage="characters",
                passed=False,
                checks={"exception": False},
                detail=str(error),
            )
        )
        return _finalize(
            config,
            case_id,
            trial_index,
            stages,
            wall_started,
            text_tokens if token_known else None,
            image_paths,
            run_dir,
            metrics_log,
        )

    cast_names = [str(item.get("name") or "") for item in characters_data]

    # --- character reference images ---
    char_image_paths: list[Path] = []
    if not skip_images:
        for index, character in enumerate(characters_data):
            prompt = (
                f"{art_style}。角色：{character.get('name', '')}。"
                f"外貌：{character.get('appearance', '')}。"
                f"发型必须为：{character.get('hairstyle', '')}。"
                f"服装必须为：{character.get('outfit', '')}。"
                f"补充：{character.get('reference_image_prompt', '')}。"
                "单人全身立绘，站姿四分之三侧，从头顶到脚完整入画，脸部五官清晰可见；"
                "禁止切头、切脸或只拍躯干；纯净浅色背景。"
                f"{NO_TEXT_CONSTRAINT}"
            )
            dest = run_dir / "images" / f"char-{index:02d}"
            try:
                image = await _generate_image(
                    config=config,
                    prompt=prompt,
                    dest=dest,
                    prompt_extend=False,
                    ratio="3:4",
                    reference_paths=None,
                )
                char_image_paths.append(image.path)
                image_paths.append(str(image.path))
                metrics_log.append(
                    {
                        "stage": f"char_image_{index}",
                        "latency_ms": image.metrics.latency_ms,
                        "provider": image.provider_kind,
                    }
                )
            except Exception as error:  # noqa: BLE001
                stages.append(
                    StageScore(
                        stage="char_images",
                        passed=False,
                        checks={"exception": False},
                        detail=f"{character.get('name')}: {error}",
                    )
                )
                return _finalize(
                    config,
                    case_id,
                    trial_index,
                    stages,
                    wall_started,
                    text_tokens if token_known else None,
                    image_paths,
                    run_dir,
                    metrics_log,
                )
        stages.append(
            score_images(
                [str(p) for p in char_image_paths],
                expected=len(characters_data),
                stage="char_images",
            )
        )
    else:
        stages.append(
            StageScore(
                stage="char_images",
                passed=True,
                checks={"skipped": True},
                detail="skip_images",
            )
        )

    # --- scenes ---
    scenes_data: list[dict[str, Any]] = []
    try:
        scene_result = await generate_structured_text(
            base_url=config.text.base_url,
            model=config.text.model,
            api_key=config.text.api_key(),
            system_prompt=SCENE_DRAFT.system,
            user_prompt=(
                f"故事标题：{title}\n故事梗概：{synopsis}\n题材：{genre}\n画风：{art_style}\n"
                f"世界观：{world_setting}\n"
                f"设计 {min_scenes} 到 {max_scenes} 个可复用场景资产。\n"
                '返回 {"scenes":[{"name":string,"description":string,"lighting":string,'
                '"palette":string,"visual_traits":[string]}]}。'
            ),
            response_model=SceneGenerationOutput,
        )
        _accumulate_tokens(scene_result.metrics, metrics_log, "scenes")
        if scene_result.metrics.total_tokens is not None:
            text_tokens += scene_result.metrics.total_tokens
            token_known = True
        scenes_data = [item.model_dump() for item in scene_result.value.scenes]
        (run_dir / "scenes.json").write_text(
            json.dumps(scenes_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        stages.append(score_scenes(scenes_data, min_count=min_scenes, max_count=max_scenes))
    except Exception as error:  # noqa: BLE001
        stages.append(
            StageScore(
                stage="scenes", passed=False, checks={"exception": False}, detail=str(error)
            )
        )
        return _finalize(
            config,
            case_id,
            trial_index,
            stages,
            wall_started,
            text_tokens if token_known else None,
            image_paths,
            run_dir,
            metrics_log,
        )

    if not skip_images:
        scene_image_paths: list[Path] = []
        for index, scene in enumerate(scenes_data):
            prompt = (
                f"{art_style}，场景「{scene.get('name', '')}」："
                f"{scene.get('description', '')}；光线：{scene.get('lighting', '')}；"
                f"色板：{scene.get('palette', '')}。空镜环境。"
                f"{NO_TEXT_CONSTRAINT}"
            )
            dest = run_dir / "images" / f"scene-{index:02d}"
            try:
                image = await _generate_image(
                    config=config,
                    prompt=prompt,
                    dest=dest,
                    prompt_extend=False,
                    ratio="9:16",
                    reference_paths=None,
                )
                scene_image_paths.append(image.path)
                image_paths.append(str(image.path))
                metrics_log.append(
                    {
                        "stage": f"scene_image_{index}",
                        "latency_ms": image.metrics.latency_ms,
                        "provider": image.provider_kind,
                    }
                )
            except Exception as error:  # noqa: BLE001
                stages.append(
                    StageScore(
                        stage="scene_images",
                        passed=False,
                        checks={"exception": False},
                        detail=str(error),
                    )
                )
                return _finalize(
                    config,
                    case_id,
                    trial_index,
                    stages,
                    wall_started,
                    text_tokens if token_known else None,
                    image_paths,
                    run_dir,
                    metrics_log,
                )
        stages.append(
            score_images(
                [str(p) for p in scene_image_paths],
                expected=len(scenes_data),
                stage="scene_images",
            )
        )
    else:
        stages.append(
            StageScore(
                stage="scene_images",
                passed=True,
                checks={"skipped": True},
                detail="skip_images",
            )
        )

    # --- storyboard ---
    panels_data: list[dict[str, Any]] = []
    try:
        board_result = await generate_structured_text(
            base_url=config.text.base_url,
            model=config.text.model,
            api_key=config.text.api_key(),
            system_prompt=STORYBOARD_DRAFT.system,
            user_prompt=(
                f"作品：{title}\n题材：{genre}\n画风：{art_style}\n梗概：{synopsis}\n"
                f"世界观：{world_setting}\n"
                f"分镜数：{panel_count}\n节奏：balanced\n"
                f"角色资产：{characters_data}\n场景资产：{scenes_data}\n"
                '返回格式：{"panels":[{"shot":string,"scene_description":string,'
                '"composition":string,"character_actions":string,"emotion":string,'
                '"dialogue":string,"story_purpose":string,"image_prompt":string,'
                '"scene_name":string,"character_names":[string]}]}。'
                "character_names 填写本格出场角色在角色资产中的准确姓名；无人出场则为 []。"
                "panels 数量必须与分镜数完全一致。"
            ),
            response_model=StoryboardGenerationOutput,
        )
        _accumulate_tokens(board_result.metrics, metrics_log, "storyboard")
        if board_result.metrics.total_tokens is not None:
            text_tokens += board_result.metrics.total_tokens
            token_known = True
        panels_data = [item.model_dump() for item in board_result.value.panels]
        (run_dir / "storyboard.json").write_text(
            json.dumps(panels_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        stages.append(
            score_storyboard(panels_data, panel_count=panel_count, cast_names=cast_names)
        )
    except Exception as error:  # noqa: BLE001
        stages.append(
            StageScore(
                stage="storyboard",
                passed=False,
                checks={"exception": False},
                detail=str(error),
            )
        )
        return _finalize(
            config,
            case_id,
            trial_index,
            stages,
            wall_started,
            text_tokens if token_known else None,
            image_paths,
            run_dir,
            metrics_log,
        )

    # --- panel images (subset) + one edit ---
    if not skip_images and panels_data:
        selected = panels_data[: max(1, min(panel_image_limit, len(panels_data)))]
        panel_paths: list[Path] = []
        for index, panel in enumerate(selected):
            prompt = _panel_prompt(art_style, panel, characters_data)
            refs: list[Path] | None = None
            if with_agnes_refs and config.image.kind == "agnes_image" and char_image_paths:
                # Map character_names to reference images when possible.
                name_to_path = {
                    str(characters_data[i].get("name") or ""): char_image_paths[i]
                    for i in range(min(len(characters_data), len(char_image_paths)))
                }
                refs = [
                    name_to_path[name]
                    for name in (panel.get("character_names") or [])
                    if name in name_to_path
                ][:3] or None
            dest = run_dir / "images" / f"panel-{index:02d}"
            try:
                image = await _generate_image(
                    config=config,
                    prompt=prompt,
                    dest=dest,
                    prompt_extend=True,
                    ratio="9:16",
                    reference_paths=refs,
                )
                panel_paths.append(image.path)
                image_paths.append(str(image.path))
                metrics_log.append(
                    {
                        "stage": f"panel_image_{index}",
                        "latency_ms": image.metrics.latency_ms,
                        "provider": image.provider_kind,
                        "used_refs": bool(refs),
                    }
                )
            except Exception as error:  # noqa: BLE001
                stages.append(
                    StageScore(
                        stage="panel_images",
                        passed=False,
                        checks={"exception": False},
                        detail=str(error),
                    )
                )
                return _finalize(
                    config,
                    case_id,
                    trial_index,
                    stages,
                    wall_started,
                    text_tokens if token_known else None,
                    image_paths,
                    run_dir,
                    metrics_log,
                )

        # one small edit on first panel
        edit_prompt = (
            _panel_prompt(art_style, selected[0], characters_data)
            + "\n轻微调整：表情更紧张，构图不变，角色外观保持一致。"
        )
        edit_refs = None
        if with_agnes_refs and config.image.kind == "agnes_image" and panel_paths:
            edit_refs = [panel_paths[0]]
        try:
            edited = await _generate_image(
                config=config,
                prompt=edit_prompt,
                dest=run_dir / "images" / "panel-00-edit",
                prompt_extend=True,
                ratio="9:16",
                reference_paths=edit_refs,
            )
            image_paths.append(str(edited.path))
            metrics_log.append(
                {
                    "stage": "panel_edit",
                    "latency_ms": edited.metrics.latency_ms,
                    "provider": edited.provider_kind,
                }
            )
            stages.append(
                score_images(
                    [str(p) for p in panel_paths] + [str(edited.path)],
                    expected=len(panel_paths) + 1,
                    stage="panel_images",
                )
            )
        except Exception as error:  # noqa: BLE001
            stages.append(
                StageScore(
                    stage="panel_images",
                    passed=False,
                    checks={"edit_failed": False},
                    detail=str(error),
                )
            )
            return _finalize(
                config,
                case_id,
                trial_index,
                stages,
                wall_started,
                text_tokens if token_known else None,
                image_paths,
                run_dir,
                metrics_log,
            )
    else:
        stages.append(
            StageScore(
                stage="panel_images",
                passed=True,
                checks={"skipped": True},
                detail="skip_images",
            )
        )

    return _finalize(
        config,
        case_id,
        trial_index,
        stages,
        wall_started,
        text_tokens if token_known else None,
        image_paths,
        run_dir,
        metrics_log,
    )


async def _generate_image(
    *,
    config: EvalConfig,
    prompt: str,
    dest: Path,
    prompt_extend: bool,
    ratio: str,
    reference_paths: list[Path] | None,
):
    if config.image.kind == "qwen_image":
        # Aliyun MaaS / Workspace often only expose OpenAI-compatible images.
        if "compatible-mode" in config.image.base_url:
            return await generate_openai_compatible_image(
                base_url=config.image.base_url,
                model=config.image.model,
                api_key=config.image.api_key(),
                prompt=prompt,
                dest=dest,
                size=size_for_ratio(ratio),
            )
        return await generate_qwen_image(
            base_url=config.image.base_url,
            model=config.image.model,
            api_key=config.image.api_key(),
            prompt=prompt,
            dest=dest,
            prompt_extend=prompt_extend,
        )
    if config.image.kind == "agnes_image":
        return await generate_agnes_image(
            base_url=config.image.base_url,
            model=config.image.model,
            api_key=config.image.api_key(),
            prompt=prompt,
            dest=dest,
            size="1K",
            ratio=ratio,
            reference_paths=reference_paths,
        )
    raise ValueError(f"未知图像 provider kind: {config.image.kind}")


def _panel_prompt(
    art_style: str, panel: dict[str, Any], characters: list[dict[str, Any]]
) -> str:
    locks: list[str] = []
    wanted = {str(name) for name in (panel.get("character_names") or [])}
    for character in characters:
        name = str(character.get("name") or "")
        if name not in wanted:
            continue
        parts = [f"角色「{name}」保持定妆一致"]
        if character.get("appearance"):
            parts.append(str(character["appearance"]))
        if character.get("reference_image_prompt"):
            parts.append(str(character["reference_image_prompt"]))
        locks.append("；".join(parts))
    return "\n".join(
        item
        for item in [
            art_style,
            str(panel.get("scene_description") or ""),
            str(panel.get("shot") or ""),
            str(panel.get("composition") or ""),
            str(panel.get("character_actions") or ""),
            str(panel.get("emotion") or ""),
            *locks,
            "保持漫画分镜构图。",
            NO_TEXT_CONSTRAINT,
        ]
        if item
    )


def _accumulate_tokens(metrics: Any, log: list[dict[str, Any]], stage: str) -> None:
    log.append(
        {
            "stage": stage,
            "latency_ms": metrics.latency_ms,
            "prompt_tokens": metrics.prompt_tokens,
            "completion_tokens": metrics.completion_tokens,
            "total_tokens": metrics.total_tokens,
        }
    )


def _finalize(
    config: EvalConfig,
    case_id: str,
    trial_index: int,
    stages: list[StageScore],
    wall_started: float,
    text_tokens: int | None,
    image_paths: list[str],
    run_dir: Path,
    metrics_log: list[dict[str, Any]],
) -> TrialScore:
    score = assemble_trial_score(
        config_id=config.id,
        case_id=case_id,
        trial=trial_index,
        stages=stages,
        total_latency_ms=int((time.perf_counter() - wall_started) * 1000),
        text_tokens=text_tokens,
        image_count=len(image_paths),
    )
    (run_dir / "metrics.json").write_text(
        json.dumps(metrics_log, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (run_dir / "score.json").write_text(
        json.dumps(score.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (run_dir / "config.json").write_text(
        json.dumps(
            {
                "id": config.id,
                "label": config.label,
                "text_model": config.text.model,
                "text_base_url": config.text.base_url,
                "image_model": config.image.model,
                "image_kind": config.image.kind,
                "image_base_url": config.image.base_url,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return score
